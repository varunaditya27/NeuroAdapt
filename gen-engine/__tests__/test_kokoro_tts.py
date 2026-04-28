from __future__ import annotations

import base64
import io
import wave
from pathlib import Path

from generators import kokoro_tts as kt


def _tiny_wav_bytes() -> bytes:
    with io.BytesIO() as buffer:
        with wave.open(buffer, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(22050)
            wav.writeframes(b"\x00\x00" * 2205)  # ~0.1s silence
        return buffer.getvalue()


def test_extract_word_timestamps_passes_text_param(monkeypatch, tmp_path):
    wav_path = tmp_path / "sample.wav"
    wav_path.write_bytes(_tiny_wav_bytes())

    captured = {"params": None}

    class _FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"timestamps": [{"word": "hello", "start_ms": 0, "end_ms": 120}]}

    def fake_get(_url, params=None, timeout=2):
        captured["params"] = params
        return _FakeResponse()

    monkeypatch.setattr(kt.requests, "get", fake_get)

    stamps, confidence = kt.extract_word_timestamps_with_confidence(
        str(wav_path), text="hello world"
    )

    assert confidence == "high"
    assert stamps
    assert captured["params"] is not None
    assert captured["params"].get("text") == "hello world"


def test_generate_tts_accepts_json_base64_audio(monkeypatch, tmp_path):
    wav_bytes = _tiny_wav_bytes()
    encoded = base64.b64encode(wav_bytes).decode("utf-8")

    class _FakeSpeechResponse:
        headers = {"content-type": "application/json"}

        def raise_for_status(self):
            return None

        def json(self):
            return {"audio_base64": encoded}

    monkeypatch.setattr(kt, "_AUDIO_DIR", Path(tmp_path))
    monkeypatch.setattr(kt.requests, "post", lambda *_args, **_kwargs: _FakeSpeechResponse())
    monkeypatch.setattr(
        kt,
        "extract_word_timestamps_with_confidence",
        lambda *_args, **_kwargs: ([{"word": "hello", "start_ms": 0, "end_ms": 100}], "high"),
    )

    result = kt.generate_tts("hello world", speed=0.9)

    assert result["audio_url"]
    assert Path(result["audio_url"]).exists()
    assert result["timestamp_confidence"] == "high"
    assert result["cache_hit"] is False
