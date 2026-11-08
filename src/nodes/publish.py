from __future__ import annotations
import json
from pathlib import Path

def _row(r, crit):
    ev = (r.evidence or "").replace("\n", " ").replace("|", "/")[:160]
    return f"| {r.check_id}{' (critical)' if crit.get(r.check_id) else ''} | {r.component} | {r.reason.replace('|','/')[:200]} | {ev} |"

def write_outputs(state: dict, run_dir: Path):
    run_dir.mkdir(parents=True, exist_ok=True)
    rubric = state["rubric"]; crit = {c["id"]: c["critical"] for c in rubric["checks"]}
    attempts = state["attempts"]; status = state["status"]
    final = state["final_lesson"]
    (run_dir / "lesson.md").write_text(final, encoding="utf-8")
    log = {"topic": state["topic"], "status": status, "attempts_made": len(attempts),
           "max_attempts": state["max_retries"] + 1, "prompt_version": attempts[-1].prompt_version,
           "rubric_version": rubric["version"], "unverified_facts": state.get("unverified_facts", []), "models_used": state.get("models_used", []), "rules_version": state["ctx"].get("rules_version", ""),
           "attempts": [{**a.model_dump(exclude={"lesson"}), "failed_ids": a.failed_ids, "passed": a.passed} for a in attempts]}
    (run_dir / "rejection_log.json").write_text(json.dumps(log, indent=2), encoding="utf-8")
    md = [f"# Rejection Log - {state['topic']}", "",
          f"**Final status:** {status}  |  **Attempts:** {len(attempts)} of {state['max_retries'] + 1} allowed  |  "
          f"**Prompt version:** {attempts[-1].prompt_version}  |  **Learned-rules version:** {state['ctx'].get('rules_version', '')}  |  **Rubric v{rubric['version']}**", ""]
    if state.get("models_used"):
        md += [f"**Models that actually answered:** {', '.join(state['models_used'])}", ""]
    if state.get("unverified_facts"):
        md += [f"> Warning: fact sheet has unverified facts: {', '.join(state['unverified_facts'])}", ""]
    for a in attempts:
        md += [f"## Attempt {a.attempt} - {'PASSED' if a.passed else 'FAILED: ' + ', '.join(a.failed_ids)}"
               + (f"  (written by {a.generator_model})" if a.generator_model else ""), ""]
        if a.llm_skipped:
            md += ["> LLM judge skipped this attempt: deterministic checks failed first (cheap checks gate the expensive ones).", ""]
        if a.sabotage_note:
            md += [f"> {a.sabotage_note}", ""]
        if a.diff_summary:
            md += [f"**What changed vs previous attempt:** {a.diff_summary}", ""]
        if a.regressions:
            md += [f"**Regressions (passed before, fail now):** {', '.join(a.regressions)}", ""]
        fails = [r for r in a.results if r.verdict == "FAIL"]
        if fails:
            md += ["| Check | Tier | Why it failed | Evidence |", "|---|---|---|---|"] + [_row(r, crit) for r in fails] + [""]
        if a.fix_brief:
            md += ["**Fix brief sent to generator:**", "", "```", a.fix_brief, "```", ""]
    md += ["## Outcome", "",
           "Lesson cleared every check." if status == "PASSED" else
           "NEEDS HUMAN REVIEW: retries exhausted. The least-bad attempt is saved as lesson.md; remaining failures are listed above."]
    (run_dir / "rejection_log.md").write_text("\n".join(md), encoding="utf-8")
    return run_dir
