import pytest
from pathlib import Path
from src.checks.deterministic import run_deterministic
from tests.golden.flaws import FLAWS

GOOD = (Path(__file__).parent / "golden/good_lesson.md").read_text()
DET = {k: v for k, v in FLAWS.items() if v[1] == "det"}

def failed(md): return {r.check_id for r in run_deterministic(md) if r.verdict == "FAIL"}

def test_good_lesson_passes_all_deterministic_checks():
    assert failed(GOOD) == set()

@pytest.mark.parametrize("name", DET)
def test_seeded_flaw_is_caught(name):
    fn, _, expected = DET[name]
    got = failed(fn(GOOD))
    assert expected <= got, f"{name}: expected {expected} to fail, got {got}"

@pytest.mark.parametrize("name", DET)
def test_flaw_does_not_cause_unrelated_cascade(name):
    """A single seeded flaw shouldn't light up half the rubric (guards against over-strict checks)."""
    fn, _, expected = DET[name]
    assert len(failed(fn(GOOD)) - expected) <= 2

def test_c2_ignores_headings_and_glossary():
    assert "C2" not in failed(GOOD)   # 'RAG' appears in headings/title before its bold definition

def test_c2_accepts_term_inside_bold_phrase():
    """LLMs often write **Large language model (LLM)** - the term is inside the bold span and IS a definition."""
    md = GOOD.replace("an **LLM**, which means large language model.", "a **large language model (LLM)**.")
    assert md != GOOD and "C2" not in failed(md)

def test_c2_still_rejects_plain_first_use():
    md = GOOD.replace("an **LLM**, which means large language model.", "an LLM, which means large language model.")
    assert "C2" in failed(md)
