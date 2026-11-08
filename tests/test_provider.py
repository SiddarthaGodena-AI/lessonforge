import httpx, openai, pytest
from src.llm import provider

def test_wait_parsing():
    w = provider._wait_from_message
    assert w("Please try again in 1m2.5s.", 5) == pytest.approx(63.5)
    assert w("Please try again in 7.4s.", 5) == pytest.approx(8.4)
    assert w("Please try again in 500ms.", 5) == pytest.approx(1.5)
    assert w("no hint here", 5) == 5

def _bad_json_error():
    req = httpx.Request("POST", "http://x")
    return openai.BadRequestError("Failed to validate JSON. See 'failed_generation'", response=httpx.Response(400, request=req), body=None)

def test_json_mode_falls_back_to_plain_when_model_emits_bad_json(monkeypatch):
    monkeypatch.setenv("JUDGE", "groq:some-model"); monkeypatch.setenv("GROQ_API_KEY", "k")
    calls = []
    class FakeC:
        class chat:
            class completions:
                @staticmethod
                def create(**kw):
                    calls.append(kw)
                    if "response_format" in kw:
                        raise _bad_json_error()
                    class R:
                        usage = None
                        choices = [type("C", (), {"message": type("M", (), {"content": '{"ok": true}'})})]
                    return R
    monkeypatch.setattr(provider, "_client", lambda p: FakeC)
    monkeypatch.setattr(provider, "USAGE_LOG", provider.USAGE_LOG.parent / "usage_test.jsonl")
    out = provider.chat("judge", [{"role": "user", "content": "hi"}], json_mode=True)
    assert out == '{"ok": true}' and len(calls) == 2 and "response_format" not in calls[1]
    assert "json" in str(calls[1]["messages"]).lower()

def _rate_err(msg):
    req = httpx.Request("POST", "http://x")
    return openai.RateLimitError(msg, response=httpx.Response(429, request=req), body=None)

def _ok_client(record):
    class FakeC:
        class chat:
            class completions:
                @staticmethod
                def create(**kw):
                    record.append(kw["model"])
                    class R:
                        usage = None
                        choices = [type("C", (), {"message": type("M", (), {"content": "hello"})})]
                    return R
    return FakeC

def test_hard_limit_skips_to_next_provider_without_waiting(monkeypatch):
    monkeypatch.setenv("GENERATOR", "groq:big,groq:small"); monkeypatch.setenv("GROQ_API_KEY", "k")
    monkeypatch.setattr(provider.time, "sleep", lambda s: (_ for _ in ()).throw(AssertionError("must not sleep")))
    monkeypatch.setattr(provider, "USAGE_LOG", provider.USAGE_LOG.parent / "usage_test.jsonl")
    calls = []
    class FakeC:
        class chat:
            class completions:
                @staticmethod
                def create(**kw):
                    calls.append(kw["model"])
                    if kw["model"] == "big":
                        raise _rate_err("Rate limit reached ... on tokens per day (TPD): Limit 200000, Used 200000. Please try again in 14m0s.")
                    return _ok_client([]).chat.completions.create(**kw)
    monkeypatch.setattr(provider, "_client", lambda p: FakeC)
    assert provider.chat("generator", [{"role": "user", "content": "hi"}]) == "hello"
    assert calls == ["big", "small"]          # exactly one attempt on the exhausted model, then fallback

def test_request_too_large_is_not_retried(monkeypatch):
    monkeypatch.setenv("GENERATOR", "groq:qwen"); monkeypatch.setenv("GROQ_API_KEY", "k")
    monkeypatch.setattr(provider.time, "sleep", lambda s: None)
    n = []
    class FakeC:
        class chat:
            class completions:
                @staticmethod
                def create(**kw):
                    n.append(1); raise _rate_err("Request too large for model on output tokens per minute (OTPM): Limit 1000, Requested 1313")
    monkeypatch.setattr(provider, "_client", lambda p: FakeC)
    with pytest.raises(RuntimeError) as e:
        provider.chat("generator", [{"role": "user", "content": "hi"}])
    assert len(n) == 1 and "Request too large" in str(e.value)

