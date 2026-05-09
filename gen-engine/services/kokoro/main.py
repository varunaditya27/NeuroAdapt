"""
Kokoro TTS service — neural synthesis with espeak fallback.
Serves the OpenAI-compatible /v1/audio/speech endpoint.
"""
from __future__ import annotations

import io
import logging
import math
import os
import re
import shutil
import struct
import subprocess
import tempfile
import uuid
import wave
from pathlib import Path
from typing import List, Optional

import numpy as np
from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

app = FastAPI(
    title="kokoro-tts",
    version="1.0.0",
    description="Neural TTS with Kokoro ONNX — NeuroAdapt gen-engine audio layer",
)

_VOICE_DIR = Path(os.getenv("KOKORO_VOICES_DIR", "/app/voices"))
_VOICE_DIR.mkdir(parents=True, exist_ok=True)

# ── Kokoro ONNX model (loaded once at startup) ────────────────────────────────
_kokoro: object | None = None
_KOKORO_MODEL  = os.getenv("KOKORO_MODEL_PATH",  "kokoro-v1.0.onnx")
_KOKORO_VOICES = os.getenv("KOKORO_VOICES_PATH", "voices.bin")

def _get_kokoro():
    global _kokoro
    if _kokoro is not None:
        return _kokoro
    try:
        from kokoro_onnx import Kokoro
        _kokoro = Kokoro(_KOKORO_MODEL, _KOKORO_VOICES)
        logger.info("Kokoro ONNX model loaded successfully")
    except Exception as exc:
        logger.warning(f"Kokoro ONNX unavailable, will use espeak fallback: {exc}")
        _kokoro = None
    return _kokoro


# ── Voice registry ────────────────────────────────────────────────────────────
# Maps Kokoro voice IDs to their kokoro-onnx voice names.
# Full list: af_bella, af_sarah, af_sky, am_adam, am_michael, bf_emma, bm_george
_VOICE_MAP = {
    "af_bella":   "af_bella",   # warm American female — DEFAULT, best for learning
    "af_sarah":   "af_sarah",   # clear American female, slightly brighter
    "af_sky":     "af_sky",     # energetic American female, good for grade5
    "am_adam":    "am_adam",    # calm American male
    "am_michael": "am_michael", # authoritative American male, good for university
    "bf_emma":    "bf_emma",    # British female, clear diction
    "bm_george":  "bm_george",  # British male, measured pace
}

# ── Learner-level speed presets ───────────────────────────────────────────────
_LEVEL_SPEED = {
    "grade5":     0.80,   # Slower, more time per word, better for younger/ADHD learners
    "grade8":     0.88,   # Default pace, clear and unhurried
    "university": 0.95,   # Slightly faster, respects information density
}

class SpeechRequest(BaseModel):
    model: str            = Field(default="kokoro")
    input: str
    voice: str            = Field(default="af_bella")
    speed: float          = Field(default=0.88)
    response_format: str  = Field(default="wav")
    learner_level: str    = Field(default="grade8")    # NEW: for speed preset
    ssml: bool            = Field(default=True)        # NEW: enable text preprocessing


# ── Text preprocessing for natural prosody ───────────────────────────────────

_NUMBER_WORDS = {
    "0":"zero","1":"one","2":"two","3":"three","4":"four",
    "5":"five","6":"six","7":"seven","8":"eight","9":"nine",
    "10":"ten","11":"eleven","12":"twelve","13":"thirteen",
    "14":"fourteen","15":"fifteen","16":"sixteen","17":"seventeen",
    "18":"eighteen","19":"nineteen","20":"twenty","100":"hundred",
    "1000":"thousand",
}

def _expand_numbers(text: str) -> str:
    """Replace bare digits with spoken words for cleaner TTS."""
    def replace(m):
        n = m.group(0)
        return _NUMBER_WORDS.get(n, n)
    return re.sub(r"\b\d+\b", replace, text)

def _preprocess_text(text: str, learner_level: str = "grade8") -> str:
    """
    Clean and enrich text for better neural TTS prosody.
    - Expand abbreviations and numbers
    - Normalize punctuation for correct pause insertion
    - Strip markdown/LaTeX artefacts that espeak/kokoro mispronounce
    """
    # Strip markdown artefacts
    text = re.sub(r"\*{1,2}([^*]+)\*{1,2}", r"\1", text)   # bold/italic
    text = re.sub(r"`[^`]+`", "", text)                      # code spans
    text = re.sub(r"\$[^$]+\$", "formula", text)             # inline LaTeX
    text = re.sub(r"#+\s*", "", text)                        # headers
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)    # markdown links

    # Expand common abbreviations
    abbrevs = {
        r"\beg\b": "for example",
        r"\bie\b": "that is",
        r"\betc\b": "et cetera",
        r"\bvs\b": "versus",
        r"\bw/\b": "with",
        r"\bw/o\b": "without",
        r"\bapprox\b": "approximately",
        r"\btemp\b": "temperature",
        r"\bfreq\b": "frequency",
    }
    for pattern, replacement in abbrevs.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

    # Expand numbers
    text = _expand_numbers(text)

    # Normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()

    # For grade5: add comma pauses after key conjunctions for better comprehension
    if learner_level == "grade5":
        text = re.sub(r"\b(because|however|therefore|so that|which means)\b",
                      r", \1,", text, flags=re.IGNORECASE)

    return text


