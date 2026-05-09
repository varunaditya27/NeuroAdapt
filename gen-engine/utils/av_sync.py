"""Audio-Video Synchronization utilities for Manim + Kokoro TTS coordination.

Produces WebVTT subtitle/cue files and JSON sync manifests consumed by the
frontend ContentRenderer. Designed for the NeuroAdapt Manim + Kokoro pipeline.

Standards:
  - WebVTT: https://www.w3.org/TR/webvtt1/
  - X-TIMESTAMP-MAP: RFC 8216 §4.4.5 (HLS precise sync header)
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ── Timestamp formatting ──────────────────────────────────────────────────────

def format_vtt_timestamp(milliseconds: int | float) -> str:
    """Format milliseconds as WebVTT timestamp string HH:MM:SS.mmm."""
    total_ms = max(0, int(milliseconds))
    ms = total_ms % 1_000
    total_s = total_ms // 1_000
    s = total_s % 60
    m = (total_s // 60) % 60
    h = total_s // 3_600
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"


# ── Beat / cue alignment helpers ──────────────────────────────────────────────

def _clamp_beats_to_duration(
    beats: list[dict[str, Any]], duration_ms: float
) -> list[dict[str, Any]]:
    """
    Remove beats that start after the video ends and clamp end times to
    duration_ms. Ensures no VTT cue references a time beyond the video.
    """
    clamped = []
    for beat in beats:
        at_s = float(beat.get("at_s", 0))
        start_ms = int(at_s * 1_000)
        if start_ms >= duration_ms:
            continue
        clamped.append(beat)
    return clamped


def _resolve_beat_end_times(
    beats: list[dict[str, Any]], duration_ms: float
) -> list[tuple[int, int, str]]:
    """
    Return (start_ms, end_ms, text) tuples for each beat.

    End time rules (in priority order):
      1. start_ms of next beat minus a 50 ms gap
      2. start_ms + 1 200 ms (if last beat or next beat is far away)
      3. Clamped to duration_ms - 50 ms
    """
    sorted_beats = sorted(beats, key=lambda b: float(b.get("at_s", 0)))
    result: list[tuple[int, int, str]] = []

    for i, beat in enumerate(sorted_beats):
        text = (beat.get("text") or "").strip()
        if not text:
            continue
        start_ms = int(float(beat.get("at_s", 0)) * 1_000)

        if i + 1 < len(sorted_beats):
            next_start_ms = int(float(sorted_beats[i + 1].get("at_s", 0)) * 1_000)
            # Use next beat boundary minus gap, but don't shrink below 200 ms
            end_ms = max(start_ms + 200, next_start_ms - 50)
        else:
            end_ms = start_ms + 1_200

        # Hard clamp to video duration
        end_ms = min(end_ms, max(start_ms + 100, int(duration_ms) - 50))
        result.append((start_ms, end_ms, text))

    return result


def _resolve_word_end_times(
    word_timestamps: list[dict[str, Any]], duration_ms: float
) -> list[tuple[int, int, str]]:
    """
    Return (start_ms, end_ms, word) tuples from word_timestamps.

    Accepts both:
      - {"word": "...", "start_ms": ..., "end_ms": ...}  (kokoro_tts.py format)
      - {"text": "...", "start_ms": ..., "end_ms": ...}  (backward compat)

    Fills missing end_ms by using start_ms of the next word minus 10 ms,
    or start_ms + 100 ms as a last resort.
    """
    # Normalise to list of (start_ms, text) first
    entries: list[tuple[int, str]] = []
    for item in word_timestamps:
        word = (item.get("word") or item.get("text") or "").strip()
        if not word:
            continue
        start_ms = int(item.get("start_ms", 0))
        entries.append((start_ms, word, int(item.get("end_ms", -1))))

    result: list[tuple[int, int, str]] = []
    for i, (start_ms, word, raw_end_ms) in enumerate(entries):
        if start_ms >= duration_ms:
            continue

        if raw_end_ms > start_ms:
            end_ms = raw_end_ms
        elif i + 1 < len(entries):
            end_ms = max(start_ms + 50, entries[i + 1][0] - 10)
        else:
            end_ms = start_ms + 100

        end_ms = min(end_ms, max(start_ms + 50, int(duration_ms) - 10))
        result.append((start_ms, end_ms, word))

    return result


# ── WebVTT generation ─────────────────────────────────────────────────────────

def generate_webvtt_metadata(
    output_path: str | Path,
    duration_ms: float,
    fps: float = 60.0,
    animation_beats: list[dict[str, Any]] | None = None,
    word_timestamps: list[dict[str, Any]] | None = None,
) -> str:
    """
    Generate a WebVTT file combining Manim animation beat cues and
    Kokoro TTS word-level subtitle cues.

    Cue types:
      [BEAT] — animation phase markers from the Manim NARRATION metadata.
               The frontend uses these to trigger caption overlay transitions.
      [WORD] — per-word TTS timestamps for karaoke-style highlighting.

    Both cue types are sorted by start time in the output file. Non-overlapping
    end times are guaranteed: no cue extends past the start of the next cue
    of the same type, and no cue extends past video duration.

    Args:
        output_path:       Path where the .vtt file is written.
        duration_ms:       Total video duration in milliseconds.
        fps:               Video frame rate (informational, written to header).
        animation_beats:   List of {"at_s": float, "text": str} dicts from
                           Manim NARRATION metadata.
        word_timestamps:   List of {"word": str, "start_ms": int, "end_ms": int}
                           dicts from kokoro_tts.generate_tts().

    Returns:
        The VTT file content as a string (also written to output_path).
    """
    animation_beats = animation_beats or []
    word_timestamps = word_timestamps or []
    duration_ms = max(1.0, float(duration_ms))

    # ── Resolve cue boundaries ────────────────────────────────────────────
    clamped_beats = _clamp_beats_to_duration(animation_beats, duration_ms)
    beat_cues = _resolve_beat_end_times(clamped_beats, duration_ms)
    word_cues = _resolve_word_end_times(word_timestamps, duration_ms)

    # ── Build VTT lines ───────────────────────────────────────────────────
    lines: list[str] = [
        "WEBVTT",
        "",
        # X-TIMESTAMP-MAP aligns WebVTT cue times to the video's MPEG-TS clock.
        # MPEGTS=0 means the video stream starts at PTS=0 (standard for MP4/WebM).
        "X-TIMESTAMP-MAP=MPEGTS=0,LOCAL=00:00:00.000",
        f"NOTE duration_ms={int(duration_ms)} fps={fps:.2f} "
        f"beats={len(beat_cues)} words={len(word_cues)}",
        "",
    ]

    cue_index = 1

    # Animation beat cues
    for start_ms, end_ms, text in beat_cues:
        lines.append(f"cue-{cue_index:04d}")
        lines.append(
            f"{format_vtt_timestamp(start_ms)} --> {format_vtt_timestamp(end_ms)}"
            " align:center line:85%"
        )
        lines.append(f"[BEAT] {text}")
        lines.append("")
        cue_index += 1

    # Word-level TTS cues
    for start_ms, end_ms, word in word_cues:
        lines.append(f"cue-{cue_index:04d}")
        lines.append(
            f"{format_vtt_timestamp(start_ms)} --> {format_vtt_timestamp(end_ms)}"
            " align:center line:95%"
        )
        lines.append(f"[WORD] {word}")
        lines.append("")
        cue_index += 1

    vtt_content = "\n".join(lines)

    # ── Write to disk ─────────────────────────────────────────────────────
    try:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(vtt_content, encoding="utf-8")
        logger.info(
            f"WebVTT written: {out} "
            f"({len(beat_cues)} beat cues, {len(word_cues)} word cues, "
            f"duration={int(duration_ms)}ms)"
        )
    except Exception as exc:
        logger.error(f"Failed to write WebVTT file to {output_path}: {exc}")

    return vtt_content


# ── JSON sync manifest ────────────────────────────────────────────────────────

def generate_sync_metadata_json(
    duration_ms: float,
    fps: float,
    animation_beats: list[dict[str, Any]] | None = None,
    word_timestamps: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    Generate a structured sync manifest as a dict for embedding in API responses.

    The frontend ContentRenderer consumes this to:
      - Schedule caption overlays at animation beat times
      - Drive karaoke-style word highlighting during audio playback
      - Confirm A/V alignment before starting playback

    Returns:
        {
          "duration_ms": int,
          "fps": float,
          "frame_count": int,
          "animation_beats": [...],   # original beat dicts unchanged
          "word_timestamps": [...],   # original word timestamp dicts unchanged
          "beat_cue_count": int,
          "word_cue_count": int,
        }
    """
    duration_ms = max(0.0, float(duration_ms))
    beats = animation_beats or []
    words = word_timestamps or []

    return {
        "duration_ms": int(duration_ms),
        "fps": float(fps),
        "frame_count": int((duration_ms / 1_000.0) * fps),
        "animation_beats": beats,
        "word_timestamps": words,
        "beat_cue_count": len(beats),
        "word_cue_count": len(words),
    }


