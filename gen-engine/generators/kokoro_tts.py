"""Tier-3 Kokoro TTS generation utilities.

Calls the kokoro-tts microservice (gen-engine/services/kokoro/main.py).
Uses the combined /v1/audio/speech/with_timestamps endpoint for a single
round-trip that returns audio + proportional word timestamps together.

Fallback chain:
  kokoro-tts service (neural Kokoro ONNX)
    → kokoro-tts service (espeak-ng, if Kokoro model unavailable)
      → text-only (audio_url=None, warning in response)
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import logging
import os
import tempfile
import wave
from pathlib import Path
from typing import Any, cast

import requests

logger = logging.getLogger(__name__)

# ── Audio cache directory ─────────────────────────────────────────────────────

def _resolve_audio_dir() -> Path:
    preferred = Path(__file__).resolve().parents[1] / "cache" / "audio"
    try:
        preferred.mkdir(parents=True, exist_ok=True)
        return preferred
    except Exception:
        fallback = Path(os.getenv("GEN_ENGINE_CACHE_DIR", "/tmp/neuroadapt-gen-engine")) / "audio"
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback


_AUDIO_DIR = _resolve_audio_dir()

# ── Learner-level speed presets ───────────────────────────────────────────────
# Matches the presets in services/kokoro/main.py so cache keys are consistent.

_LEVEL_SPEED: dict[str, float] = {
    "grade5":     0.80,
    "grade8":     0.88,
    "university": 0.95,
}

# ── Internal helpers ──────────────────────────────────────────────────────────

def _base_url() -> str:
    return os.getenv("KOKORO_TTS_URL") or os.getenv("TTS_URL") or "http://localhost:8880"


def _cache_key(text: str, voice: str, speed: float, learner_level: str) -> str:
    return hashlib.md5(
        f"{voice}:{speed:.3f}:{learner_level}:{text}".encode("utf-8")
    ).hexdigest()


def _duration_from_wav(file_path: Path) -> int:
    try:
        with wave.open(str(file_path), "rb") as wf:
            frames = wf.getnframes()
            rate = wf.getframerate() or 44_100
            return int((frames / rate) * 1_000)
    except Exception:
        return 0


def _proportional_word_timestamps(text: str, duration_ms: int) -> list[dict[str, Any]]:
    """
    Generate word timestamps proportional to word length + punctuation weight.
    More accurate than uniform step distribution — longer words get more time,
    sentence-ending punctuation gets an additional pause budget.
    """
    import re
    words = [w for w in text.split() if w.strip()]
    if not words or duration_ms <= 0:
        return []

    weights: list[float] = []
    for word in words:
        clean = re.sub(r"[^a-zA-Z0-9]", "", word)
        weight = max(1.5, len(clean) * 0.9)
        if word.endswith((",", ";", "—", ":")):
            weight += 1.5
        elif word.endswith((".", "!", "?", "…")):
            weight += 2.5
        weights.append(weight)

    total_weight = sum(weights)
    cursor = 0
    stamps: list[dict[str, Any]] = []
    for word, w in zip(words, weights):
        duration = int((w / total_weight) * duration_ms)
        stamps.append({"word": word, "start_ms": cursor, "end_ms": cursor + duration})
        cursor += duration
    return stamps


# ── Voice resolution ──────────────────────────────────────────────────────────

def clone_voice_from_sample(sample_audio_path: str, voice_name: str) -> dict[str, Any]:
    """POST a WAV sample to kokoro-tts and get back a voice_id."""
    with open(sample_audio_path, "rb") as f:
        response = requests.post(
            f"{_base_url()}/v1/voices/create",
            files={"audio": f},
            data={"name": voice_name},
            timeout=300,
        )
    response.raise_for_status()
    payload = response.json()
    return {"voice_id": payload.get("voice_id"), "voice_name": voice_name}


def _decode_voice_profile_sample(voice_profile: str) -> Path | None:
    """Decode a base64-encoded audio sample from a voice_profile string."""
    raw = (voice_profile or "").strip()
    if not raw:
        return None
    if raw.startswith("data:"):
        marker = ";base64,"
        if marker not in raw:
            return None
        raw = raw.split(marker, 1)[1].strip()
    if len(raw) < 64:
        return None
    try:
        decoded = base64.b64decode(raw, validate=True)
    except (binascii.Error, ValueError):
        return None
    if len(decoded) < 256:
        return None
    with tempfile.NamedTemporaryFile(prefix="kokoro_voice_", suffix=".wav", delete=False) as tmp:
        tmp.write(decoded)
        return Path(tmp.name)


def _resolve_voice(voice_profile: str | None) -> tuple[str, str | None]:
    """
    Resolve voice_profile to a kokoro voice ID.

    Returns (voice_id, optional_warning_message).
    Resolution order:
      1. None / empty  → KOKORO_DEFAULT_VOICE env var (default: af_bella)
      2. Filesystem path to a WAV sample → clone via /v1/voices/create
      3. Base64-encoded WAV data URI → decode, clone, cleanup
      4. Treat as a raw voice ID string (passed through unchanged)
    """
    default_voice = os.getenv("KOKORO_DEFAULT_VOICE", "af_bella")

    if not voice_profile:
        return default_voice, None

    # Path to existing file
    candidate = Path(voice_profile)
    if candidate.exists() and candidate.is_file():
        clone_name = f"clone_{candidate.stem[:24] or 'voice'}"
        try:
            payload = clone_voice_from_sample(str(candidate), voice_name=clone_name)
            voice_id = payload.get("voice_id")
            if isinstance(voice_id, str) and voice_id.strip():
                return voice_id.strip(), None
            return default_voice, "Voice clone returned no voice_id; using default."
        except Exception as exc:
            return default_voice, f"Voice cloning failed ({exc}); using default."

    # Base64 data URI
    decoded_sample = _decode_voice_profile_sample(voice_profile)
    if decoded_sample is not None:
        clone_name = f"clone_{decoded_sample.stem[:24] or 'voice'}"
        try:
            payload = clone_voice_from_sample(str(decoded_sample), voice_name=clone_name)
            voice_id = payload.get("voice_id")
            if isinstance(voice_id, str) and voice_id.strip():
                return voice_id.strip(), None
            return default_voice, "Voice clone returned no voice_id; using default."
        except Exception as exc:
            return default_voice, f"Voice cloning failed ({exc}); using default."
        finally:
            try:
                decoded_sample.unlink(missing_ok=True)
            except Exception:
                pass

    # Raw voice ID (af_bella, am_adam, etc.)
    return voice_profile, None


# ── Backward-compatible timestamp helpers ────────────────────────────────────

def extract_word_timestamps_with_confidence(
    audio_path: str, text: str | None = None
) -> tuple[list[dict[str, Any]], str]:
    """
    Fetch proportional word timestamps from the kokoro-tts service.
    Falls back to local proportional computation if the service is unavailable.
    """
    try:
        response = requests.get(
            f"{_base_url()}/v1/audio/timestamps",
            params={"audio_path": audio_path, "text": text or ""},
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        stamps = data.get("timestamps")
        if isinstance(stamps, list) and stamps:
            return stamps, "proportional"
    except Exception:
        pass

    duration_ms = _duration_from_wav(Path(audio_path))
    return _proportional_word_timestamps(text or "", duration_ms), "proportional_local"


def extract_word_timestamps(audio_path: str, text: str | None = None) -> list[dict[str, Any]]:
    """Backward-compatible helper — returns only the timestamps list."""
    stamps, _ = extract_word_timestamps_with_confidence(audio_path, text=text)
    return stamps


# ── Primary public API ────────────────────────────────────────────────────────

def generate_tts(
    text: str,
    voice_profile: str | None = None,
    speed: float = 0.88,
    learner_level: str = "grade8",
    learner_id: str | None = None,
    session_id: str | None = None,
) -> dict[str, Any]:
    """
    Generate speech audio for the given text via the kokoro-tts microservice.

    Uses the combined /v1/audio/speech/with_timestamps endpoint so audio
    and word timestamps are retrieved in a single HTTP call.

    Args:
        text:           The narration text to synthesize.
        voice_profile:  Voice ID string, filesystem path to a WAV sample,
                        or base64 data URI of a voice sample.
        speed:          Base speaking rate (0.7–1.2). Overridden by learner_level
                        preset when learner_level is recognized.
        learner_level:  "grade5" | "grade8" | "university". Controls speed preset
                        and text preprocessing inside the kokoro-tts service.
        learner_id:     Optional learner identifier for cache namespacing.
        session_id:     Optional session identifier for tracing.

    Returns:
        dict with keys:
          audio_url (str | None)       — path to cached WAV file, or None on failure
          duration_ms (int)            — audio duration in milliseconds
          word_timestamps (list)       — [{word, start_ms, end_ms}, ...]
          timestamp_confidence (str)   — "proportional" | "proportional_local"
          synthesis_backend (str)      — "kokoro-onnx" | "espeak" | "silence" | "cached"
          voice_profile (str)          — resolved voice ID used
          cache_hit (bool)
          learner_id (str | None)
          session_id (str | None)
          warning (str | None)         — present only when a non-fatal issue occurred
    """
    if not text.strip():
        return {
            "audio_url": None,
            "duration_ms": 0,
            "word_timestamps": [],
            "timestamp_confidence": None,
            "synthesis_backend": "none",
            "voice_profile": None,
            "cache_hit": False,
            "warning": "No text provided for TTS.",
        }

    voice, voice_warning = _resolve_voice(voice_profile)

    # Learner-level preset overrides bare speed
    effective_speed = _LEVEL_SPEED.get(learner_level, speed)
    speed_value = max(0.7, min(1.2, float(effective_speed)))

    key = _cache_key(text, voice, speed_value, learner_level)
    wav_path = _AUDIO_DIR / f"{key}.wav"

    # ── Cache hit ──────────────────────────────────────────────────────────
    if wav_path.exists():
        duration_ms = _duration_from_wav(wav_path)
        timestamps, confidence = extract_word_timestamps_with_confidence(
            str(wav_path), text=text
        )
        result: dict[str, Any] = {
            "audio_url": str(wav_path),
            "duration_ms": duration_ms,
            "word_timestamps": timestamps,
            "timestamp_confidence": confidence,
            "synthesis_backend": "cached",
            "voice_profile": voice,
            "cache_hit": True,
            "learner_id": learner_id,
            "session_id": session_id,
        }
        if voice_warning:
            result["warning"] = voice_warning
        return result

    # ── Combined synthesis + timestamps call ───────────────────────────────
    request_payload = {
        "model": "kokoro",
        "input": text,
        "voice": voice,
        "speed": speed_value,
        "response_format": "wav",
        "learner_level": learner_level,
        "ssml": True,
    }

    timeout = float(os.getenv("LATENCY_BUDGET_AUDIO", "8"))

    try:
        response = requests.post(
            f"{_base_url()}/v1/audio/speech/with_timestamps",
            json=request_payload,
            timeout=timeout,
        )
        response.raise_for_status()
        data = response.json()

        audio_b64 = data.get("audio_base64", "")
        if not audio_b64:
            raise ValueError("Service returned no audio_base64 field")

        wav_bytes = base64.b64decode(audio_b64)
        wav_path.write_bytes(wav_bytes)

        duration_ms = data.get("duration_ms") or _duration_from_wav(wav_path)
        word_timestamps = data.get("word_timestamps") or _proportional_word_timestamps(
            data.get("processed_text", text), duration_ms
        )

        result = {
            "audio_url": str(wav_path),
            "duration_ms": duration_ms,
            "word_timestamps": word_timestamps,
            "timestamp_confidence": "proportional",
            "synthesis_backend": data.get("synthesis_backend", "kokoro-onnx"),
            "voice_profile": voice,
            "cache_hit": False,
            "learner_id": learner_id,
            "session_id": session_id,
        }
        if voice_warning:
            result["warning"] = voice_warning
        return result

    except Exception as exc:
        logger.warning(f"kokoro-tts combined endpoint failed, trying plain WAV: {exc}")

    # ── Fallback: plain /v1/audio/speech (older service versions) ─────────
    try:
        response = requests.post(
            f"{_base_url()}/v1/audio/speech",
            json={
                "model": "kokoro",
                "input": text,
                "voice": voice,
                "speed": speed_value,
                "response_format": "wav",
            },
            timeout=timeout,
        )
        response.raise_for_status()

        content_type = (response.headers.get("content-type") or "").lower()
        if "application/json" in content_type:
            body = response.json()
            raw = None
            for k in ("audio_base64", "audio", "audio_content"):
                raw = body.get(k)
                if isinstance(raw, str) and raw.strip():
                    break
            if raw:
                wav_bytes = base64.b64decode(raw)
            else:
                audio_url = body.get("audio_url")
                if audio_url:
                    follow = requests.get(audio_url, timeout=30)
                    follow.raise_for_status()
                    wav_bytes = cast(bytes, follow.content)
                else:
                    raise ValueError("No audio bytes in JSON response")
        else:
            wav_bytes = cast(bytes, response.content)

        wav_path.write_bytes(wav_bytes)
        duration_ms = _duration_from_wav(wav_path)
        timestamps = _proportional_word_timestamps(text, duration_ms)

        result = {
            "audio_url": str(wav_path),
            "duration_ms": duration_ms,
            "word_timestamps": timestamps,
            "timestamp_confidence": "proportional_local",
            "synthesis_backend": "espeak_fallback",
            "voice_profile": voice,
            "cache_hit": False,
            "learner_id": learner_id,
            "session_id": session_id,
        }
        if voice_warning:
            result["warning"] = voice_warning
        return result

    except Exception as exc:
        warning = f"Kokoro TTS service unavailable — audio disabled ({exc})."
        if voice_warning:
            warning = f"{voice_warning} {warning}"
        logger.error(f"All TTS paths failed: {exc}")
        return {
            "audio_url": None,
            "duration_ms": 0,
            "word_timestamps": [],
            "timestamp_confidence": None,
            "synthesis_backend": "none",
            "voice_profile": voice,
            "cache_hit": False,
            "learner_id": learner_id,
            "session_id": session_id,
            "warning": warning,
        }