# ── Audio helpers ─────────────────────────────────────────────────────────────

def _clamp_speed(value: float) -> float:
    return max(0.7, min(1.2, float(value)))

def _silence_wav_bytes(duration_ms: int, sample_rate: int = 24_000) -> bytes:
    frames = int(sample_rate * (duration_ms / 1000.0))
    payload = b"\x00\x00" * max(1, frames)
    with io.BytesIO() as buf:
        with wave.open(buf, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(sample_rate)
            w.writeframes(payload)
        return buf.getvalue()

def _np_to_wav_bytes(samples: "np.ndarray", sample_rate: int) -> bytes:
    """Convert float32 numpy array to 16-bit PCM WAV bytes."""
    pcm = np.clip(samples, -1.0, 1.0)
    pcm_int16 = (pcm * 32767).astype(np.int16)
    with io.BytesIO() as buf:
        with wave.open(buf, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(sample_rate)
            w.writeframes(pcm_int16.tobytes())
        return buf.getvalue()

def _duration_from_wav_bytes(wav_bytes: bytes) -> int:
    try:
        with io.BytesIO(wav_bytes) as buf:
            with wave.open(buf, "rb") as w:
                return int((w.getnframes() / w.getframerate()) * 1000)
    except Exception:
        return 0

def _duration_from_wav_file(path: Path) -> int:
    try:
        with wave.open(str(path), "rb") as w:
            return int((w.getnframes() / w.getframerate()) * 1000)
    except Exception:
        return 0


# ── Timestamp generation ──────────────────────────────────────────────────────

def _proportional_word_timestamps(text: str, duration_ms: int) -> List[dict]:
    """
    Generate word timestamps proportional to word length rather than uniform.
    Longer words get more time. Punctuation adds pause after preceding word.
    Significantly more accurate than the uniform step distribution.
    """
    words = [w for w in text.split() if w.strip()]
    if not words or duration_ms <= 0:
        return []

    # Weight each word by character length (proxy for phoneme count)
    weights = []
    for word in words:
        clean = re.sub(r"[^a-zA-Z0-9]", "", word)
        weight = max(1.5, len(clean) * 0.9)
        # Punctuation suffix → add pause weight
        if word.endswith((",", ";", "—")):
            weight += 1.5
        elif word.endswith((".", "!", "?")):
            weight += 2.5
        weights.append(weight)

    total_weight = sum(weights)
    cursor = 0
    stamps: List[dict] = []
    for word, w in zip(words, weights):
        duration = int((w / total_weight) * duration_ms)
        stamps.append({
            "word": word,
            "start_ms": cursor,
            "end_ms": cursor + duration,
        })
        cursor += duration
    return stamps


# ── Synthesis backends ────────────────────────────────────────────────────────

def _synthesize_kokoro(text: str, voice: str, speed: float) -> bytes | None:
    """Primary: neural synthesis via kokoro-onnx."""
    kokoro = _get_kokoro()
    if kokoro is None:
        return None
    try:
        voice_name = _VOICE_MAP.get(voice, voice)
        # kokoro-onnx returns (samples: np.ndarray, sample_rate: int)
        samples, sample_rate = kokoro.create(text, voice=voice_name, speed=speed)
        return _np_to_wav_bytes(samples, sample_rate)
    except Exception as exc:
        logger.warning(f"Kokoro ONNX synthesis failed: {exc}")
        return None

def _espeak_voice_id(voice: str) -> str:
    lowered = (voice or "").lower()
    if "bella" in lowered or "sarah" in lowered or "sky" in lowered or "emma" in lowered or lowered.startswith("af_") or lowered.startswith("bf_"):
        return "en+f3"
    if "adam" in lowered or "michael" in lowered or "george" in lowered or lowered.startswith("am_") or lowered.startswith("bm_"):
        return "en+m3"
    return "en"

def _synthesize_espeak(text: str, voice: str, speed: float) -> bytes | None:
    """Secondary fallback: espeak-ng."""
    binary = shutil.which("espeak-ng") or shutil.which("espeak")
    if binary is None:
        return None
    wpm = int(max(120, min(220, 165 * _clamp_speed(speed))))
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    try:
        proc = subprocess.run(
            [binary, "-v", _espeak_voice_id(voice), "-s", str(wpm),
             "-a", "180",       # amplitude (louder = clearer)
             "-g", "8",         # gap between words (ms) — improves clarity
             "-w", str(tmp_path), text],
            capture_output=True, text=True, timeout=12,
        )
        if proc.returncode != 0 or not tmp_path.exists() or tmp_path.stat().st_size == 0:
            return None
        return tmp_path.read_bytes()
    except Exception:
        return None
    finally:
        tmp_path.unlink(missing_ok=True)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health")
def health() -> JSONResponse:
    kokoro_available = _get_kokoro() is not None
    espeak_available = bool(shutil.which("espeak-ng") or shutil.which("espeak"))
    return JSONResponse({
        "status": "ok",
        "service": "kokoro-tts",
        "synthesis_backend": "kokoro-onnx" if kokoro_available else ("espeak" if espeak_available else "silence"),
        "kokoro_loaded": kokoro_available,
        "voices_available": list(_VOICE_MAP.keys()),
    })

@app.post("/v1/audio/speech")
def synthesize_speech(payload: SpeechRequest) -> Response:
    text = (payload.input or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="input text is required")

    # Determine effective speed: learner_level preset takes precedence over bare speed
    level_speed = _LEVEL_SPEED.get(payload.learner_level, payload.speed)
    speed = _clamp_speed(level_speed)

    # Preprocess text for natural prosody
    processed = _preprocess_text(text, learner_level=payload.learner_level) if payload.ssml else text

    # Synthesis chain: Kokoro ONNX → espeak → silence
    wav_bytes = _synthesize_kokoro(processed, voice=payload.voice, speed=speed)
    if wav_bytes is None:
        logger.info("Kokoro ONNX unavailable, falling back to espeak-ng")
        wav_bytes = _synthesize_espeak(processed, voice=payload.voice, speed=speed)
    if not wav_bytes:
        duration_ms = max(500, len(text.split()) * int(60_000 / (150 * speed)))
        wav_bytes = _silence_wav_bytes(duration_ms)

    return Response(content=wav_bytes, media_type="audio/wav")

@app.get("/v1/audio/timestamps")
def get_timestamps(
    audio_path: str = Query(..., min_length=1),
    text: str | None = Query(default=None),
) -> JSONResponse:
    file_path = Path(audio_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="audio file not found")
    duration_ms = _duration_from_wav_file(file_path)
    source_text = (text or "audio playback").strip()
    stamps = _proportional_word_timestamps(source_text, duration_ms)
    return JSONResponse({"timestamps": stamps, "duration_ms": duration_ms})

@app.post("/v1/audio/speech/with_timestamps")
def synthesize_with_timestamps(payload: SpeechRequest) -> JSONResponse:
    """
    Combined endpoint: returns audio (base64 WAV) + word timestamps in one call.
    Eliminates the extra round-trip that kokoro_tts.py currently makes.
    Preferred for the Manim A/V sync pipeline.
    """
    text = (payload.input or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="input text is required")

    level_speed = _LEVEL_SPEED.get(payload.learner_level, payload.speed)
    speed = _clamp_speed(level_speed)
    processed = _preprocess_text(text, learner_level=payload.learner_level) if payload.ssml else text

    wav_bytes = _synthesize_kokoro(processed, voice=payload.voice, speed=speed)
    synthesis_backend = "kokoro-onnx"
    if wav_bytes is None:
        wav_bytes = _synthesize_espeak(processed, voice=payload.voice, speed=speed)
        synthesis_backend = "espeak"
    if not wav_bytes:
        duration_ms = max(500, len(text.split()) * int(60_000 / (150 * speed)))
        wav_bytes = _silence_wav_bytes(duration_ms)
        synthesis_backend = "silence"

    duration_ms = _duration_from_wav_bytes(wav_bytes)
    stamps = _proportional_word_timestamps(processed, duration_ms)

    import base64
    return JSONResponse({
        "audio_base64": base64.b64encode(wav_bytes).decode("utf-8"),
        "audio_format": "wav",
        "duration_ms": duration_ms,
        "word_timestamps": stamps,
        "synthesis_backend": synthesis_backend,
        "processed_text": processed,
    })

@app.post("/v1/voices/create")
async def create_voice_profile(
    audio: UploadFile = File(...),
    name: str = Form(...),
) -> JSONResponse:
    cleaned_name = name.strip()
    if not cleaned_name:
        raise HTTPException(status_code=400, detail="voice name is required")
    sample_bytes = await audio.read()
    if not sample_bytes:
        raise HTTPException(status_code=400, detail="voice sample is empty")
    suffix = Path(audio.filename or "sample.wav").suffix or ".wav"
    voice_id = f"{cleaned_name.lower().replace(' ', '_')}_{uuid.uuid4().hex[:8]}"
    (_VOICE_DIR / f"{voice_id}{suffix}").write_bytes(sample_bytes)
    return JSONResponse({"voice_id": voice_id, "voice_name": cleaned_name})