def test_gpt_oss_gets_low_reasoning_and_falls_back_if_rejected(monkeypatch):
    monkeypatch.setenv("JUDGE", "groq:openai/gpt-oss-120b"); monkeypatch.setenv("GROQ_API_KEY", "k")
    monkeypatch.delenv("REASONING_EFFORT", raising=False)
    monkeypatch.setattr(provider, "USAGE_LOG", provider.USAGE_LOG.parent / "usage_test.jsonl")
    seen = []
    class FakeC:
        class chat:
            class completions:
                @staticmethod
                def create(**kw):
                    seen.append(kw.get("extra_body"))
                    if kw.get("extra_body"):
                        req = httpx.Request("POST", "http://x")
                        raise openai.BadRequestError("unsupported parameter: reasoning_effort", response=httpx.Response(400, request=req), body=None)
                    return _ok_client([]).chat.completions.create(**kw)
    monkeypatch.setattr(provider, "_client", lambda p: FakeC)
    assert provider.chat("judge", [{"role": "user", "content": "hi"}]) == "hello"
    assert seen == [{"reasoning_effort": "low"}, None]

def _text_client(calls, text="verdict"):
    class FakeC:
        class chat:
            class completions:
                @staticmethod
                def create(**kw):
                    calls.append(kw)
                    class R:
                        usage = None
                        choices = [type("C", (), {"message": type("M", (), {"content": text}), "finish_reason": "stop"})]
                    return R
    return FakeC

def test_judge_cache_avoids_second_api_call(monkeypatch, tmp_path):
    monkeypatch.setenv("JUDGE", "groq:m"); monkeypatch.setenv("GROQ_API_KEY", "k"); monkeypatch.delenv("LLM_CACHE", raising=False)
    monkeypatch.setattr(provider, "CACHE_FILE", tmp_path / "c.json"); monkeypatch.setattr(provider, "_CACHE", None)
    monkeypatch.setattr(provider, "USAGE_LOG", tmp_path / "u.jsonl")
    calls = []
    monkeypatch.setattr(provider, "_client", lambda p: _text_client(calls))
    msgs = [{"role": "user", "content": "judge this"}]
    assert provider.chat("judge", msgs, cache=True) == "verdict"
    assert provider.chat("judge", msgs, cache=True) == "verdict"
    assert len(calls) == 1 and "groq:m" in provider.MODELS_USED
    provider.chat("judge", [{"role": "user", "content": "different"}], cache=True)
    assert len(calls) == 2                                   # different request -> real call
    monkeypatch.setenv("LLM_CACHE", "0")
    provider.chat("judge", msgs, cache=True); assert len(calls) == 3   # cache can be disabled

def test_cache_key_changes_with_judge_model(monkeypatch, tmp_path):
    monkeypatch.setenv("GROQ_API_KEY", "k"); monkeypatch.delenv("LLM_CACHE", raising=False)
    monkeypatch.setattr(provider, "CACHE_FILE", tmp_path / "c.json"); monkeypatch.setattr(provider, "_CACHE", None)
    monkeypatch.setattr(provider, "USAGE_LOG", tmp_path / "u.jsonl")
    calls = []; monkeypatch.setattr(provider, "_client", lambda p: _text_client(calls))
    msgs = [{"role": "user", "content": "x"}]
    monkeypatch.setenv("JUDGE", "groq:model-a"); provider.chat("judge", msgs, cache=True)
    monkeypatch.setenv("JUDGE", "groq:model-b"); provider.chat("judge", msgs, cache=True)
    assert len(calls) == 2                                   # a different judge must never reuse another judge's verdicts

def test_gemini_gets_reasoning_param(monkeypatch):
    monkeypatch.delenv("GEMINI_REASONING", raising=False)
    assert provider._extra_body("gemini", "gemini-x") == {"reasoning_effort": "low"}
    monkeypatch.setenv("GEMINI_REASONING", "off"); assert provider._extra_body("gemini", "gemini-x") == {}
    assert provider._extra_body("groq", "llama") == {}

