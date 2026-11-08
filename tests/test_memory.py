"""Memory + reflector tests with a fake LLM. The fake writer obeys an injected rule only if the rule text is in the prompt."""
import json, time
from pathlib import Path
from contextlib import closing
import pytest
from src.llm import provider
from src.graph import build_graph
from src.memory import store
from src.nodes import reflector
from src.context import build_context
from tests.golden.flaws import FLAWS

GOOD = (Path(__file__).parent / "golden/good_lesson.md").read_text()
IDIOM = FLAWS["idiom"][0](GOOD)
RULE = "Never use idioms such as piece of cake; use plain literal words."

def fake(obeys_rule=True, always_good=False):
    def f(role, messages, **kw):
        text = messages[-1]["content"]
        if role == "generator":
            if text.startswith("You improve a lesson-writing prompt"):
                return RULE
            if always_good or (obeys_rule and RULE in text):
                return GOOD
            return IDIOM
        return json.dumps({"claims": []}) if "list the factual claims" in text else json.dumps({"results": []})
    return f

def one_run(monkeypatch, f, sabotage=None):
    monkeypatch.setattr(provider, "chat", f)
    s = build_graph().invoke({"topic": "Intro to RAG", "max_retries": 0, "use_llm": False, "sabotage": sabotage}, {"recursion_limit": 40})
    s["models_used"] = ["fake:model"]
    return s, store.record_run(s, use_llm=False)

def seed_check_failure(check_id, component, runs=3):
    with closing(store.connect()) as c:
        for _ in range(runs):
            cur = c.execute("INSERT INTO runs(ts,topic,status,attempts,prompt_version,rules_version,models,sabotage,use_llm) VALUES(?,?,?,?,?,?,?,?,?)",
                            (time.time(), "t", "PASSED", 1, "v1", "r0", "", "", 1))
            c.execute("INSERT INTO attempts(run_id,n,passed,llm_skipped,failed_ids) VALUES(?,?,?,?,?)", (cur.lastrowid, 1, 0, 0, check_id))
            c.execute("INSERT INTO check_results(run_id,attempt_n,check_id,component,verdict,reason,evidence) VALUES(?,?,?,?,?,?,?)",
                      (cur.lastrowid, 1, check_id, component, "FAIL", "term 'weights' not explained", "the model's weights"))
        c.commit()

def test_run_is_recorded_and_stats_computed(monkeypatch):
    for _ in range(3): one_run(monkeypatch, fake(obeys_rule=False))
    st = store.failure_stats()
    assert st["B3"]["fails"] == 3 and st["B3"]["evaluated"] == 3
    assert "E1" not in st or st["E1"]["fails"] == 0

def test_sabotage_runs_are_never_learned_from(monkeypatch):
    one_run(monkeypatch, fake(always_good=True), sabotage="jargon")
    assert store.failure_stats() == {}          # B1/B2 failed, but only because we injected them on purpose

def test_helpful_rule_is_activated_and_injected(monkeypatch):
    for _ in range(3): one_run(monkeypatch, fake())
    res = reflector.reflect(min_count=2, n=2)
    assert len(res) == 1 and res[0]["check_id"] == "B3" and res[0]["decision"] == "active"
    ctx = build_context()
    assert RULE in ctx["rules_text"] and ctx["rules_version"] != "r0"
    assert json.loads(store.rules()[0]["gate"])["baseline"]["fails"]["B3"] == 2      # evidence stored with the decision
    assert "Learned rules" in (reflector._out() / "docs/EVOLUTION.md").read_text()

def test_useless_rule_is_rejected(monkeypatch):
    for _ in range(3): one_run(monkeypatch, fake(obeys_rule=False))
    res = reflector.reflect(min_count=2, n=2)
    assert res[0]["decision"] == "rejected"
    assert build_context()["rules_version"] == "r0" and store.active_rules() == []

def test_inconclusive_when_problem_never_reproduces(monkeypatch):
    monkeypatch.setattr(provider, "chat", fake(always_good=True))
    rid = store.add_rule("B3", RULE, "candidate")
    g = reflector.gate(rid, n=2)
    assert g["decision"] == "candidate" and "inconclusive" in g["why"]
    assert store.active_rules() == []

