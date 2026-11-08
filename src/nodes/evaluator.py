from __future__ import annotations
import os
from src.checks.deterministic import run_deterministic
from src.checks.llm_checks import run_llm_checks
from src.checks.claim_verify import run_claim_verification

def evaluate(lesson: str, ctx: dict, use_llm: bool = True):
    """Tier 1 (free, instant) always runs. Tier 2 (LLM, costs tokens) runs only if tier 1 is clean:
    there is no point judging analogy quality in a lesson that is missing a whole section.
    Set LLM_GATE=0 to run both tiers always (full calibration)."""
    res = run_deterministic(lesson, ctx["rubric"], ctx["blueprint"]["required_terms"])
    gate = os.environ.get("LLM_GATE", "1") != "0"
    if use_llm and not (gate and any(r.verdict == "FAIL" for r in res)):
        res += run_claim_verification(lesson, ctx)
        res += run_llm_checks(lesson, ctx, ctx["rubric"])
    return res