def test_gemini_style_retry_hints_are_parsed():
    w = provider._wait_from_message
    assert w("Quota exceeded. Please retry in 21.5s.", 5) == pytest.approx(22.5)
    assert w('{"retryDelay": "34s"}', 5) == pytest.approx(35)

def test_per_day_quota_is_treated_as_hard_limit(monkeypatch):
    monkeypatch.setenv("GENERATOR", "gemini:big,groq:small"); monkeypatch.setenv("GEMINI_API_KEY", "k"); monkeypatch.setenv("GROQ_API_KEY", "k")
    monkeypatch.setattr(provider.time, "sleep", lambda s: (_ for _ in ()).throw(AssertionError("must not sleep")))
    monkeypatch.setattr(provider, "USAGE_LOG", provider.USAGE_LOG.parent / "usage_test.jsonl")
    monkeypatch.setattr(provider, "_LAST_CALL", {})
    calls = []
    class FakeC:
        class chat:
            class completions:
                @staticmethod
                def create(**kw):
                    calls.append(kw["model"])
                    if kw["model"] == "big":
                        raise _rate_err("Quota exceeded: GenerateRequestsPerDayPerProjectPerModel-FreeTier, limit: 20")
                    return _ok_client([]).chat.completions.create(**kw)
    monkeypatch.setattr(provider, "_client", lambda p: FakeC)
    assert provider.chat("generator", [{"role": "user", "content": "hi"}]) == "hello"
    assert calls == ["big", "small"]

def test_pacing_spaces_out_calls(monkeypatch):
    sleeps = []
    monkeypatch.setattr(provider.time, "sleep", lambda s: sleeps.append(s))
    monkeypatch.setattr(provider, "_LAST_CALL", {}); monkeypatch.setenv("MIN_INTERVAL_GEMINI", "5")
    provider._pace("gemini"); provider._pace("gemini")
    assert len(sleeps) == 1 and 0 < sleeps[0] <= 5
    provider._pace("groq"); assert len(sleeps) == 1     # providers with no interval are not delayed

def test_last_model_formats_provider_and_model():
    provider.LAST.clear(); assert provider.last_model() == ""
    provider.LAST.update({"provider": "gemini", "model": "flash"}); assert provider.last_model() == "gemini:flash"

# ---------------- Ollama fallback ----------------
class _Usage:
    def __init__(self, p=100, c=20): self.prompt_tokens, self.completion_tokens = p, c

def _client_with(behaviour, record):
    class FakeC:
        class chat:
            class completions:
                @staticmethod
                def create(**kw):
                    record.append(kw)
                    return behaviour(kw)
    return FakeC

def _resp(text="local answer", prompt_tokens=100):
    class R:
        usage = _Usage(prompt_tokens)
        choices = [type("C", (), {"message": type("M", (), {"content": text}), "finish_reason": "stop"})]
    return R

@pytest.fixture
def ollama_env(monkeypatch, tmp_path):
    monkeypatch.setenv("GEMINI_API_KEY", "k"); monkeypatch.setenv("GROQ_API_KEY", "k")
    monkeypatch.setattr(provider, "_OLLAMA_MODELS", {}); monkeypatch.setattr(provider, "_LAST_CALL", {})
    monkeypatch.setattr(provider, "USAGE_LOG", tmp_path / "u.jsonl"); provider.MODELS_USED.clear()

def test_chain_parses_model_names_containing_colons(monkeypatch):
    monkeypatch.setenv("GENERATOR", "gemini:flash,ollama:llama3.1:8b")
    assert provider._chain("generator") == [("gemini", "flash"), ("ollama", "llama3.1:8b")]

