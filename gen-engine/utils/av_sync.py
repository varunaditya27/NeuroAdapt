"""Audio-Video Synchronization utilities for Manim + Kokoro TTS coordination.

Uses industry-standard WebVTT format with X-TIMESTAMP-MAP for precise A/V sync.
References:
  - W3C WebVTT Spec: https://www.w3.org/TR/webvtt1/
  - HLS Media Playlist (X-TIMESTAMP-MAP): RFC 8216, section 4.4.5
  - FFmpeg A/V Sync: timestamp-based frame synchronization
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def format_vtt_timestamp(milliseconds: int | float) -> str:
    """Format milliseconds as VTT timestamp HH:MM:SS.mmm.
    
    Args:
        milliseconds: Timestamp in milliseconds
        
    Returns:
        VTT-formatted timestamp (HH:MM:SS.mmm)
    """
    total_ms = int(milliseconds)
    ms = total_ms % 1000
    total_s = total_ms // 1000
    s = total_s % 60
    m = (total_s // 60) % 60
    h = total_s // 3600
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"


def generate_webvtt_metadata(
    output_path: str | Path,
    duration_ms: float,
    fps: float = 60.0,
    animation_beats: list[dict[str, Any]] | None = None,
    word_timestamps: list[dict[str, Any]] | None = None,
) -> str:
    """Generate WebVTT file with sync metadata for video + audio.
    
    Format uses X-TIMESTAMP-MAP header (HLS standard) to ensure precise sync
    between WebVTT cues and video playback. Each cue represents either an
    animation beat or a word boundary from TTS output.
    
    Args:
        output_path: Path where VTT file will be written
        duration_ms: Total video duration in milliseconds
        fps: Video frame rate (used for calculating frame count)
        animation_beats: List of beats with 'at_s' (seconds) and 'text' keys
        word_timestamps: List of words with 'start_ms' and 'text' keys
        
    Returns:
        VTT file content (string) and writes to disk
        
    Example animation_beats:
        [
            {"at_s": 0.5, "text": "Light enters the leaf"},
            {"at_s": 2.0, "text": "Electrons energized"},
        ]
        
    Example word_timestamps (from Kokoro TTS):
        [
            {"text": "Light", "start_ms": 50, "end_ms": 200},
            {"text": "enters", "start_ms": 200, "end_ms": 400},
        ]
    """
    animation_beats = animation_beats or []
    word_timestamps = word_timestamps or []
    
    # Calculate frame count for X-TIMESTAMP-MAP
    frame_count = int((duration_ms / 1000.0) * fps)
    
    # VTT header with X-TIMESTAMP-MAP (HLS standard for precise sync)
    lines = [
        "WEBVTT",
        "",
        f"X-TIMESTAMP-MAP=MPEGTS=0,LOCAL=00:00:00.000",
        "",
    ]
    
    # Add animation beat cues (from Manim narration)
    for beat in animation_beats:
        at_s = beat.get("at_s", 0)
        text = beat.get("text", "")
        if not text:
            continue
        
        start_ms = int(at_s * 1000)
        # Estimate end as start + 1 second or until next beat
        end_ms = start_ms + 1000
        
        start_vtt = format_vtt_timestamp(start_ms)
        end_vtt = format_vtt_timestamp(end_ms)
        
        lines.append(f"{start_vtt} --> {end_vtt}")
        lines.append(f"[ANIMATION] {text}")
        lines.append("")
    
    # Add word-level TTS cues (for closed captions / sync markers)
    for word_info in word_timestamps:
        # Accept "word" (Kokoro/gen-engine payload) or "text" (backward compat)
        text = word_info.get("word") or word_info.get("text", "")
        start_ms = word_info.get("start_ms", 0)
        end_ms = word_info.get("end_ms", start_ms + 100)
        
        if not text:
            continue
        
        start_vtt = format_vtt_timestamp(start_ms)
        end_vtt = format_vtt_timestamp(end_ms)
        
        lines.append(f"{start_vtt} --> {end_vtt}")
        lines.append(f"[WORD] {text}")
        lines.append("")
    
    vtt_content = "\n".join(lines)
    
    # Write to disk
    try:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(vtt_content, encoding="utf-8")
        logger.info(f"Generated WebVTT metadata: {output_path} ({len(animation_beats)} animation beats, {len(word_timestamps)} word cues)")
    except Exception as exc:
        logger.error(f"Failed to write WebVTT file: {exc}")
    
    return vtt_content


def generate_sync_metadata_json(
    duration_ms: float,
    fps: float,
    animation_beats: list[dict[str, Any]] | None = None,
    word_timestamps: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Generate structured sync metadata as JSON for API responses.
    
    Returns dict with precise timing information for frontend sync engines.
    """
    return {
        "duration_ms": int(duration_ms),
        "fps": fps,
        "frame_count": int((duration_ms / 1000.0) * fps),
        "animation_beats": animation_beats or [],
        "word_timestamps": word_timestamps or [],
    }
