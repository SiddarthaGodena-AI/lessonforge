"""One OpenAI-compatible client for every free provider. Switch providers via .env only.
NOT yet exercised against live APIs (no keys at build time) -- run scripts/smoke_test.py first."""
from __future__ import annotations
import hashlib, json, os, re, time
from pathlib import Path
from openai import OpenAI, RateLimitError, APIStatusError, APIConnectionError

BASE_URLS = {
    "groq":       "https://api.groq.com/openai/v1",
    "gemini":     "https://generativelanguage.googleapis.com/v1beta/openai/",
    "openrouter": "https://openrouter.ai/api/v1",
    "ollama":     "http://localhost:11434/v1",
}
KEY_ENV = {"groq": "GROQ_API_KEY", "gemini": "GEMINI_API_KEY", "openrouter": "OPENROUTER_API_KEY", "ollama": None}
USAGE_LOG = Path(__file__).resolve().parents[2] / "outputs/usage.jsonl"

ROOT_DIR = Path(__file__).resolve().parents[2]

def _env_file() -> Path:
    """Settings file. Default .env; set LESSONFORGE_ENV=.env.lab in the shell to use a different setup (e.g. all-local experiments)."""
    name = os.environ.get("LESSONFORGE_ENV", ".env")
    return Path(name) if Path(name).is_absolute() else ROOT_DIR / name

def _load_dotenv():
    f = _env_file()
    if f.exists():
        for ln in f.read_text().splitlines():
            if "=" in ln and not ln.strip().startswith("#"):
                k, v = ln.split("=", 1); os.environ[k.strip()] = v.strip().strip('"').strip("'")   # file overrides stale shell vars
        if f.name != ".env":
            print(f"[settings] loaded {f.name}", flush=True)
_load_dotenv()

def _err_text(e) -> str:
    """str(e) plus the HTTP response body: Gemini's 429 message alone says nothing; the body names the exceeded quota."""
    txt = str(e)
    try:
        body = e.response.text or ""
        if body and body[:60] not in txt:
            txt += " " + body
    except Exception:
        pass
    return txt