def test_ollama_status_reasons(monkeypatch, ollama_env):
    def down(url, timeout=2.0): raise OSError("refused")
    monkeypatch.setattr(provider, "_http_get_json", down)
    assert "not reachable" in provider._ollama_status("llama3.1:8b")
    monkeypatch.setattr(provider, "_OLLAMA_MODELS", {})
    monkeypatch.setattr(provider, "_http_get_json", lambda url, timeout=2.0: {"models": [{"name": "qwen2.5:7b"}]})
    assert "ollama pull llama3.1:8b" in provider._ollama_status("llama3.1:8b")
    assert provider._ollama_status("qwen2.5:7b") is None

def test_falls_back_to_ollama_when_cloud_is_exhausted(monkeypatch, ollama_env):
    monkeypatch.setenv("GENERATOR", "groq:big,ollama:llama3.1:8b")
    monkeypatch.setattr(provider, "_http_get_json", lambda url, timeout=2.0: {"models": [{"name": "llama3.1:8b"}]})
    monkeypatch.setattr(provider.time, "sleep", lambda s: None)
    rec = []
    def behave(kw):
        if kw["model"] == "big":
            raise _rate_err("Rate limit reached on tokens per day (TPD): Limit 200000, Used 200000")
        return _resp()
    monkeypatch.setattr(provider, "_client", lambda p: _client_with(behave, rec))
    assert provider.chat("generator", [{"role": "user", "content": "hi"}]) == "local answer"
    assert [r["model"] for r in rec] == ["big", "llama3.1:8b"]
    assert "ollama:llama3.1:8b" in provider.MODELS_USED and "ollama:llama3.1:8b" not in provider.primary_models()

def test_unreachable_ollama_is_skipped_with_clear_message(monkeypatch, ollama_env):
    monkeypatch.setenv("GENERATOR", "ollama:llama3.1:8b")
    def down(url, timeout=2.0): raise OSError("refused")
    monkeypatch.setattr(provider, "_http_get_json", down)
    with pytest.raises(RuntimeError) as e:
        provider.chat("generator", [{"role": "user", "content": "hi"}])
    assert "not reachable" in str(e.value) and "ollama serve" in str(e.value)

def test_ollama_connection_error_is_not_retried(monkeypatch, ollama_env):
    monkeypatch.setenv("GENERATOR", "ollama:m")
    monkeypatch.setattr(provider, "_http_get_json", lambda url, timeout=2.0: {"models": [{"name": "m"}]})
    monkeypatch.setattr(provider.time, "sleep", lambda s: (_ for _ in ()).throw(AssertionError("must not sleep")))
    n = []
    def behave(kw): raise openai.APIConnectionError(request=httpx.Request("POST", "http://x"))
    monkeypatch.setattr(provider, "_client", lambda p: _client_with(behave, n))
    with pytest.raises(RuntimeError):
        provider.chat("generator", [{"role": "user", "content": "hi"}])
    assert len(n) == 1

def test_ollama_json_mode_rejection_falls_back_to_plain(monkeypatch, ollama_env):
    monkeypatch.setenv("JUDGE", "ollama:m")
    monkeypatch.setattr(provider, "_http_get_json", lambda url, timeout=2.0: {"models": [{"name": "m"}]})
    rec = []
    def behave(kw):
        if "response_format" in kw:
            raise openai.BadRequestError("response_format not supported", response=httpx.Response(400, request=httpx.Request("POST", "http://x")), body=None)
        return _resp('{"ok": true}')
    monkeypatch.setattr(provider, "_client", lambda p: _client_with(behave, rec))
    assert provider.chat("judge", [{"role": "user", "content": "x"}], json_mode=True) == '{"ok": true}'
    assert len(rec) == 2 and "json" in str(rec[1]["messages"]).lower()

def test_truncated_context_warning(monkeypatch, ollama_env, capsys):
    monkeypatch.setenv("GENERATOR", "ollama:m")
    monkeypatch.setattr(provider, "_http_get_json", lambda url, timeout=2.0: {"models": [{"name": "m"}]})
    monkeypatch.setattr(provider, "_client", lambda p: _client_with(lambda kw: _resp(prompt_tokens=4096), []))
    provider.chat("generator", [{"role": "user", "content": "hi"}])
    assert "context window may be truncating" in capsys.readouterr().out

