"""Run once after filling .env:  python scripts/smoke_test.py   (tests BOTH roles even if one fails)"""
import os, sys; sys.path.insert(0, ".")
from src.llm.provider import chat, _chain, KEY_ENV
print("Resolved config (from .env, which overrides shell variables):")
for role in ("generator", "judge"):
    print(f"  {role}: {_chain(role)}")
for prov, env in KEY_ENV.items():
    if env and os.environ.get(env):
        print(f"  {env}: set (…{os.environ[env][-4:]})")
print()
ok = True
for role in ("generator", "judge"):
    try:
        out = chat(role, [{"role": "user", "content": 'Reply with this JSON object and nothing else: {"ok": true}'}], json_mode=True)
        print(f"[PASS] {role} -> {out.strip()[:80]}")
    except Exception as e:
        ok = False
        print(f"[FAIL] {role}:\n{e}\n")
print("ALL GOOD" if ok else "Fix the FAIL lines above (tip: python scripts/list_models.py groq)")
