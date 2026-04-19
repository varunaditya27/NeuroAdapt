"""Tier-3 avatar generation with LivePortrait integration and fallback."""

from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path
from typing import Dict, List

def _resolve_avatar_dir() -> Path:
    preferred = Path(__file__).resolve().parents[1] / "cache" / "avatars"
    try:
        preferred.mkdir(parents=True, exist_ok=True)
        return preferred
    except Exception:
        fallback = Path(os.getenv("GEN_ENGINE_CACHE_DIR", "/tmp/neuroadapt-gen-engine")) / "avatars"
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback


_AVATAR_DIR = _resolve_avatar_dir()


def _cache_key(source_image: str, audio_url: str) -> str:
    return hashlib.md5(f"{source_image}:{audio_url}".encode("utf-8")).hexdigest()


def _candidate_script() -> Path | None:
    root = os.getenv("LIVEPORTRAIT_DIR")
    if not root:
        return None
    script = Path(root) / "inference.py"
    return script if script.exists() else None


def generate_avatar_video(
    source_image: str,
    audio_url: str,
    word_timestamps: List[dict] | None = None,
    learner_id: str | None = None,
) -> Dict:
    """Generate talking avatar video if LivePortrait is configured, otherwise fallback."""
    source_path = Path(source_image) if source_image else None
    audio_path = Path(audio_url) if audio_url else None

    if not source_path or not source_path.exists() or not audio_path or not audio_path.exists():
        return {
            "avatar_video_url": None,
            "warning": "Missing image/audio for avatar generation.",
            "audio_url": audio_url,
            "word_timestamps": word_timestamps or [],
        }

    key = _cache_key(str(source_path), str(audio_path))
    out_video = _AVATAR_DIR / f"{key}.mp4"
    if out_video.exists():
        return {
            "avatar_video_url": str(out_video),
            "audio_url": str(audio_path),
            "word_timestamps": word_timestamps or [],
            "cache_hit": True,
        }

    script = _candidate_script()
    if script is None:
        return {
            "avatar_video_url": None,
            "audio_url": str(audio_path),
            "word_timestamps": word_timestamps or [],
            "image_url": str(source_path),
            "warning": "LivePortrait not configured; served static avatar with audio.",
            "learner_id": learner_id,
        }

    cmd = [
        "python",
        str(script),
        "--source_image",
        str(source_path),
        "--driving_audio",
        str(audio_path),
        "--output",
        str(out_video),
    ]

    try:
        result = subprocess.run(
            cmd,
            cwd=str(script.parent),
            capture_output=True,
            text=True,
            timeout=float(os.getenv("LATENCY_BUDGET_AVATAR", "20")),
        )
        if result.returncode == 0 and out_video.exists():
            return {
                "avatar_video_url": str(out_video),
                "audio_url": str(audio_path),
                "word_timestamps": word_timestamps or [],
                "cache_hit": False,
            }

        return {
            "avatar_video_url": None,
            "audio_url": str(audio_path),
            "word_timestamps": word_timestamps or [],
            "image_url": str(source_path),
            "warning": (
                "LivePortrait failed; served static avatar with audio. "
                f"Details: {result.stderr[:240]}"
            ),
        }
    except Exception as exc:
        return {
            "avatar_video_url": None,
            "audio_url": str(audio_path),
            "word_timestamps": word_timestamps or [],
            "image_url": str(source_path),
            "warning": f"Avatar timeout/error; served static avatar with audio ({exc}).",
        }
