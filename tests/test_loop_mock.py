"""Loop-logic tests with a fake LLM (no network). Live behaviour is checked by scripts/smoke_test.py + calibrate.py."""
import json, re
from pathlib import Path
import pytest
from src.llm import provider
from src.graph import build_graph
from src.nodes.publish import write_outputs
from src.nodes.feedback import build_fix_brief
from src.checks.deterministic import load_rubric
from src.schemas import CheckResult
from src.util import quote_in_text
from tests.golden.flaws import FLAWS

GOOD = (Path(__file__).parent / "golden/good_lesson.md").read_text()
NO_WHY = FLAWS["missing_why"][0](GOOD)

def fake_llm(gen_outputs, judge_fail=None, claims=None, verdicts=None):
    st = {"gen": 0}
    def fake(role, messages, **kw):
        text = messages[-1]["content"]
        if role == "generator":
            i = min(st["gen"], len(gen_outputs) - 1); st["gen"] += 1
            return gen_outputs[i]
        if "Read the lesson and list the factual claims" in text:
            return json.dumps({"claims": claims or []})
        if "You verify claims" in text:
            return json.dumps({"results": verdicts or []})
        out = []
        for cid in re.findall(r"^- ([A-Z]\d\d?): ", text, flags=re.M):
            if judge_fail and cid in judge_fail:
                out.append({"check_id": cid, "verdict": "FAIL", "evidence_quote": judge_fail[cid], "reason": "bad"})
            else:
                out.append({"check_id": cid, "verdict": "PASS", "evidence_quote": "", "reason": "ok"})
        return json.dumps({"results": out})
    return fake

def run(monkeypatch, fake, **kw):
    monkeypatch.setattr(provider, "chat", fake)
    return build_graph().invoke({"topic": "Intro to RAG", "max_retries": 2, "use_llm": True, **kw}, {"recursion_limit": 40})

def test_recovers_on_second_attempt(monkeypatch):
    s = run(monkeypatch, fake_llm([NO_WHY, GOOD]))
    assert s["status"] == "PASSED" and len(s["attempts"]) == 2
    a1, a2 = s["attempts"]
    assert "E1" in a1.failed_ids and "E1" in a1.fix_brief
    assert a2.passed and "why it matters" in a2.diff_summary and a2.regressions == []

def test_escalates_after_retry_cap(monkeypatch):
    s = run(monkeypatch, fake_llm([NO_WHY]))
    assert s["status"] == "NEEDS_HUMAN_REVIEW" and len(s["attempts"]) == 3   # 1 try + 2 retries, then stops

def test_unverifiable_judge_quote_is_flagged_not_trusted(monkeypatch):
    s = run(monkeypatch, fake_llm([GOOD], judge_fail={"D1": "this sentence appears nowhere in the lesson at all"}))
    r = next(r for r in s["attempts"][0].results if r.check_id == "D1")
    assert r.verdict == "FAIL" and r.metrics.get("unverified") is True

def test_verified_judge_quote_is_kept(monkeypatch):
    q = "A small online course called \"Python for Beginners\" has three chunks"
    s = run(monkeypatch, fake_llm([GOOD], judge_fail={"D1": q}))
    r = next(r for r in s["attempts"][0].results if r.check_id == "D1")
    assert r.verdict == "FAIL" and not r.metrics.get("unverified") and "Python for Beginners" in r.evidence

def test_sabotage_is_caught_and_logged(monkeypatch):
    s = run(monkeypatch, fake_llm([GOOD, GOOD]), sabotage="jargon")
    a1 = s["attempts"][0]
    assert not a1.passed and {"B1", "B2"} & set(a1.failed_ids)
    assert "DELIBERATE SABOTAGE" in a1.sabotage_note
    assert s["status"] == "PASSED"

def test_claim_verification_contradicted_claim_fails_a1(monkeypatch):
    sent = "The LLM does not change. The system only adds text to the prompt."
    claims = [{"id": 1, "claim": "RAG retrains the model", "quote": sent}]
    verdicts = [{"id": 1, "status": "contradicted", "specific": False, "fact_id": "F05", "reason": "conflicts F05"}]
    s = run(monkeypatch, fake_llm([GOOD], claims=claims, verdicts=verdicts))
    r = next(r for r in s["attempts"][0].results if r.check_id == "A1")
    assert r.verdict == "FAIL" and r.evidence

def test_unsupported_but_not_specific_claim_is_not_failed(monkeypatch):
    claims = [{"id": 1, "claim": "Files can be PDFs", "quote": "A knowledge base can hold PDF files"}]
    verdicts = [{"id": 1, "status": "unsupported", "specific": False, "fact_id": None, "reason": "n/a"}]
    s = run(monkeypatch, fake_llm([GOOD], claims=claims, verdicts=verdicts))
    assert next(r for r in s["attempts"][0].results if r.check_id == "A2").verdict == "PASS"