def _ollama_host() -> str:
    h = os.environ.get("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
    return h if h.startswith("http") else "http://" + h

def _client(provider: str) -> OpenAI:
    env = KEY_ENV[provider]
    key = os.environ.get(env, "") if env else "ollama"
    if not key:
        raise RuntimeError(f"Missing {env} in .env")
    base = _ollama_host() + "/v1" if provider == "ollama" else BASE_URLS[provider]
    return OpenAI(base_url=base, api_key=key, timeout=900 if provider == "ollama" else 120)   # local CPU generation is slow

def _chain(role: str) -> list[tuple[str, str]]:
    """role in {'generator','judge'}. Env: GENERATOR=groq:<model>[,provider:<model>...]"""
    raw = os.environ.get(role.upper(), "")
    if not raw:
        raise RuntimeError(f"Set {role.upper()}=provider:model in .env  (e.g. groq:openai/gpt-oss-120b)")
    out = []
    for x in raw.split(","):
        x = x.strip()
        if not x:
            continue
        prov, sep, model = x.partition(":")
        if not sep or prov not in BASE_URLS:
            raise RuntimeError(f"{role.upper()} entry '{x}' must look like provider:model "
                               f"with provider in {list(BASE_URLS)}. If you set this in PowerShell earlier, "
                               f"run: Remove-Item Env:{role.upper()}")
        out.append((prov, model))
    return out

def _ensure_json_word(messages: list[dict]) -> list[dict]:
    """Groq/OpenAI reject response_format=json_object unless the prompt mentions 'json'."""
    if any("json" in str(m.get("content", "")).lower() for m in messages):
        return messages
    return [{"role": "system", "content": "Respond with a single valid JSON object and nothing else."}] + messages

def _wait_from_message(msg: str, default: float) -> float:
    """Groq: 'try again in 1m2.5s'.  Gemini: 'Please retry in 21.4s' or retryDelay: '21s'."""
    m = re.search(r"(?:try again|retry) in\s+((?:\d+(?:\.\d+)?(?:ms|m|s))+)", msg)
    if m:
        mult = {"ms": 0.001, "s": 1, "m": 60}
        return sum(float(v) * mult[u] for v, u in re.findall(r"(\d+(?:\.\d+)?)(ms|m|s)", m.group(1))) + 1
    m2 = re.search(r"retrydelay\W+(\d+(?:\.\d+)?)s", msg.lower())
    return float(m2.group(1)) + 1 if m2 else default

LAST: dict = {}            # metadata of the most recent call (finish_reason, tokens, model)
MODELS_USED: set = set()   # every provider:model that actually answered this process (goes into the rejection log)
CACHE_FILE = Path(__file__).resolve().parents[2] / "outputs/llm_cache.json"
_CACHE: dict | None = None

def _cache_get(key):
    global _CACHE
    if _CACHE is None:
        try: _CACHE = json.loads(CACHE_FILE.read_text())
        except Exception: _CACHE = {}
    return _CACHE.get(key)

def _cache_put(key, text, model):
    _cache_get(key)
    _CACHE[key] = {"text": text, "model": model}
    CACHE_FILE.parent.mkdir(exist_ok=True)
    CACHE_FILE.write_text(json.dumps(_CACHE))

def _extra_body(provider: str, model: str) -> dict:
    if provider == "gemini":      # hidden 'thinking' can eat the whole token budget; keep it small. GEMINI_REASONING=off disables
        eff = os.environ.get("GEMINI_REASONING", "low").lower()
        return {"reasoning_effort": eff} if eff not in ("", "off") else {}
    return _extra_body_oss(model)

def _extra_body_oss(model: str) -> dict:
    """gpt-oss models spend most tokens on hidden reasoning; 'low' cuts free-tier usage a lot. REASONING_EFFORT=off disables."""
    eff = os.environ.get("REASONING_EFFORT", "low").lower()
    return {"reasoning_effort": eff} if ("gpt-oss" in model and eff not in ("", "off")) else {}

HARD_LIMIT_HINTS = ("request too large", "tokens per day", "(tpd)", "requests per day", "(rpd)", "perday", "per day", "daily")

DAILY_HINTS = ("tokens per day", "(tpd)", "requests per day", "(rpd)", "perday", "per day", "daily")

def _exh_path() -> Path:
    return Path(os.environ.get("LESSONFORGE_EXHAUSTED_FILE") or ROOT_DIR / "outputs/exhausted.json")

def _exh_load() -> dict:
    try:
        return json.loads(_exh_path().read_text())
    except Exception:
        return {}

def _exhausted_until(key: str) -> float:
    return _exh_load().get(key, 0)

def _mark_exhausted(key: str, seconds: float):
    d = _exh_load(); d[key] = time.time() + seconds
    p = _exh_path(); p.parent.mkdir(parents=True, exist_ok=True); p.write_text(json.dumps(d))

_LAST_CALL: dict = {}
_SEEN_429: set = set()
DEFAULT_MIN_INTERVAL = {"gemini": 13.0}      # seconds between calls; free tiers allow only a few requests per minute

def _pace(provider: str):
    """Spread calls out instead of hitting the rate limit and waiting. Override: MIN_INTERVAL_GEMINI=8 (seconds)."""
    gap = float(os.environ.get(f"MIN_INTERVAL_{provider.upper()}", DEFAULT_MIN_INTERVAL.get(provider, 0)))
    wait = gap - (time.monotonic() - _LAST_CALL.get(provider, -1e9))
    if wait > 0:
        time.sleep(wait)
    _LAST_CALL[provider] = time.monotonic()

def last_model() -> str:
    """provider:model of the most recent successful call ('' if none) - used to record WHICH model wrote each lesson."""
    m = LAST
    if m.get("provider") and m.get("model"):
        return f"{m['provider']}:{m['model']}"
    return m.get("model") or ""

_OLLAMA_MODELS: dict = {}

def _http_get_json(url: str, timeout: float = 2.0):
    import urllib.request
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read().decode())

