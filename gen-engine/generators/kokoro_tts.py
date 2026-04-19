"""Tier-3 Kokoro TTS generation utilities."""

from __future__ import annotations

import hashlib
import os
import wave
from pathlib import Path
from typing import Dict, List

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


def _heuristic_word_timestamps(text: str, duration_ms: int) -> List[dict]:
    words = [w for w in text.split() if w.strip()]
    if not words:
        return []
    step = max(120, int(duration_ms / len(words))) if duration_ms > 0 else 220
    out = []
    cursor = 0
    for word in words:
        out.append({"word": word, "start_ms": cursor, "end_ms": cursor + step})
        cursor += step
    return out


def extract_word_timestamps(audio_path: str, text: str | None = None) -> List[dict]:
    """Use Kokoro alignment endpoint if available, else fall back to heuristic timings."""
    try:
        response = requests.get(
            f"{_base_url()}/v1/audio/timestamps",
            params={"audio_path": audio_path},
            timeout=2,
        )
        response.raise_for_status()
        data = response.json()
        stamps = data.get("timestamps")
        if isinstance(stamps, list):
            return stamps
    except Exception:
        pass

    duration_ms = _duration_from_wav(Path(audio_path))
    return _heuristic_word_timestamps(text or "", duration_ms)


def clone_voice_from_sample(sample_audio_path: str, voice_name: str) -> Dict:
    """Create a Kokoro voice profile from a short sample."""
    with open(sample_audio_path, "rb") as sample_file:
        response = requests.post(
            f"{_base_url()}/v1/voices/create",
            files={"audio": sample_file},
            data={"name": voice_name},
            timeout=10,
        )
    response.raise_for_status()
    payload = response.json()
    return {
        "voice_id": payload.get("voice_id"),
        "voice_name": voice_name,
    }


def generate_tts(
    text: str,
    voice_profile: str | None = None,
    speed: float = 0.85,
    learner_id: str | None = None,
    session_id: str | None = None,
) -> Dict:
    """Generate TTS with calm defaults and robust fallbacks."""
    if not text.strip():
        return {"audio_url": None, "word_timestamps": [], "warning": "No text provided for TTS."}

    voice = voice_profile or os.getenv("KOKORO_DEFAULT_VOICE", "af_bella")
    speed_value = max(0.7, min(1.2, float(speed)))

    key = _cache_key(text, voice, speed_value)
    wav_path = _AUDIO_DIR / f"{key}.wav"

    if wav_path.exists():
        duration_ms = _duration_from_wav(wav_path)
        timestamps = _heuristic_word_timestamps(text, duration_ms)
        return {
            "audio_url": str(wav_path),
            "duration_ms": duration_ms,
            "word_timestamps": timestamps,
            "voice_profile": voice,
            "cache_hit": True,
        }

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
        wav_path.write_bytes(response.content)

        duration_ms = _duration_from_wav(wav_path)
        timestamps = extract_word_timestamps(str(wav_path), text=text)

        return {
            "audio_url": str(wav_path),
            "duration_ms": duration_ms,
            "word_timestamps": timestamps,
            "voice_profile": voice,
            "cache_hit": False,
            "learner_id": learner_id,
            "session_id": session_id,
        }
    except Exception as exc:
        return {
            "audio_url": None,
            "duration_ms": 0,
            "word_timestamps": [],
            "voice_profile": voice,
            "warning": f"Kokoro unavailable; served text-only fallback ({exc}).",
        }