def test_primary_models_is_first_of_each_chain(monkeypatch):
    monkeypatch.setenv("GENERATOR", "gemini:flash,ollama:m"); monkeypatch.setenv("JUDGE", "groq:oss-120b,groq:oss-20b")
    assert provider.primary_models() == {"gemini:flash", "groq:oss-120b"}

# ---------------- exhausted quotas, error bodies, lab/final settings ----------------
def _rate_err_with_body(short_msg, body):
    req = httpx.Request("POST", "http://x")
    return openai.RateLimitError(short_msg, response=httpx.Response(429, request=req, content=body.encode()), body=None)

def test_per_day_quota_detected_from_response_body_not_just_message(monkeypatch, ollama_env):
    """Gemini's str(e) is just 'Error code: 429'; the reason ('PerDay') is only in the HTTP body."""
    monkeypatch.setenv("GENERATOR", "gemini:g,groq:small")
    monkeypatch.setattr(provider.time, "sleep", lambda s: (_ for _ in ()).throw(AssertionError("must not sleep")))
    calls = []
    def behave(kw):
        if kw["model"] == "g":
            raise _rate_err_with_body("Error code: 429", '{"error": {"details": "GenerateRequestsPerDayPerProjectPerModel-FreeTier"}}')
        return _resp()
    monkeypatch.setattr(provider, "_client", lambda p: _client_with(behave, calls))
    assert provider.chat("generator", [{"role": "user", "content": "hi"}]) == "local answer"
    assert [c["model"] for c in calls] == ["g", "small"]

def test_exhausted_quota_is_remembered_across_calls_and_processes(monkeypatch, ollama_env):
    monkeypatch.setenv("GENERATOR", "gemini:g,groq:small")
    monkeypatch.setattr(provider.time, "sleep", lambda s: None)
    calls = []
    def behave(kw):
        if kw["model"] == "g":
            raise _rate_err_with_body("Error code: 429", "RequestsPerDay quota (perday) exceeded")
        return _resp()
    monkeypatch.setattr(provider, "_client", lambda p: _client_with(behave, calls))
    provider.chat("generator", [{"role": "user", "content": "one"}])
    provider.chat("generator", [{"role": "user", "content": "two"}])
    assert [c["model"] for c in calls] == ["g", "small", "small"]      # the exhausted model was NOT tried again
    assert provider._exhausted_until("gemini:g") > provider.time.time()
    assert "gemini:g" in provider._exh_path().read_text()               # persisted on disk: a new command also skips it

def test_exhaustion_expires(monkeypatch, ollama_env):
    provider._mark_exhausted("gemini:g", -1)                            # already expired
    assert "exhausted" not in (provider._usable("gemini", "g") or "")
    provider._mark_exhausted("gemini:g", 3600)
    assert "exhausted" in provider._usable("gemini", "g")

def test_request_too_large_does_not_mark_model_exhausted(monkeypatch, ollama_env):
    monkeypatch.setenv("GENERATOR", "groq:qwen")
    monkeypatch.setattr(provider, "_client", lambda p: _client_with(lambda kw: (_ for _ in ()).throw(_rate_err("Request too large ... OTPM")), []))
    with pytest.raises(RuntimeError): provider.chat("generator", [{"role": "user", "content": "hi"}])
    assert provider._exhausted_until("groq:qwen") == 0                   # a too-big REQUEST is not a used-up DAY

def test_settings_file_is_selectable(monkeypatch, tmp_path):
    monkeypatch.setenv("LESSONFORGE_ENV", str(tmp_path / ".env.lab"))
    assert provider._env_file() == tmp_path / ".env.lab"
    monkeypatch.setenv("LESSONFORGE_ENV", ".env.lab")
    assert provider._env_file() == provider.ROOT_DIR / ".env.lab"
    monkeypatch.delenv("LESSONFORGE_ENV"); assert provider._env_file().name == ".env"

def test_default_gemini_pacing_respects_5_requests_per_minute():
    assert provider.DEFAULT_MIN_INTERVAL["gemini"] >= 12
