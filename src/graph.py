"""LangGraph state machine:  plan -> generate -> evaluate -> (publish | feedback -> generate | escalate)"""
from __future__ import annotations
from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from src.context import build_context
from src.nodes import generator
from src.nodes.evaluator import evaluate
from src.nodes.feedback import build_fix_brief, diff_summary
from src.nodes.sabotage import apply_sabotage
from src.llm import provider
from src.prompts import version
from src.schemas import AttemptRecord
from src.util import evidence_still_present

class S(TypedDict, total=False):
    topic: str; blueprint: dict; rubric: dict; ctx: dict
    lesson: str; prev_lesson: str; sabotage: str | None; sabotage_note: str
    attempts: list; fix_brief: str; max_retries: int; use_llm: bool
    status: str; final_lesson: str; unverified_facts: list; gen_model: str; stagnated: bool

def plan(s: S):
    ctx = build_context()
    return {"ctx": ctx, "rubric": ctx["rubric"], "blueprint": ctx["blueprint"], "attempts": [],
            "fix_brief": "", "unverified_facts": ctx["unverified_facts"]}

def offending_text_untouched(rec, new_lesson: str) -> bool:
    """True if EVERY passage the fix brief quoted as evidence is still verbatim in the revised lesson, i.e. the model
    did not touch what it was told to fix. (Overall similarity cannot detect this: a correct fix is also ~99% identical.)"""
    ev = [r.evidence for r in rec.results if r.verdict == "FAIL" and not r.evidence.startswith("[")]
    verdicts = [v for v in (evidence_still_present(e, new_lesson) for e in ev) if v is not None]
    return bool(verdicts) and all(verdicts)

def needs_rewrite(prev_lesson: str, rec, rubric) -> bool:
    """Patching only works on a basically-complete lesson. If it is far too short, or the whole structure is missing, rewrite."""
    import re
    n_words = len(re.findall(r"\w+", prev_lesson))
    structural = {"E1", "F1", "F2"} <= set(rec.failed_ids)
    return n_words < 0.5 * rubric["thresholds"]["min_words"] or structural

def generate(s: S):
    n = len(s["attempts"]) + 1
    stagnated = False
    if n == 1:
        lesson = generator.generate(s["ctx"])
    elif needs_rewrite(s["lesson"], s["attempts"][-1], s["rubric"]):     # too broken to patch: write again from scratch
        lesson = generator.generate(s["ctx"], retry_note=s["fix_brief"])
    else:
        lesson = generator.revise(s["ctx"], s["lesson"], s["fix_brief"])
        if offending_text_untouched(s["attempts"][-1], lesson):          # model ignored the fix brief
            lesson = generator.generate(s["ctx"], retry_note=s["fix_brief"])
            stagnated = True
    note = ""
    if n == 1 and s.get("sabotage"):
        lesson, note = apply_sabotage(lesson, s["sabotage"])
    return {"prev_lesson": s.get("lesson", ""), "lesson": lesson, "sabotage_note": note,
            "gen_model": provider.last_model(), "stagnated": stagnated}

def evaluate_node(s: S):
    results = evaluate(s["lesson"], s["ctx"], use_llm=s.get("use_llm", True))
    n = len(s["attempts"]) + 1
    rec = AttemptRecord(attempt=n, prompt_version=version(), rubric_version=s["rubric"]["version"],
                        results=results, lesson=s["lesson"], sabotage_note=s.get("sabotage_note", ""),
                        llm_skipped=bool(s.get("use_llm", True)) and not any(r.component == "llm" for r in results),
                        generator_model=s.get("gen_model", ""))
    if n > 1:
        rec.diff_summary = diff_summary(s["prev_lesson"], s["lesson"])
        if s.get("stagnated"):
            rec.diff_summary = ("STAGNATION GUARD: the revision left every passage quoted in the fix brief unchanged (the model ignored "
                                "the fix brief), so the lesson was rewritten from scratch. ") + rec.diff_summary
        prev_failed = set(s["attempts"][-1].failed_ids)
        rec.regressions = sorted(set(rec.failed_ids) - prev_failed)
    return {"attempts": s["attempts"] + [rec]}

def route(s: S) -> str:
    rec = s["attempts"][-1]
    if rec.passed:
        return "publish"
    return "escalate" if len(s["attempts"]) > s["max_retries"] else "feedback"

def feedback(s: S):
    brief = build_fix_brief(s["attempts"][-1].results, s["rubric"])
    s["attempts"][-1].fix_brief = brief
    return {"fix_brief": brief}

def publish(s: S):
    return {"status": "PASSED", "final_lesson": s["attempts"][-1].lesson}

def escalate(s: S):
    crit = {c["id"] for c in s["rubric"]["checks"] if c["critical"]}
    best = min(s["attempts"], key=lambda a: (len(set(a.failed_ids) & crit), len(a.failed_ids)))
    return {"status": "NEEDS_HUMAN_REVIEW", "final_lesson": best.lesson}

def build_graph():
    g = StateGraph(S)
    for name, fn in [("plan", plan), ("generate", generate), ("evaluate", evaluate_node),
                     ("feedback", feedback), ("publish", publish), ("escalate", escalate)]:
        g.add_node(name, fn)
    g.add_edge(START, "plan"); g.add_edge("plan", "generate"); g.add_edge("generate", "evaluate")
    g.add_conditional_edges("evaluate", route, {"publish": "publish", "feedback": "feedback", "escalate": "escalate"})
    g.add_edge("feedback", "generate"); g.add_edge("publish", END); g.add_edge("escalate", END)
    return g.compile()
