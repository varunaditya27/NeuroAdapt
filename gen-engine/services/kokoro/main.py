"""Minimal Kokoro-compatible local API for development and compose integration.

This service intentionally provides a lightweight compatibility surface so local
gen-engine flows can exercise audio and timestamp branches without requiring a
full external Kokoro deployment.
"""

from __future__ import annotations

import io
import math
import os
import shutil
import struct
import subprocess
import tempfile
import uuid
import wave
from pathlib import Path
from typing import List

from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field

app = FastAPI(
    title="kokoro-tts",
    version="0.2.0",
    description="Kokoro-compatible TTS API surface for local development",
)

_VOICE_DIR = Path(os.getenv("KOKORO_VOICES_DIR", "/app/voices"))
_VOICE_DIR.mkdir(parents=True, exist_ok=True)


class SpeechRequest(BaseModel):
    model: str = Field(default="kokoro")
    input: str
    voice: str = Field(default="af_bella")
    speed: float = Field(default=0.85)
    response_format: str = Field(default="wav")


def _clamp_speed(value: float) -> float:
    return max(0.7, min(1.2, float(value)))


def _estimate_duration_ms(text: str, speed: float) -> int:
    words = max(1, len([w for w in text.split() if w.strip()]))
    words_per_minute = max(90.0, 150.0 * _clamp_speed(speed))
    return max(500, int((words / words_per_minute) * 60_000))


def _silence_wav_bytes(duration_ms: int, sample_rate: int = 44_100) -> bytes:
    frames = int(sample_rate * (duration_ms / 1000.0))
    payload = b"\x00\x00" * max(1, frames)

    with io.BytesIO() as buffer:
        with wave.open(buffer, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)  # 16-bit PCM
            wav.setframerate(sample_rate)
            wav.writeframes(payload)
        return buffer.getvalue()


def _espeak_binary() -> str | None:
    return shutil.which("espeak-ng") or shutil.which("espeak")


def _espeak_voice(voice: str) -> str:
    lowered = (voice or "").lower()
    if lowered.startswith("af_") or "bella" in lowered or "female" in lowered:
        return "en+f3"
    if lowered.startswith("am_") or "male" in lowered:
        return "en+m3"
    return "en"


def _synthesize_espeak_wav_bytes(text: str, voice: str, speed: float) -> bytes | None:
    binary = _espeak_binary()
    if binary is None:
        return None

    words_per_minute = int(max(120, min(240, 175 * _clamp_speed(speed))))
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    try:
        cmd = [
            binary,
            "-v",
            _espeak_voice(voice),
            "-s",
            str(words_per_minute),
            "-w",
            str(tmp_path),
            text,
        ]
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=8,
        )
        if proc.returncode != 0 or (not tmp_path.exists()) or tmp_path.stat().st_size == 0:
            return None
        return tmp_path.read_bytes()
    except Exception:
        return None
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass


def _tone_wav_bytes(text: str, speed: float, sample_rate: int = 22_050) -> bytes:
    """Audible fallback when real TTS engines are unavailable."""
    words = [w for w in text.split() if w.strip()]
    if not words:
        return _silence_wav_bytes(400, sample_rate=sample_rate)

    clamped_speed = _clamp_speed(speed)
    audio = bytearray()
    max_words = words[:120]

    for idx, word in enumerate(max_words):
        checksum = sum(ord(ch) for ch in word)
        base_freq = 170 + (checksum % 42) * 11
        duration_ms = int(max(80, min(260, (120 + len(word) * 18) / clamped_speed)))
        amplitude = 11_000
        samples = int(sample_rate * (duration_ms / 1000.0))

        for n in range(samples):
            envelope = min(1.0, n / max(1, samples * 0.15)) * min(
                1.0, (samples - n) / max(1, samples * 0.2)
            )
            sample = int(
                amplitude * envelope * math.sin((2.0 * math.pi * base_freq * n) / sample_rate)
            )
            audio.extend(struct.pack("<h", sample))

        # Word break pause.
        pause_ms = 40 if idx < len(max_words) - 1 else 120
        pause_samples = int(sample_rate * (pause_ms / 1000.0))
        audio.extend(b"\x00\x00" * pause_samples)

    with io.BytesIO() as buffer:
        with wave.open(buffer, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(sample_rate)
            wav.writeframes(bytes(audio))
        return buffer.getvalue()


def _duration_from_wav(file_path: Path) -> int:
    try:
        with wave.open(str(file_path), "rb") as wav:
            frames = wav.getnframes()
            rate = wav.getframerate() or 44_100
            return int((frames / rate) * 1000)
    except Exception:
        return 0


def _timestamps_for_text(text: str, duration_ms: int) -> List[dict]:
    words = [word for word in text.split() if word.strip()]
    if not words:
        return []

    step = max(120, int(duration_ms / len(words))) if duration_ms > 0 else 220
    cursor = 0
    stamps: List[dict] = []
    for word in words:
        stamps.append({"word": word, "start_ms": cursor, "end_ms": cursor + step})
        cursor += step
    return stamps


@app.get("/health")
def health() -> JSONResponse:
    """Health check endpoint for Docker Compose and Kubernetes."""
    backend = "espeak" if _espeak_binary() else "tone-fallback"
    return JSONResponse(
        {
            "status": "ok",
            "service": "kokoro-tts",
            "mode": "compat",
            "synthesis_backend": backend,
        }
    )


@app.post("/v1/audio/speech")
def synthesize_speech(payload: SpeechRequest) -> Response:
    """OpenAI-compatible speech endpoint returning WAV bytes."""
    text = (payload.input or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="input text is required")

    if payload.response_format.lower() != "wav":
        raise HTTPException(status_code=400, detail="only wav response_format is supported")

    wav_bytes = _synthesize_espeak_wav_bytes(text, voice=payload.voice, speed=payload.speed)
    if wav_bytes is None:
        wav_bytes = _tone_wav_bytes(text, speed=payload.speed)

    if not wav_bytes:
        duration_ms = _estimate_duration_ms(text, payload.speed)
        wav_bytes = _silence_wav_bytes(duration_ms)

    return Response(content=wav_bytes, media_type="audio/wav")


@app.get("/v1/audio/timestamps")
def get_timestamps(
    audio_path: str = Query(..., min_length=1),
    text: str | None = Query(default=None),
) -> JSONResponse:
    """Return heuristic per-word timestamps for a local WAV file path."""
    file_path = Path(audio_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="audio file not found")

    duration_ms = _duration_from_wav(file_path)
    source_text = (text or "audio playback").strip()
    return JSONResponse({"timestamps": _timestamps_for_text(source_text, duration_ms)})


@app.post("/v1/voices/create")
async def create_voice_profile(
    audio: UploadFile = File(...),
    name: str = Form(...),
) -> JSONResponse:
    """Store uploaded sample and return a generated voice_id."""
    cleaned_name = name.strip()
    if not cleaned_name:
        raise HTTPException(status_code=400, detail="voice name is required")

    sample_bytes = await audio.read()
    if not sample_bytes:
        raise HTTPException(status_code=400, detail="voice sample is empty")

    suffix = Path(audio.filename or "sample.wav").suffix or ".wav"
    voice_id = f"{cleaned_name.lower().replace(' ', '_')}_{uuid.uuid4().hex[:8]}"
    target = _VOICE_DIR / f"{voice_id}{suffix}"
    target.write_bytes(sample_bytes)

    return JSONResponse({"voice_id": voice_id, "voice_name": cleaned_name})