def _ollama_status(model: str) -> str | None:
    """None if Ollama is reachable and the model is installed, else a human-readable reason (checked once per process)."""
    host = _ollama_host()
    if host not in _OLLAMA_MODELS:
        try:
            _OLLAMA_MODELS[host] = [m["name"] for m in _http_get_json(host + "/api/tags").get("models", [])]
        except Exception:
            _OLLAMA_MODELS[host] = None
    names = _OLLAMA_MODELS[host]
    if names is None:
        return f"Ollama is not reachable at {host} (start the Ollama app or run 'ollama serve')"
    if model not in names and model + ":latest" not in names:
        return f"model '{model}' is not installed in Ollama (run: ollama pull {model})"
    return None

def primary_models() -> set:
    """The first entry of each role's chain = what you intend to use. Anything else that answers is a FALLBACK."""
    out = set()
    for role in ("generator", "judge"):
        try:
            prov, model = _chain(role)[0]; out.add(f"{prov}:{model}")
        except Exception:
            pass
    return out

def _usable(provider: str, model: str) -> str | None:
    """Return a reason string if this chain entry can't be used, else None."""
    if "REPLACE" in model.upper() or not model:
        return "placeholder model id"
    if provider not in BASE_URLS:
        return f"unknown provider '{provider}'"
    until = _exhausted_until(f"{provider}:{model}")
    if until > time.time():
        return (f"daily quota exhausted earlier; skipping until about {time.strftime('%H:%M', time.localtime(until))} "
                f"(delete outputs/exhausted.json if your quota has already reset)")
    if provider == "ollama":
        return _ollama_status(model)
    env = KEY_ENV[provider]
    if env and not os.environ.get(env):
        return f"{env} not set"
    return None

