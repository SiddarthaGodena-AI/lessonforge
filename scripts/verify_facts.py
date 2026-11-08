"""Interactive fact-sheet verification:  python scripts/verify_facts.py
For each unverified fact: open its source, find a supporting sentence, then answer v (verified), e (edit text, then verified),
d (delete - a fact you cannot support must not stay in the sheet) or s (skip). Saves after every answer."""
import json, sys, time
from pathlib import Path
P = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1] / "data/fact_sheet.json"
d = json.loads(P.read_text())
src = d["sources"]
todo = [f for f in d["facts"] if not f.get("verified")]
print(f"{len(todo)} unverified facts. Sources:")
for k, v in src.items(): print(f"  {k}: {v['title']}\n      {v['url']}")
for f in list(todo):
    s = src.get(f["source"], {})
    print(f"\n[{f['id']}] {f['claim']}\n   source {f['source']}: {s.get('title','?')}  {s.get('url','')}")
    while True:
        a = input("   (v)erified / (e)dit / (d)elete / (s)kip > ").strip().lower()[:1]
        if a == "v": f["verified"] = True; f["verified_on"] = time.strftime("%Y-%m-%d"); break
        if a == "e": f["claim"] = input("   new text > ").strip() or f["claim"]; f["verified"] = True; f["verified_on"] = time.strftime("%Y-%m-%d"); break
        if a == "d": d["facts"].remove(f); break
        if a == "s": break
    P.write_text(json.dumps(d, indent=2))
left = [f["id"] for f in d["facts"] if not f.get("verified")]
print(f"\nSaved. Verified: {sum(1 for f in d['facts'] if f.get('verified'))}  Still unverified: {left or 'none'}")
