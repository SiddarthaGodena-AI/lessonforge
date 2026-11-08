"""Self-evolution. Reads failure memory, proposes ONE generator-side rule per repeatedly failing check, and only
activates it if an A/B experiment shows it helps without making anything else worse.
DESIGN: the reflector can never edit the rubric, thresholds or judge prompts - only generator rules - so it cannot
"improve" its score by loosening the evaluator. Rubric changes remain human decisions, re-validated by calibrate.py."""
from __future__ import annotations
import collections, json, re
from pathlib import Path
from src.context import build_context, rules_to_text
from src.llm import provider
from src.memory import store
from src.nodes import generator
from src.nodes.evaluator import evaluate
from src.nodes.feedback import FIX_HINTS

ROOT = Path(__file__).resolve().parents[2]

def _out() -> Path:
    """Where docs/ and data/ outputs go. Tests redirect this so they never overwrite real evidence files."""
    import os
    return Path(os.environ.get("LESSONFORGE_OUT") or ROOT)

# ---------------- 1. propose ----------------
def write_rule(check_id: str, evidence: list[dict], feedback: list[dict], check_name: str) -> str:
    ex = "\n".join(f'- why it failed: {e["reason"][:220]} | offending text: "{e["evidence"][:160]}"' for e in evidence[:5])
    fb = "\n".join(f"- human note: {f['note']}" for f in feedback[:3])
    prompt = ("You improve a lesson-writing prompt. A quality check keeps failing on lessons written for a beginner "
              f"(17-year-old Indian student, limited English).\n\nCHECK {check_id}: {check_name}\n\nRECENT FAILURES:\n{ex}\n{fb}\n\n"
              "Write ONE rule for the writer that would prevent this. It must be: imperative, specific, at most 30 words, "
              "general (do not mention this particular lesson's content), and must not weaken the quality bar. "
              "Reply with the rule text only, on one line.")
    try:
        out = provider.chat("generator", [{"role": "user", "content": prompt}], temperature=0.2, max_tokens=1200)
        line = next((l for l in out.strip().splitlines() if l.strip()), "")
        rule = re.sub(r"^[\s\-\*\u2022\d.)]+", "", line).strip().strip("\"'")[:240]
    except Exception:
        rule = ""
    return rule if len(rule) >= 15 else FIX_HINTS.get(check_id, "Avoid the failure described for this check.")

def propose(min_count: int = 2, min_rate: float = 0.3, max_new: int = 3) -> list[dict]:
    rubric = build_context()["rubric"]
    names = {c["id"]: c["name"] for c in rubric["checks"]}
    stats = store.failure_stats()
    for fb_check in {r["check_id"] for r in _all_feedback()}:        # human notes count double
        stats.setdefault(fb_check, {"fails": 0, "evaluated": 0, "llm_fails": 0})
        stats[fb_check]["fails"] += 2 * len(store.feedback_for(fb_check)); stats[fb_check]["evaluated"] += 1
    taken = {r["check_id"] for r in store.rules(("active", "candidate"))}
    out = []
    for cid, st in sorted(stats.items(), key=lambda kv: -kv[1]["fails"]):
        if cid in taken or st["fails"] < min_count or st["fails"] / max(1, st["evaluated"]) < min_rate:
            continue
        ev, fb = store.evidence_for(cid, 5), store.feedback_for(cid)
        rule = write_rule(cid, ev, fb, names.get(cid, cid))
        meta = {"fails": st["fails"], "evaluated": st["evaluated"], "examples": [e["evidence"][:120] for e in ev[:3]]}
        rid = store.add_rule(cid, rule, "candidate", evidence=json.dumps(meta))
        out.append({"id": rid, "check_id": cid, "rule": rule, "needs_llm": st["llm_fails"] > 0, **meta})
        if len(out) >= max_new:
            break
    return out

def _all_feedback():
    return store._rows("SELECT * FROM human_feedback WHERE check_id != ''")

# ---------------- 2. gate (A/B experiment) ----------------
def _arm(ctx: dict, rules: list[str], n: int, use_llm: bool) -> dict:
    c2 = dict(ctx, rules_text=rules_to_text(rules))
    fails, passes, total, models = collections.Counter(), 0, 0, set()
    for _ in range(n):
        lesson = generator.generate(c2)
        models.add(provider.last_model())            # captured BEFORE evaluate(), which may call a different (judge) model
        res = evaluate(lesson, c2, use_llm=use_llm)
        failed = {r.check_id for r in res if r.verdict == "FAIL"}
        fails.update(failed); total += len(failed); passes += not failed
    return {"n": n, "passes": passes, "total_failed_checks": total, "fails": dict(fails), "models": sorted(models - {""})}

