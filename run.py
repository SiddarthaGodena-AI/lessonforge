"""python run.py --topic "Introduction to RAG" [--sabotage factual|jargon|forward_ref|unsupported] [--max-retries 2] [--no-llm-judge]"""
import argparse, shutil, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from src.graph import build_graph
from src.llm import provider
from src.nodes.publish import write_outputs
from src.memory import store

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--topic", default="Introduction to RAG")
    ap.add_argument("--sabotage", default=None, help="inject a deliberate flaw into attempt 1 (demo)")
    ap.add_argument("--max-retries", type=int, default=2)
    ap.add_argument("--repeat", type=int, default=1, help="run the pipeline N times (builds failure memory)")
    ap.add_argument("--no-memory", action="store_true", help="do not record this run in memory")
    ap.add_argument("--no-llm-judge", action="store_true", help="deterministic checks only (offline debugging)")
    a = ap.parse_args()
    try:
        from src.prompts import version
        print(f"[config] generator chain={provider._chain('generator')}  judge chain={provider._chain('judge') if not a.no_llm_judge else 'off'}  "
              f"prompt={version()}  memory={store.db_path().name}")
    except Exception as e:
        print(f"[config] could not read settings: {e}")
    for k in range(a.repeat):
        t0 = time.time()
        if a.repeat > 1:
            print(f"\n=== run {k + 1} of {a.repeat} ===")
        one_run(a, t0)

def one_run(a, t0):
    state = build_graph().invoke({"topic": a.topic, "sabotage": a.sabotage, "max_retries": a.max_retries,
                                  "use_llm": not a.no_llm_judge}, {"recursion_limit": 40})
    state["models_used"] = sorted(provider.MODELS_USED)
    out = Path("outputs") / time.strftime("run_%Y%m%d_%H%M%S")
    write_outputs(state, out)
    for f in ("lesson.md", "rejection_log.md", "rejection_log.json"):
        shutil.copy(out / f, Path("outputs") / f)
    print(f"\nStatus: {state['status']} after {len(state['attempts'])} attempt(s) in {time.time() - t0:.0f}s")
    for at in state["attempts"]:
        print(f"  attempt {at.attempt}: {'PASS' if at.passed else 'FAIL ' + ','.join(at.failed_ids)}"
              + ("  (LLM judge skipped: deterministic checks failed first)" if at.llm_skipped else ""))
        for r in at.results:
            if r.verdict == "FAIL":
                print(f"      {r.check_id}: {r.reason[:230]}")
    print(f"Outputs: {out}  (copies in outputs/)")
    fallback = sorted(set(state["models_used"]) - provider.primary_models())
    if fallback:
        print(f"WARNING: fallback model(s) answered during this run: {', '.join(fallback)}. "
              "Results are NOT comparable with runs that used only your primary models; the log records which attempt used which.")
    if not a.no_memory:
        rid = store.record_run(state, use_llm=not a.no_llm_judge)
        print(f"Memory: recorded run #{rid}; learned-rules version {state['ctx']['rules_version']} "
              f"({len(store.active_rules())} active rule(s))")
    if state.get("unverified_facts"):
        print(f"WARNING: {len(state['unverified_facts'])} fact-sheet facts are unverified - verify before submitting.")

if __name__ == "__main__":
    main()
