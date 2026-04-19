from __future__ import annotations

from generators import text_simplify as ts


def test_fk_retry_loop_meets_target(monkeypatch):
    ts._CACHE.clear()

    calls = {"n": 0}

    def fake_call(_prompt: str, timeout_seconds: float = 4.0):
        calls["n"] += 1
        return "COMPLEX output" if calls["n"] == 1 else "SIMPLE output"

    def fake_fk(text: str) -> float:
        if "COMPLEX" in text:
            return 12.5
        if "SIMPLE" in text:
            return 7.2
        return 11.0

    monkeypatch.setattr(ts, "_call_ollama", fake_call)
    monkeypatch.setattr(ts, "compute_fk_grade", fake_fk)

    result = ts.simplify_text("Original technical paragraph", target_level="grade8")

    assert calls["n"] == 2
    assert result["fk_grade"] <= ts.TARGETS["grade8"]
    assert result["attempts"] == 2
    assert isinstance(result["chunks"], list)


def test_cache_hit(monkeypatch):
    ts._CACHE.clear()

    calls = {"n": 0}

    def fake_call(_prompt: str, timeout_seconds: float = 4.0):
        calls["n"] += 1
        return "Simple and clear text."

    monkeypatch.setattr(ts, "_call_ollama", fake_call)

    r1 = ts.simplify_text("Caching should work here", target_level="grade8")
    r2 = ts.simplify_text("Caching should work here", target_level="grade8")

    assert r1["cache_hit"] is False
    assert r2["cache_hit"] is True
    assert calls["n"] == 1


def test_ollama_failure_fallback(monkeypatch):
    ts._CACHE.clear()

    def fake_fail(_prompt: str, timeout_seconds: float = 4.0):
        raise RuntimeError("ollama unavailable")

    monkeypatch.setattr(ts, "_call_ollama", fake_fail)

    text = "Photosynthesis utilizes sunlight for biochemical conversion into glucose."
    result = ts.simplify_text(text, target_level="grade5")

    assert result["simplified_text"]
    assert "chunks" in result
    assert isinstance(result["chunks"], list)


def test_empty_input_still_returns_valid_shape():
    result = ts.simplify_text(" ", target_level="grade8")
    assert "simplified_text" in result
    assert "chunks" in result


def test_empty_first_response_retries_strict_before_fallback(monkeypatch):
    ts._CACHE.clear()

    calls = {"n": 0}

    def fake_call(_prompt: str, timeout_seconds: float = 4.0):
        calls["n"] += 1
        if calls["n"] == 1:
            return ""
        return "SIMPLE strict retry output"

    def fake_fk(text: str) -> float:
        if "SIMPLE" in text:
            return 7.0
        return 11.0

    monkeypatch.setattr(ts, "_call_ollama", fake_call)
    monkeypatch.setattr(ts, "compute_fk_grade", fake_fk)

    result = ts.simplify_text("Complex source text", target_level="grade8")

    assert calls["n"] == 2
    assert result["simplified_text"] == "SIMPLE strict retry output"
    assert result["fk_grade"] <= ts.TARGETS["grade8"]
