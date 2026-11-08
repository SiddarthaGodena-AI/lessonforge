import pytest

@pytest.fixture(autouse=True)
def isolated_memory_db(tmp_path, monkeypatch):
    """Every test gets its own empty memory database; the real data/memory.db is never touched."""
    monkeypatch.setenv("LESSONFORGE_DB", str(tmp_path / "memory.db"))

@pytest.fixture(autouse=True)
def isolated_reports(tmp_path, monkeypatch):
    monkeypatch.setenv("LESSONFORGE_OUT", str(tmp_path / "out"))

@pytest.fixture(autouse=True)
def hermetic(monkeypatch):
    """Tests must not depend on YOUR machine: no real .env settings, no network. A test that tries to connect fails loudly
    instead of hanging for minutes (rate-limit waits, DNS timeouts, a local Ollama that is down...)."""
    import socket
    for k in ("GENERATOR", "JUDGE", "GROQ_API_KEY", "GEMINI_API_KEY", "OPENROUTER_API_KEY", "OLLAMA_HOST", "PROMPT_VERSION",
              "MIN_INTERVAL_GEMINI", "LESSONFORGE_ENV", "EXHAUSTED_TTL_HOURS", "REASONING_EFFORT", "GEMINI_REASONING", "LLM_GATE", "LLM_CACHE", "JUDGE_NARROW"):
        monkeypatch.delenv(k, raising=False)
    def blocked(*a, **k):
        raise RuntimeError("network access attempted inside a test - tests must be hermetic")
    monkeypatch.setattr(socket.socket, "connect", blocked)


@pytest.fixture(autouse=True)
def isolated_exhausted_state(tmp_path, monkeypatch):
    monkeypatch.setenv("LESSONFORGE_EXHAUSTED_FILE", str(tmp_path / "exhausted.json"))