def test_llm_tier_rule_waits_for_explicit_gate_flag(monkeypatch):
    seed_check_failure("C1", "llm", runs=3)
    monkeypatch.setattr(provider, "chat", fake(always_good=True))
    res = reflector.reflect(min_count=2, n=2, gate_llm=False)
    assert res[0]["check_id"] == "C1" and res[0]["decision"] == "candidate" and "--gate-llm" in res[0]["why"]
    assert store.active_rules() == []           # never injected unvalidated

def test_one_rule_per_check_and_human_feedback_counts(monkeypatch):
    monkeypatch.setattr(provider, "chat", fake(always_good=True))
    store.add_feedback("Explain the word 'weights'", check_id="C1")
    store.add_feedback("Still unexplained jargon", check_id="C1")
    first = reflector.propose(min_count=2)
    assert [c["check_id"] for c in first] == ["C1"]
    assert reflector.propose(min_count=2) == []  # already has a candidate: no duplicates

def test_rules_are_capped_in_prompt(monkeypatch):
    for i in range(12): store.add_rule(f"X{i}", f"rule number {i}", "active")
    ctx = build_context()
    assert ctx["rules_text"].count("\n") + 1 == 8 and "rule number 11" in ctx["rules_text"] and "rule number 0" not in ctx["rules_text"]

def test_before_after_table(monkeypatch):
    one_run(monkeypatch, fake(obeys_rule=False))
    store.add_rule("B3", RULE, "active")
    one_run(monkeypatch, fake())
    rows = store.pass_rate_by_rules_version()
    assert len(rows) == 2 and rows[0]["rules_version"] == "r0" and rows[1]["rules_version"] != "r0"
    assert rows[0]["first_try_passes"] == 0 and rows[1]["first_try_passes"] == 1

def test_gate_refuses_confounded_experiment(monkeypatch):
    """If the primary model runs out and a fallback writes some lessons, the A/B comparison is invalid -> inconclusive."""
    for _ in range(3): one_run(monkeypatch, fake(obeys_rule=False))
    inner = fake()
    counter = {"n": 0}
    def alternating(role, messages, **kw):
        out = inner(role, messages, **kw)
        if role == "generator" and not messages[-1]["content"].startswith("You improve"):
            counter["n"] += 1
            provider.LAST.clear(); provider.LAST.update({"provider": "gemini" if counter["n"] % 2 else "groq", "model": "m"})
        return out
    monkeypatch.setattr(provider, "chat", alternating)
    res = reflector.reflect(min_count=2, n=2)
    assert res[0]["decision"] == "candidate" and "confounded" in res[0]["why"]
    assert store.active_rules() == []

def test_reset_clears_memory(monkeypatch):
    one_run(monkeypatch, fake(always_good=True)); store.add_rule("B3", "x", "active")
    store.reset()
    assert store.rules() == [] and store.failure_stats() == {}

def test_prompt_v2_is_complete_and_differs_only_in_generator():
    import filecmp
    from src.prompts import ROOT as PR
    v1, v2 = PR / "prompts/v1", PR / "prompts/v2"
    assert {f.name for f in v1.glob("*.md")} == {f.name for f in v2.glob("*.md")}
    changed = [f.name for f in v1.glob("*.md") if not filecmp.cmp(f, v2 / f.name, shallow=False)]
    assert changed == ["generator.md"]               # evaluator prompts untouched: the bar did not move
    assert "ONE bold phrase" in (v2 / "generator.md").read_text()

def test_relative_db_path_resolves_against_project_root(monkeypatch):
    monkeypatch.setenv("LESSONFORGE_DB", "data/memory_lab.db")
    assert store.db_path() == store.ROOT / "data/memory_lab.db"
    monkeypatch.setenv("LESSONFORGE_DB", "/abs/place/m.db")
    assert str(store.db_path()).endswith("m.db") and store.db_path().is_absolute()