def gate(rule_id: int, n: int = 3, use_llm: bool = False) -> dict:
    """Accept only if: target check fails LESS often with the rule, AND total failed checks do not increase,
    AND passes do not decrease. If the target never failed in the baseline sample the result is inconclusive."""
    r = next(x for x in store.rules() if x["id"] == rule_id)
    ctx = build_context(); current = [x["rule"] for x in store.active_rules()]
    base = _arm(ctx, current, n, use_llm); new = _arm(ctx, current + [r["rule"]], n, use_llm)
    t = r["check_id"]; bt, nt = base["fails"].get(t, 0), new["fails"].get(t, 0)
    used = set(base["models"]) | set(new["models"])
    if len(used) > 1:       # e.g. quota exhausted mid-experiment -> fallback model wrote some lessons: comparison is invalid
        decision, why = "candidate", f"inconclusive: experiment confounded, lessons were written by different models {sorted(used)} (quota fallback?). Re-run when the primary generator is available"
    elif bt == 0:
        decision, why = "candidate", f"inconclusive: {t} never failed in the baseline sample of {n}, so improvement cannot be shown"
    elif nt < bt and new["total_failed_checks"] <= base["total_failed_checks"] and new["passes"] >= base["passes"]:
        decision, why = "active", f"{t} failures {bt}->{nt} of {n}; total failed checks {base['total_failed_checks']}->{new['total_failed_checks']}; clean passes {base['passes']}->{new['passes']}"
    else:
        decision, why = "rejected", f"no net improvement: {t} {bt}->{nt}; total failed checks {base['total_failed_checks']}->{new['total_failed_checks']}; clean passes {base['passes']}->{new['passes']}"
    gate_info = {"n": n, "llm_tier": use_llm, "baseline": base, "with_rule": new, "decision": decision, "why": why}
    store.set_rule_status(rule_id, decision, json.dumps(gate_info))
    return gate_info

# ---------------- 3. orchestrate + report ----------------
def reflect(min_count=2, n=3, gate_llm=False, propose_only=False) -> list[dict]:
    results = []
    for cand in propose(min_count=min_count):
        if propose_only:
            results.append({**cand, "decision": "candidate", "why": "propose-only run"}); continue
        if cand["needs_llm"] and not gate_llm:
            why = "needs --gate-llm: this check is judged by the LLM tier, so a fair A/B costs judge tokens"
            store.set_rule_status(cand["id"], "candidate", json.dumps({"decision": "candidate", "why": why}))
            results.append({**cand, "decision": "candidate", "why": why}); continue
        g = gate(cand["id"], n=n, use_llm=cand["needs_llm"])
        results.append({**cand, "decision": g["decision"], "why": g["why"]})
    export_rules(); write_report()
    return results

def export_rules():
    (_out() / "data").mkdir(parents=True, exist_ok=True)
    (_out() / "data/learned_rules.json").write_text(json.dumps(
        [{"id": r["id"], "check_id": r["check_id"], "rule": r["rule"], "status": r["status"]} for r in store.rules()], indent=2))

def write_report():
    stats = store.failure_stats(); md = ["# Self-Evolution Report", "",
        "Rules are written by the reflector from failure memory and activated ONLY if an A/B gate shows improvement. "
        "The evaluator is never modified by this process.", "", "## First-attempt failure rates (deliberate sabotage runs excluded)", "",
        "| Check | Failed first attempts | Times evaluated | Rate |", "|---|---|---|---|"]
    for cid, s in sorted(stats.items(), key=lambda kv: -kv[1]["fails"]):
        md.append(f"| {cid} | {s['fails']} | {s['evaluated']} | {s['fails'] / max(1, s['evaluated']):.0%} |")
    md += ["", "## Learned rules", "", "| # | Check | Status | Rule | Gate result |", "|---|---|---|---|---|"]
    for r in store.rules():
        g = json.loads(r["gate"]).get("why", "") if r["gate"] else ""
        md.append(f"| {r['id']} | {r['check_id']} | {r['status']} | {r['rule'].replace('|', '/')} | {g.replace('|', '/')} |")
    md += ["", "## Outcome by prompt version and learned-rules version (before/after)", "",
           "| Prompt | Rules version | LLM judge | Runs | Passed on first try | Avg attempts |", "|---|---|---|---|---|---|"]
    for p in store.pass_rate_by_rules_version():
        md.append(f"| {p['prompt_version']} | {p['rules_version']} | {'yes' if p['use_llm'] else 'no (deterministic only)'} | {p['runs']} | {p['first_try_passes']} | {p['avg_attempts']} |")
    md += ["", "Small samples: treat these numbers as evidence of direction, not statistical proof."]
    (_out() / "docs").mkdir(parents=True, exist_ok=True)
    (_out() / "docs/EVOLUTION.md").write_text("\n".join(md), encoding="utf-8")