def test_outputs_written(monkeypatch, tmp_path):
    s = run(monkeypatch, fake_llm([NO_WHY, GOOD]))
    write_outputs(s, tmp_path)
    md = (tmp_path / "rejection_log.md").read_text()
    assert "Attempt 1" in md and "Attempt 2" in md and "PASSED" in md
    assert json.loads((tmp_path / "rejection_log.json").read_text())["attempts_made"] == 2
    assert (tmp_path / "lesson.md").read_text() == s["final_lesson"]

def test_fix_brief_lists_critical_first():
    rub = load_rubric()
    res = [CheckResult(check_id="B1", verdict="FAIL", reason="long"),
           CheckResult(check_id="C2", verdict="FAIL", reason="undefined", evidence="x")]
    brief = build_fix_brief(res, rub)
    assert brief.index("C2") < brief.index("B1") and "CRITICAL" in brief

def test_quote_verifier():
    assert quote_in_text("**Retrieval** means finding the right information.", GOOD)
    assert not quote_in_text("RAG retrains the model every night without asking", GOOD)

def test_llm_tier_is_gated_by_deterministic_failures(monkeypatch):
    """Cheap checks first: a lesson missing a section must not burn judge tokens."""
    judge_calls = []
    inner = fake_llm([NO_WHY, GOOD])
    def spy(role, messages, **kw):
        if role == "judge": judge_calls.append(len(judge_calls))
        return inner(role, messages, **kw)
    s = run(monkeypatch, spy)
    a1, a2 = s["attempts"]
    assert a1.llm_skipped and not any(r.component == "llm" for r in a1.results)
    assert not a2.llm_skipped and a2.passed
    assert len(judge_calls) == 4          # 1 claim-extraction call (no claims -> verify call skipped) + 3 grouped judge calls, all in attempt 2

def test_gate_can_be_disabled_for_full_calibration(monkeypatch):
    monkeypatch.setenv("LLM_GATE", "0")
    s = run(monkeypatch, fake_llm([NO_WHY, GOOD]))
    assert not s["attempts"][0].llm_skipped and any(r.component == "llm" for r in s["attempts"][0].results)

def test_malformed_attempt_is_rewritten_not_patched(monkeypatch):
    """A 40-word scrap can't be patched into a lesson: attempt 2 must regenerate from scratch (no 'CURRENT LESSON' in prompt)."""
    prompts = []
    inner = fake_llm(["Short scrap. RAG is good.", GOOD])
    def spy(role, messages, **kw):
        if role == "generator": prompts.append(messages[-1]["content"])
        return inner(role, messages, **kw)
    s = run(monkeypatch, spy)
    assert s["status"] == "PASSED" and len(prompts) == 2
    assert "CURRENT LESSON:" not in prompts[1] and "Write the COMPLETE lesson again from scratch" in prompts[1]

def test_nearly_complete_attempt_is_patched_not_rewritten(monkeypatch):
    prompts = []
    inner = fake_llm([FLAWS["idiom"][0](GOOD), GOOD])
    def spy(role, messages, **kw):
        if role == "generator": prompts.append(messages[-1]["content"])
        return inner(role, messages, **kw)
    s = run(monkeypatch, spy)
    assert len(prompts) == 2 and "CURRENT LESSON:" in prompts[1]

def test_stagnation_guard_rewrites_when_model_ignores_fix_brief(monkeypatch):
    """Revision returns the SAME flawed lesson (offending passage untouched) -> next call is a from-scratch rewrite."""
    prompts = []
    inner = fake_llm([FLAWS["idiom"][0](GOOD), FLAWS["idiom"][0](GOOD), GOOD])
    def spy(role, messages, **kw):
        if role == "generator": prompts.append(messages[-1]["content"])
        return inner(role, messages, **kw)
    s = run(monkeypatch, spy)
    assert s["status"] == "PASSED" and len(s["attempts"]) == 2 and len(prompts) == 3
    assert "CURRENT LESSON:" in prompts[1] and "CURRENT LESSON:" not in prompts[2]
    assert s["attempts"][1].diff_summary.startswith("STAGNATION GUARD")

def test_generator_model_is_recorded_per_attempt(monkeypatch):
    inner = fake_llm([NO_WHY, GOOD])
    models = iter(["gemini:flash", "groq:gpt-oss-20b"])
    def spy(role, messages, **kw):
        out = inner(role, messages, **kw)
        if role == "generator":
            provider.LAST.clear(); provider.LAST.update({"provider": next(models).split(":")[0], "model": "x"})
        return out
    s = run(monkeypatch, spy)
    assert [a.generator_model for a in s["attempts"]] == ["gemini:x", "groq:x"]

def test_evidence_matching_ignores_cut_words_and_markdown():
    from src.util import evidence_still_present as present
    lesson = "Something else.\n- In a nutshell, RAG is a piece of cake, but it can still be wrong.\n## Next"
    assert present("er. - In a nutshell, RAG is a piece of cake, but it can still be wrong.  ", lesson) is True
    assert present("er. - In plain words, RAG is a useful method, but it can still be wrong.  ", lesson) is False
    assert present("too short", lesson) is None
