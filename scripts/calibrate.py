"""Run the FULL evaluator (deterministic + LLM judge) on the golden good lesson and every seeded-flaw lesson.
Writes docs/CALIBRATION.md. Results are cached per (lesson + prompts + rubric + facts) so a crash or rate-limit
doesn't lose progress, and editing any prompt/rubric automatically re-runs. Usage:
    python scripts/calibrate.py [--only name1,name2] [--det-only] [--fresh]"""
import argparse, hashlib, json, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from src.context import build_context
from src.nodes.evaluator import evaluate
from src.schemas import CheckResult

ap = argparse.ArgumentParser(); ap.add_argument("--only", default=""); ap.add_argument("--det-only", action="store_true")
ap.add_argument("--fresh", action="store_true")
ap.add_argument("--quick", action="store_true", help="GOOD + only the LLM-tier flaws (deterministic flaws are already proven by pytest) - saves tokens")
a = ap.parse_args()
G = ROOT / "tests/golden"; man = json.loads((G / "manifest.json").read_text()); ctx = build_context()
CACHE = ROOT / "outputs/calibration_cache.json"
cache = {} if a.fresh or not CACHE.exists() else json.loads(CACHE.read_text())

def fingerprint(lesson: str) -> str:
    h = hashlib.sha1(lesson.encode())
    for f in sorted((ROOT / "prompts").rglob("*.md")) + [ROOT / "rubric/rubric.yaml", ROOT / "data/fact_sheet.json", ROOT / "data/blueprint_rag.json"]:
        h.update(f.read_bytes())
    h.update(str(a.det_only).encode())
    return h.hexdigest()

only = {x for x in a.only.split(",") if x}
jobs = [("GOOD (should pass everything)", G / man["good"], set(), set(), "-")]
jobs += [(n, G / m["file"], set(m["expected_fail"]), set(m.get("also_ok", [])), m["tier"])
         for n, m in man["flawed"].items() if (not only or n in only) and not (a.quick and m["tier"] == "det")]
rows = []
for name, path, expected, also_ok, tier in jobs:
    lesson = path.read_text(); key = f"{name}:{fingerprint(lesson)}"
    t0 = time.time()
    if key in cache:
        res = [CheckResult(**r) for r in cache[key]]; src = "cached"
    else:
        res = evaluate(lesson, ctx, use_llm=not a.det_only); src = f"{time.time() - t0:.0f}s"
        cache[key] = [r.model_dump() for r in res]; CACHE.write_text(json.dumps(cache))   # save after EVERY lesson
    failed = {r.check_id for r in res if r.verdict == "FAIL"}
    caught = expected <= failed if expected else not failed
    legit = sorted((failed - expected) & also_ok); unexpected = sorted(failed - expected - also_ok)
    rows.append((name, tier, ",".join(sorted(expected)) or "none", "YES" if caught else "NO", ",".join(legit) or "-", ",".join(unexpected) or "-"))
    print(f"{name:34} expected={sorted(expected)} failed={sorted(failed)} caught={caught} ({src})")
    for r in res:                                   # show WHY for anything unexpected: this is how we tune the judge
        if r.verdict == "FAIL" and r.check_id not in expected and r.check_id not in also_ok:
            print(f"      unexpected {r.check_id} [{r.component}]: {r.reason[:220]}\n          evidence: {r.evidence[:160]}")
flawed = [r for r in rows[1:] if not (a.det_only and r[1] == "llm")]
n_caught = sum(r[3] == "YES" for r in flawed); n_fp = sum(r[5] != "-" for r in rows)
md = ["# Evaluator Calibration", "", f"Mode: {'deterministic only' if a.det_only else 'deterministic + LLM judge'}. "
      "Each seeded lesson = the good lesson with exactly ONE flaw.", "",
      "| Seeded flaw | Caught by | Expected failing check | Caught? | Also failed, legitimately | Unexpected failures (false positives) |",
      "|---|---|---|---|---|---|"] + [f"| {' | '.join(r)} |" for r in rows]
md += ["", f"**Catch rate:** {n_caught}/{len(flawed)} seeded flaws caught.",
       f"**Lessons with unexpected failures:** {n_fp} of {len(rows)} (the GOOD row must be '-').", "",
       "'Also failed, legitimately' = a check that the flaw really does violate (e.g. a jargon dump also leaves jargon unexplained). "
       "Unexpected failures are possible judge false positives; record what you changed to fix each one in DESIGN_DECISIONS.md."]
(ROOT / "docs/CALIBRATION.md").write_text("\n".join(md), encoding="utf-8")
print(f"\nCatch rate {n_caught}/{len(flawed)}; lessons with unexpected failures: {n_fp}. Wrote docs/CALIBRATION.md")
