"""Tier-2 evaluator: LLM judge. Binary verdicts, evidence quotes are verified against the lesson text."""
from __future__ import annotations
import json, os
from src.llm import provider
from src.prompts import load, render
from src.schemas import CheckResult
from src.util import parse_json, quote_in_text

# Grouped to save free-tier tokens/requests (set JUDGE_NARROW=1 for one check per call = most precise)
GROUPS = [["A3", "D1", "D2"], ["B3", "C1", "F1"], ["E2"]]

def _judge_group(ids: list[str], lesson: str, ctx: dict, rubric: dict) -> list[CheckResult]:
    spec = {c["id"]: c for c in rubric["checks"]}
    checks_txt = "\n".join(f'- {i}: {spec[i]["name"]}. Question: {spec[i]["question"]}' for i in ids)
    prompt = render(load("judge"), LEARNER=ctx["blueprint"]["learner"], CHECKS=checks_txt,
                    BLUEPRINT=json.dumps({k: ctx["blueprint"][k] for k in ("key_concepts", "required_terms")}),
                    LESSON=lesson)
    out: dict[str, CheckResult] = {}
    nudge = ""
    for attempt in range(2):
        raw = provider.chat("judge", [{"role": "user", "content": prompt + nudge}], temperature=0.0, json_mode=True, max_tokens=2500, cache=True)
        try:
            items = parse_json(raw)["results"]
        except Exception:
            nudge = "\n\nYour last reply was not valid JSON in the required shape. Return ONLY the JSON object."
            continue
        retry_ids = []
        for it in items:
            cid = str(it.get("check_id", "")).strip()
            if cid not in ids or cid in out:
                continue
            verdict = str(it.get("verdict", "")).upper()
            quote, reason = str(it.get("evidence_quote", "")).strip(), str(it.get("reason", "")).strip()
            if verdict == "PASS":
                out[cid] = CheckResult(check_id=cid, component="llm", verdict="PASS", reason=reason or "ok")
            elif quote and quote_in_text(quote, lesson):
                out[cid] = CheckResult(check_id=cid, component="llm", verdict="FAIL", reason=reason, evidence=quote)
            elif attempt == 0:
                retry_ids.append(cid)           # FAIL without verifiable evidence -> ask once more
            else:
                out[cid] = CheckResult(check_id=cid, component="llm", verdict="FAIL",
                                       reason=reason + " [evidence quote could not be verified in lesson]",
                                       evidence=quote or "[no quote provided]", metrics={"unverified": True})
        missing = [i for i in ids if i not in out and i not in retry_ids]
        if not retry_ids and not missing:
            break
        nudge = ("\n\nFix your reply: " + (f"for {retry_ids} copy an EXACT passage from the lesson as evidence_quote. " if retry_ids else "")
                 + (f"Include entries for {missing}. " if missing else "") + "Return the full JSON object again.")
    for i in ids:                               # judge never answered -> fail safe, visibly
        out.setdefault(i, CheckResult(check_id=i, component="llm", verdict="FAIL",
                       reason="Judge returned no valid verdict for this check", evidence="[judge error]",
                       metrics={"judge_error": True}))
    return [out[i] for i in ids]

def run_llm_checks(lesson: str, ctx: dict, rubric: dict) -> list[CheckResult]:
    groups = [[i] for g in GROUPS for i in g] if os.environ.get("JUDGE_NARROW") == "1" else GROUPS
    res: list[CheckResult] = []
    for g in groups:
        res += _judge_group(g, lesson, ctx, rubric)
    return res