def chat(role: str, messages: list[dict], temperature: float = 0.0, json_mode: bool = False,
         max_tokens: int = 4096, retries: int = 5, cache: bool = False) -> str:
    errors: list[str] = []
    ckey = None
    if cache and os.environ.get("LLM_CACHE", "1") != "0":     # deterministic judge calls: identical request -> identical stored answer
        ckey = hashlib.sha1(json.dumps([_chain(role), messages, temperature, json_mode, max_tokens], sort_keys=True).encode()).hexdigest()
        hit = _cache_get(ckey)
        if hit:
            MODELS_USED.add(hit["model"]); LAST.update({"model": hit["model"], "cached": True, "finish_reason": "cached"})
            return hit["text"]
    for provider, model in _chain(role):               # fallback chain across providers
        why = _usable(provider, model)
        if why:
            errors.append(f"{provider}:{model} -> skipped ({why})"); continue
        use_json, use_reasoning = json_mode, True
        for i in range(retries):
            try:
                kw = dict(model=model, messages=messages, temperature=temperature, max_tokens=max_tokens)
                if json_mode:
                    kw["messages"] = _ensure_json_word(messages)
                    if use_json:
                        kw["response_format"] = {"type": "json_object"}
                if use_reasoning and _extra_body(provider, model):
                    kw["extra_body"] = _extra_body(provider, model)
                _pace(provider)
                r = _client(provider).chat.completions.create(**kw)
                USAGE_LOG.parent.mkdir(exist_ok=True)
                u = r.usage
                fr = getattr(r.choices[0], "finish_reason", None)
                det = getattr(u, "completion_tokens_details", None)
                meta = {"t": time.time(), "role": role, "provider": provider, "model": model,
                        "in": getattr(u, "prompt_tokens", None), "out": getattr(u, "completion_tokens", None),
                        "reasoning": getattr(det, "reasoning_tokens", None), "finish": fr,
                        "extra_body": bool(kw.get("extra_body"))}
                with USAGE_LOG.open("a") as f:
                    f.write(json.dumps(meta) + "\n")
                LAST.clear(); LAST.update(meta); MODELS_USED.add(f"{provider}:{model}")
                if provider == "ollama" and meta["in"] in (2048, 4096):
                    print(f"   [warning] Ollama reports exactly {meta['in']} prompt tokens: its context window may be truncating the prompt. "
                          "Set OLLAMA_CONTEXT_LENGTH=8192 and restart Ollama (see scripts/ollama_check.py).", flush=True)
                if fr == "length":
                    print(f"   [truncated] {provider}:{model} hit max_tokens={max_tokens} (hidden reasoning can use the budget)", flush=True)
                text = r.choices[0].message.content or ""
                text = re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()  # Qwen-style reasoning
                if not text:
                    errors.append(f"{provider}:{model} -> empty reply (reasoning model may have used all max_tokens)")
                    break
                if ckey:
                    _cache_put(ckey, text, f"{provider}:{model}")
                return text
            except (RateLimitError, APIConnectionError) as e:
                msg = _err_text(e)
                errors.append(f"{provider}:{model} -> {type(e).__name__} (try {i + 1}): {msg[:500]}")
                if provider == "ollama" and isinstance(e, APIConnectionError):
                    break                               # server not running: retrying is pointless
                low = msg.lower()
                if f"{provider}:{model}" not in _SEEN_429:
                    _SEEN_429.add(f"{provider}:{model}")
                    print(f"   [rate limit detail] {provider}:{model}: {msg[:350]}", flush=True)
                if any(h in low for h in DAILY_HINTS):           # remember it: don't spend another request rediscovering this
                    parsed = _wait_from_message(msg, -1)
                    ttl = min(parsed, 86400) if (provider == "groq" and parsed > 0) else float(os.environ.get("EXHAUSTED_TTL_HOURS", "6")) * 3600
                    _mark_exhausted(f"{provider}:{model}", ttl)
                if any(h in low for h in HARD_LIMIT_HINTS):      # waiting a minute will not fix these -> next provider
                    print(f"   [hard limit] {provider}:{model}: {msg[:160]} -> trying next provider in chain", flush=True)
                    break
                wait = min(2 ** i * 5, 30)
                try:   # free tiers may send a Retry-After header on 429
                    wait = float(e.response.headers.get("retry-after", wait)) + 1
                except Exception:
                    pass
                wait = _wait_from_message(msg, wait)
                if wait > 120:                                    # e.g. daily budget refills in minutes/hours
                    print(f"   [hard limit] {provider}:{model} needs ~{wait / 60:.0f} min -> trying next provider in chain", flush=True)
                    break
                print(f"   [rate limit] {provider}:{model} waiting {wait:.0f}s ...", flush=True)
                time.sleep(wait)
            except APIStatusError as e:
                errors.append(f"{provider}:{model} -> HTTP {e.status_code}: {str(e)[:500]}")
                msg = _err_text(e).lower()
                if e.status_code == 400 and use_json and provider == "ollama":
                    use_json = False                    # some local models/versions reject response_format; we parse JSON ourselves
                    continue
                if e.status_code == 400 and use_reasoning and "reasoning" in msg:
                    use_reasoning = False   # provider rejected reasoning_effort: retry without it
                    continue
                if e.status_code == 400 and use_json and ("validate json" in msg or "failed_generation" in msg or "json_validate" in msg):
                    use_json = False        # model produced bad JSON under strict mode: retry without it; we parse ourselves
                    continue
                if e.status_code >= 500: time.sleep(2 ** i)
                else: break                              # 4xx (bad key/model): go to next provider
    raise RuntimeError(f"All providers failed for role '{role}':\n  " + "\n  ".join(errors))
