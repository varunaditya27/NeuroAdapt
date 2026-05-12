"""Audio narration generator.

Uses the existing Kokoro TTS pipeline to produce narrated audio assets
with transcripts and metadata for the frontend AudioRenderer.
"""

from __future__ import annotations

from typing import Any

from generators.kokoro_tts import generate_tts


def generate_audio_narration(
    text: str,
    learner_level: str = "grade8",
    voice_profile: str | None = None,
    learner_id: str | None = None,
    session_id: str | None = None,
    title: str | None = None,
    speed: float = 0.88,
) -> dict[str, Any]:
    """Generate narrated audio with transcript metadata."""

    tts_result = generate_tts(
        text,
        voice_profile=voice_profile,
        speed=speed,
        learner_level=learner_level,
        learner_id=learner_id,
        session_id=session_id,
    )

    duration_ms = int(tts_result.get("duration_ms") or 0)
    suggested_duration_seconds = None
    if duration_ms > 0:
        suggested_duration_seconds = max(1, int(round(duration_ms / 1000)))

    return {
        **tts_result,
        "transcript": text,
        "title": title or "Narrated Explanation",
        "suggested_duration_seconds": suggested_duration_seconds,
    }
