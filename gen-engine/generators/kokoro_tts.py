"""Tier-3 Kokoro TTS generation utilities."""

from __future__ import annotations

import base64
import binascii
import hashlib
import os
import tempfile
import wave
from pathlib import Path
from typing import Any, cast

import requests


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


def _base_url() -> str:
    return os.getenv("KOKORO_TTS_URL") or os.getenv("TTS_URL") or "http://localhost:8880"


def _cache_key(text: str, voice: str, speed: float) -> str:
    return hashlib.md5(f"{voice}:{speed}:{text}".encode("utf-8")).hexdigest()


def _duration_from_wav(file_path: Path) -> int:
    try:
        with wave.open(str(file_path), "rb") as wf:
            frames = wf.getnframes()
            rate = wf.getframerate() or 44100
            return int((frames / rate) * 1000)
    except Exception:
        return 0


def _heuristic_word_timestamps(text: str, duration_ms: int) -> list[dict[str, Any]]:
    words = [w for w in text.split() if w.strip()]
    if not words:
        return []
    step = max(120, int(duration_ms / len(words))) if duration_ms > 0 else 220
    out: list[dict[str, Any]] = []
    cursor = 0
    for word in words:
        out.append({"word": word, "start_ms": cursor, "end_ms": cursor + step})
        cursor += step
    return out


def extract_word_timestamps_with_confidence(
    audio_path: str, text: str | None = None
) -> tuple[list[dict[str, Any]], str]:
    """Use Kokoro alignment endpoint if available, else fall back to heuristic timings."""
    try:
        response = requests.get(
            f"{_base_url()}/v1/audio/timestamps",
            params={"audio_path": audio_path, "text": text or ""},
            timeout=120,
        )
        response.raise_for_status()
        data = response.json()
        stamps = data.get("timestamps")
        if isinstance(stamps, list):
            return stamps, "high"
    except Exception:
        pass

    duration_ms = _duration_from_wav(Path(audio_path))
    return _heuristic_word_timestamps(text or "", duration_ms), "heuristic"


def extract_word_timestamps(audio_path: str, text: str | None = None) -> list[dict[str, Any]]:
    """Backward-compatible helper returning only timestamp entries."""
    stamps, _ = extract_word_timestamps_with_confidence(audio_path, text=text)
    return stamps


def clone_voice_from_sample(sample_audio_path: str, voice_name: str) -> dict[str, Any]:
    """Create a Kokoro voice profile from a short sample."""
    with open(sample_audio_path, "rb") as sample_file:
        response = requests.post(
            f"{_base_url()}/v1/voices/create",
            files={"audio": sample_file},
            data={"name": voice_name},
            timeout=300,
        )
    response.raise_for_status()
    payload = response.json()
    return {
        "voice_id": payload.get("voice_id"),
        "voice_name": voice_name,
    }


def _decode_voice_profile_sample(voice_profile: str) -> Path | None:
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
    default_voice = os.getenv("KOKORO_DEFAULT_VOICE", "af_bella")
    if not voice_profile:
        return default_voice, None

    candidate = Path(voice_profile)
    if candidate.exists() and candidate.is_file():
        clone_name = f"clone_{candidate.stem[:24] or 'voice'}"
        try:
            payload = clone_voice_from_sample(str(candidate), voice_name=clone_name)
            voice_id = payload.get("voice_id")
            if isinstance(voice_id, str) and voice_id.strip():
                return voice_id.strip(), None
            return default_voice, "Voice clone endpoint returned no voice_id; using default voice."
        except Exception as exc:
            return default_voice, f"Voice cloning failed; using default voice ({exc})."

    decoded_sample = _decode_voice_profile_sample(voice_profile)
    if decoded_sample is not None:
        clone_name = f"clone_{decoded_sample.stem[:24] or 'voice'}"
        try:
            payload = clone_voice_from_sample(str(decoded_sample), voice_name=clone_name)
            voice_id = payload.get("voice_id")
            if isinstance(voice_id, str) and voice_id.strip():
                return voice_id.strip(), None
            return default_voice, "Voice clone endpoint returned no voice_id; using default voice."
        except Exception as exc:
            return default_voice, f"Voice cloning failed; using default voice ({exc})."
        finally:
            try:
                decoded_sample.unlink(missing_ok=True)
            except Exception:
                pass

    return voice_profile, None


def _extract_wav_bytes(response: requests.Response) -> bytes:
    content_type = (response.headers.get("content-type") or "").lower()
    if "application/json" not in content_type:
        return cast(bytes, response.content)

    payload = response.json()
    for key in ("audio_base64", "audio", "audio_content"):
        raw = payload.get(key)
        if isinstance(raw, str) and raw.strip():
            return base64.b64decode(raw)

    audio_url = payload.get("audio_url")
    if isinstance(audio_url, str) and audio_url.strip():
        follow = requests.get(audio_url, timeout=60)
        follow.raise_for_status()
        return cast(bytes, follow.content)

    raise ValueError("Kokoro JSON response did not contain audio bytes")


def generate_tts(
    text: str,
    voice_profile: str | None = None,
    speed: float = 0.85,
    learner_id: str | None = None,
    session_id: str | None = None,
) -> dict[str, Any]:
    """Generate TTS with calm defaults and robust fallbacks."""
    if not text.strip():
        return {"audio_url": None, "word_timestamps": [], "warning": "No text provided for TTS."}

    voice, voice_warning = _resolve_voice(voice_profile)
    speed_value = max(0.7, min(1.2, float(speed)))

    key = _cache_key(text, voice, speed_value)
    wav_path = _AUDIO_DIR / f"{key}.wav"

    if wav_path.exists():
        duration_ms = _duration_from_wav(wav_path)
        timestamps, timestamp_confidence = extract_word_timestamps_with_confidence(
            str(wav_path), text=text
        )
        payload = {
            "audio_url": str(wav_path),
            "duration_ms": duration_ms,
            "word_timestamps": timestamps,
            "timestamp_confidence": timestamp_confidence,
            "voice_profile": voice,
            "cache_hit": True,
        }
        if voice_warning:
            payload["warning"] = voice_warning
        return payload

    payload = {
        "model": "kokoro",
        "input": text,
        "voice": voice,
        "speed": speed_value,
        "response_format": "wav",
    }

    try:
        response = requests.post(
            f"{_base_url()}/v1/audio/speech",
            json=payload,
            timeout=float(os.getenv("LATENCY_BUDGET_AUDIO", "3")),
        )
        response.raise_for_status()
        wav_path.write_bytes(_extract_wav_bytes(response))

        duration_ms = _duration_from_wav(wav_path)
        timestamps, timestamp_confidence = extract_word_timestamps_with_confidence(
            str(wav_path), text=text
        )

        result = {
            "audio_url": str(wav_path),
            "duration_ms": duration_ms,
            "word_timestamps": timestamps,
            "timestamp_confidence": timestamp_confidence,
            "voice_profile": voice,
            "cache_hit": False,
            "learner_id": learner_id,
            "session_id": session_id,
        }
        if voice_warning:
            result["warning"] = voice_warning
        return result
    except Exception as exc:
        warning = f"Kokoro unavailable; served text-only fallback ({exc})."
        if voice_warning:
            warning = f"{voice_warning} {warning}".strip()
        return {
            "audio_url": None,
            "duration_ms": 0,
            "word_timestamps": [],
            "timestamp_confidence": None,
            "voice_profile": voice,
            "warning": warning,
        }
