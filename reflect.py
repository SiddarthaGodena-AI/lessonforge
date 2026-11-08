"""Self-evolution CLI.
  python reflect.py stats                       failure rates + before/after table
  python reflect.py run [--n 3] [--gate-llm]    propose rules from failure memory, A/B-gate them, update docs/EVOLUTION.md
  python reflect.py rules                       list rules
  python reflect.py feedback "text" --check C1  add human feedback (counts as extra evidence)
  python reflect.py disable ID | enable ID      manual override
  python reflect.py reset --yes                 wipe memory (e.g. after a contaminated batch of runs)"""
import argparse, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from src.memory import store
from src.nodes import reflector

ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest="cmd", required=True)
sub.add_parser("stats"); sub.add_parser("rules")
r = sub.add_parser("run"); r.add_argument("--n", type=int, default=3); r.add_argument("--min-count", type=int, default=2)
r.add_argument("--gate-llm", action="store_true"); r.add_argument("--propose-only", action="store_true")
f = sub.add_parser("feedback"); f.add_argument("note"); f.add_argument("--check", default=""); f.add_argument("--run", type=int)
rs = sub.add_parser("reset"); rs.add_argument("--yes", action="store_true")
for n in ("disable", "enable"): sub.add_parser(n).add_argument("id", type=int)
a = ap.parse_args()

if a.cmd == "stats":
    for cid, s in sorted(store.failure_stats().items(), key=lambda kv: -kv[1]["fails"]):
        print(f"{cid:3} failed {s['fails']}/{s['evaluated']} first attempts ({s['fails'] / max(1, s['evaluated']):.0%})")
    print("\nprompt | rules_version | llm | runs | first-try passes | avg attempts")
    for p in store.pass_rate_by_rules_version():
        print(f"{p['prompt_version']:6} {p['rules_version']:10} {p['use_llm']} {p['runs']:4} {p['first_try_passes']:4} {p['avg_attempts']}")
elif a.cmd == "rules":
    for x in store.rules(): print(f"#{x['id']} [{x['status']}] {x['check_id']}: {x['rule']}")
elif a.cmd == "run":
    res = reflector.reflect(min_count=a.min_count, n=a.n, gate_llm=a.gate_llm, propose_only=a.propose_only)
    if not res: print("No check has failed often enough yet (need >= min-count first-attempt failures). Run more: python run.py --repeat 5")
    for x in res: print(f"#{x['id']} {x['check_id']} -> {x['decision'].upper()}\n    rule: {x['rule']}\n    {x['why']}")
    print("\nWrote docs/EVOLUTION.md and data/learned_rules.json")
elif a.cmd == "feedback":
    print(f"saved feedback #{store.add_feedback(a.note, a.check, a.run)}")
elif a.cmd == "reset":
    if not a.yes: sys.exit("This deletes ALL runs, rules and feedback. Re-run with --yes to confirm.")
    store.reset(); reflector.export_rules(); print("memory cleared")
else:
    store.set_rule_status(a.id, "active" if a.cmd == "enable" else "rejected"); reflector.export_rules(); reflector.write_report(); print("ok")
