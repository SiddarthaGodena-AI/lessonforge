"""Token usage so far, per model:  python scripts/usage_report.py   (Groq free tier: check your daily token limit per model)"""
import json, sys, collections, time
from pathlib import Path
f = Path(__file__).resolve().parents[1] / "outputs/usage.jsonl"
if not f.exists(): sys.exit("no usage logged yet")
tot = collections.defaultdict(lambda: [0, 0, 0, 0, 0]); cutoff = time.time() - 24 * 3600
for ln in f.read_text().splitlines():
    r = json.loads(ln)
    if r["t"] < cutoff: continue
    k = f'{r["provider"]}:{r["model"]} ({r["role"]})'
    tot[k][0] += 1; tot[k][1] += r.get("in") or 0; tot[k][2] += r.get("out") or 0; tot[k][3] += r.get("reasoning") or 0; tot[k][4] += r.get("finish") == "length"
print("Last 24h (this machine's log only):")
for k, (n, i, o, rs, tr) in sorted(tot.items()):
    print(f"  {k:50} calls={n:4} in={i:7} out={o:7} (reasoning={rs}) total={i + o:7} truncated={tr}")

ex = f.parent / "exhausted.json"
if ex.exists():
    d = json.loads(ex.read_text()); live = {k: v for k, v in d.items() if v > time.time()}
    if live:
        print("\nQuota cool-downs (these models are skipped until then; delete outputs/exhausted.json after your quota resets):")
        for k, v in live.items():
            print(f"  {k}: until {time.strftime('%Y-%m-%d %H:%M', time.localtime(v))}")
