"""Is local Ollama ready to act as a fallback?   python scripts/ollama_check.py [model]
Checks: server reachable, model installed, speed, and whether the context window is big enough for our prompts."""
import os, sys, time
sys.path.insert(0, ".")
from src.llm import provider

host = provider._ollama_host()
model = sys.argv[1] if len(sys.argv) > 1 else next((m for p, m in provider._chain("generator") if p == "ollama"), None) \
    if os.environ.get("GENERATOR") else None
print(f"Ollama host: {host}")
try:
    tags = provider._http_get_json(host + "/api/tags")
except Exception as e:
    sys.exit(f"[FAIL] cannot reach Ollama ({e}). Start the Ollama app (or 'ollama serve') and retry.")
names = [m["name"] for m in tags.get("models", [])]
print("Installed models:", ", ".join(names) or "(none - run: ollama pull llama3.1:8b)")
if not model:
    sys.exit("Pass a model name:  python scripts/ollama_check.py llama3.1:8b   (or put ollama:<model> in GENERATOR in .env)")
reason = provider._ollama_status(model)
if reason:
    sys.exit(f"[FAIL] {reason}")
print(f"[OK] '{model}' is installed")

c = provider._client("ollama")
t0 = time.time()
r = c.chat.completions.create(model=model, messages=[{"role": "user", "content": "Reply with one short sentence about libraries."}], max_tokens=60)
dt = time.time() - t0; out = r.usage.completion_tokens or 1
print(f"[OK] speed: {out} tokens in {dt:.1f}s = {out / dt:.1f} tokens/sec "
      f"(a lesson is ~1500 tokens => about {1500 / (out / dt) / 60:.1f} min per generation)")

filler = ("The library has many books about science and history. " * 300)          # ~3000 tokens
r = c.chat.completions.create(model=model, messages=[{"role": "user", "content": filler + "\nSay OK."}], max_tokens=5)
sent_est, got = len(filler) // 4, r.usage.prompt_tokens
print(f"Context test: sent about {sent_est} tokens, Ollama counted {got}.")
if got < 0.8 * sent_est:
    print("[WARN] context window too small - prompts will be silently cut. Fix (pick one):\n"
          "  1) PowerShell:  setx OLLAMA_CONTEXT_LENGTH 8192   then QUIT Ollama from the tray and start it again\n"
          "  2) Modelfile with 'FROM <model>' and 'PARAMETER num_ctx 8192', then: ollama create lessonforge-8k -f Modelfile\n"
          "     and use ollama:lessonforge-8k in .env")
else:
    print("[OK] context window is large enough for our prompts")
print("\nSuggested .env lines:\n  GENERATOR=gemini:<your-gemini-model>,groq:openai/gpt-oss-20b,ollama:" + model +
      "\n  (Ollama last: it is slow and small local models write weaker lessons; every fallback is flagged in the log)")