# ── Convenience: generate both VTT + JSON in one call ────────────────────────

def generate_av_sync_package(
    vtt_output_path: str | Path,
    duration_ms: float,
    fps: float = 60.0,
    animation_beats: list[dict[str, Any]] | None = None,
    word_timestamps: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    Generate the WebVTT file and the JSON sync manifest together.

    Intended to be called from action_router.py after both the Manim render
    and the Kokoro TTS call have completed.

    Args:
        vtt_output_path:   Where to write the .vtt file.
        duration_ms:       Video duration (from manim video_metadata.duration_s * 1000).
        fps:               Video frame rate (from manim video_metadata.fps).
        animation_beats:   From manim_gen result["narration"]["beats"].
        word_timestamps:   From kokoro_tts result["word_timestamps"].

    Returns:
        {
          "vtt_path": str,
          "vtt_content": str,
          "sync_metadata": dict,   # same shape as generate_sync_metadata_json()
        }
    """
    vtt_content = generate_webvtt_metadata(
        output_path=vtt_output_path,
        duration_ms=duration_ms,
        fps=fps,
        animation_beats=animation_beats,
        word_timestamps=word_timestamps,
    )
    sync_metadata = generate_sync_metadata_json(
        duration_ms=duration_ms,
        fps=fps,
        animation_beats=animation_beats,
        word_timestamps=word_timestamps,
    )
    return {
        "vtt_path": str(vtt_output_path),
        "vtt_content": vtt_content,
        "sync_metadata": sync_metadata,
    }