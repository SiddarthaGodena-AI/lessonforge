"""Lists the model IDs YOUR key can actually use.  Usage:
   python scripts/list_models.py groq
   python scripts/list_models.py gemini
   python scripts/list_models.py openrouter      (prints only ':free' models)"""
import sys; sys.path.insert(0, ".")
from src.llm.provider import _client, BASE_URLS
prov = sys.argv[1] if len(sys.argv) > 1 else ""
if prov not in BASE_URLS:
    sys.exit(f"Usage: python scripts/list_models.py {'|'.join(BASE_URLS)}")
ids = sorted(m.id for m in _client(prov).models.list().data)
if prov == "openrouter":
    ids = [i for i in ids if i.endswith(":free")]
for i in ids:
    print(i)
print(f"\n{len(ids)} models. In .env use  {prov}:<id exactly as printed>  (Gemini ids may start with 'models/' -- drop that prefix if it errors)")
