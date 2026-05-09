"""Action routing and generation orchestration."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict
from uuid import uuid4

from generators.analogy_engine import generate_analogies
from generators.chunk_renderer import chunk_text
from generators.image_gen import generate_image
from generators.kokoro_tts import generate_tts
from generators.liveportrait_avatar import generate_avatar_video
from generators.manim_gen import generate_manim_animation
from generators.quiz_injector import generate_quiz
from generators.text_simplify import simplify_text
from models.request_schemas import GenerateRequest
from orchestration.hyperfocus_gate import check_hyperfocus
from orchestration.latency_budget import fallback_for, get_timeout_seconds, run_with_timeout
from utils.av_sync import generate_webvtt_metadata

logger = logging.getLogger(__name__)

_CONTENT_TYPE_NORMALIZATION = {
    "animation": "animation",
    "video": "animation",
    "manim": "animation",
    "stem": "animation",
    "math": "animation",
    "physics": "animation",
    "algorithm": "animation",
    "process": "animation",
    "image": "image",
    "visual": "image",
    "illustration": "image",
    "graphic": "image",
    "general": "image",
    "audio": "audio",
    "tts": "audio",
    "speech": "audio",
    "avatar": "avatar",
    "liveportrait": "avatar",
    "video_avatar": "avatar",
    "auto": "auto",
}


def classify_tier(action_id: int) -> str:
    if action_id in {1, 5}:
        return "tier1"
    if action_id in {2, 4}:
        return "tier2"
    return "tier3"


def _is_stem_content(text: str) -> bool:
    low = text.lower()
    # Expanded markers to include biology, chemistry, life sciences, and other STEM
    markers = [
        "equation", "vector", "force", "algorithm", "physics", "math", "graph", "derivative",
        "photosynthesis", "biology", "chemistry", "cell", "dna", "molecule", "atom",
        "reaction", "compound", "organic", "reaction", "enzyme", "protein", "gene",
        "membrane", "mitochondria", "chloroplast", "electron", "ion", "orbital",
        "periodic", "isotope", "valence", "bond", "catalysis"
    ]
    return any(marker in low for marker in markers)


def _resolved_content_type(request_data: dict[str, Any]) -> str:
    content_type = request_data.get("content_type")
    if content_type is not None:
        normalized = _CONTENT_TYPE_NORMALIZATION.get(str(content_type).strip().lower())
        if normalized and normalized != "auto":
            return normalized

    slide = str(request_data.get("slide_content", ""))
    if _is_stem_content(slide):
        return "animation"
    return "image"


def _safe_session_id(request_data: dict[str, Any]) -> str:
    return str(request_data.get("session_id", "unknown"))


def _get_env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _public_base_url() -> str:
    return os.getenv("GEN_ENGINE_PUBLIC_URL") or os.getenv("PUBLIC_BASE_URL") or "http://localhost:8001"


def _maybe_public_url(value: str) -> str:
    if not value:
        return value
    if value.startswith(("data:", "http://", "https://")):
        return value

    try:
        cache_root = (Path(__file__).resolve().parents[1] / "cache").resolve()
        candidate = Path(value).resolve()
        if candidate.is_relative_to(cache_root):
            relative = candidate.relative_to(cache_root).as_posix()
            return f"{_public_base_url().rstrip('/')}/media/{relative}"
    except Exception:
        return value

    return value


def _normalize_media_urls(payload: dict[str, Any]) -> dict[str, Any]:
    for key in ("audio_url", "video_url", "image_url", "metadata_vtt", "asset_path"):
        raw = payload.get(key)
        if isinstance(raw, str):
            payload[key] = _maybe_public_url(raw)
    return payload


def _generate_payload_for_action(action_id: int, request_data: dict[str, Any]) -> dict[str, Any]:
    slide_content = str(request_data.get("slide_content", ""))
    learner_level = str(request_data.get("learner_level", "grade8"))
    session_id = _safe_session_id(request_data)
    concept = str(request_data.get("concept") or "").strip() or slide_content[:80]
    state_vector = request_data.get("state_vector") or {}

    if action_id == 1:
        chunked = chunk_text(slide_content, chunk_strategy="sentence")
        return {
            "simplified_text": slide_content,
            "chunks": chunked.get("chunks", []),
            "encouragement_text": "Take it one chunk at a time—you've got this.",
        }

    if action_id == 2:
        timeout = get_timeout_seconds("text_simplify")
        result, timed_out, _, error = run_with_timeout(
            simplify_text,
            timeout,
            slide_content,
            learner_level,
            session_id,
        )

        if timed_out:
            payload = fallback_for("text_simplify", original_text=slide_content)
            payload.update(
                {
                    "fk_grade": None,
                    "original_fk": None,
                    "chunks": chunk_text(slide_content, chunk_strategy="sentence").get(
                        "chunks", []
                    ),
                }
            )
            return payload

        if error:
            payload = fallback_for("text_simplify", original_text=slide_content)
            payload["warning"] = f"Text simplification failed: {error}"
            payload["chunks"] = chunk_text(slide_content, chunk_strategy="sentence").get(
                "chunks", []
            )
            return payload

        if (
            state_vector.get("cognitive_load", 0.0) >= 0.82
            or state_vector.get("regression_count", 0) >= 6
        ):
            a_result, a_timed_out, _, _ = run_with_timeout(
                generate_analogies,
                get_timeout_seconds("analogy"),
                concept,
                slide_content,
                learner_level,
            )
            if not a_timed_out and a_result:
                result["analogies"] = a_result.get("analogies")
                if a_result.get("analogy_types"):
                    result["analogy_types"] = a_result.get("analogy_types")
                if a_result.get("warning") and not result.get("warning"):
                    result["warning"] = a_result.get("warning")

        return result

    if action_id == 3:
        content_type = _resolved_content_type(request_data)

        if content_type == "audio":
            res, timed_out, _, error = run_with_timeout(
                generate_tts,
                get_timeout_seconds("audio"),
                slide_content,
                request_data.get("voice_profile"),
                0.85,
                request_data.get("learner_id"),
                session_id,
            )
            if timed_out:
                return fallback_for("audio", original_text=slide_content)
            if error:
                return {"warning": f"Audio generation failed: {error}"}
            return res

        if content_type == "avatar":
            tts_res, tts_timed_out, _, _ = run_with_timeout(
                generate_tts,
                get_timeout_seconds("audio"),
                slide_content,
                request_data.get("voice_profile"),
                0.85,
                request_data.get("learner_id"),
                session_id,
            )
            if tts_timed_out or not tts_res.get("audio_url"):
                return fallback_for("avatar", original_text=slide_content)

            source_image = request_data.get("source_image")
            if not source_image:
                image_res = generate_image(
                    concept=concept, slide_content=slide_content, learner_level=learner_level
                )
                source_image = image_res.get("image_url")

            avatar_res, avatar_timed_out, _, avatar_error = run_with_timeout(
                generate_avatar_video,
                get_timeout_seconds("avatar"),
                str(source_image),
                str(tts_res.get("audio_url")),
                tts_res.get("word_timestamps") or [],
                request_data.get("learner_id"),
            )

            merged = {**tts_res, **(avatar_res or {})}
            if avatar_timed_out:
                merged.update(fallback_for("avatar"))
            if avatar_error:
                merged["warning"] = f"Avatar generation failed: {avatar_error}"
            return merged

        if content_type == "animation":
            anim_res, timed_out, _, error = run_with_timeout(
                generate_manim_animation,
                max(120, get_timeout_seconds("manim")),  # At least 120s for manim with Groq LLM
                concept,
                slide_content,
                learner_level,
                session_id,
            )

            if timed_out:
                # Cascading fallback: static image + optional audio
                image_res = generate_image(
                    concept=concept, slide_content=slide_content, learner_level=learner_level
                )
                audio_res = generate_tts(slide_content, speed=0.85, session_id=session_id)
                return {**image_res, **audio_res, **fallback_for("manim")}

            if error:
                image_res = generate_image(
                    concept=concept, slide_content=slide_content, learner_level=learner_level
                )
                return {**image_res, "warning": f"Animation failed: {error}"}

            if anim_res.get("video_url"):
                # Extract narration metadata if available
                narration = anim_res.get("narration")
                video_duration_s = anim_res.get("duration_ms", 0) / 1000.0
                video_metadata = anim_res.get("video_metadata") or {"fps": 60.0}
                
                # Use narration script if available, otherwise use slide_content
                tts_text = slide_content
                speed = 0.85  # default
                
                if narration and narration.get("script"):
                    tts_text = narration["script"]
                    # Calculate speed to match video duration
                    # Natural speech ≈ 2.5 words/second; aim to fill 90% of video
                    word_count = len(tts_text.split())
                    if video_duration_s > 0:
                        target_duration_s = video_duration_s * 0.9
                        natural_duration_s = word_count / 2.5
                        if natural_duration_s > 0:
                            speed = max(0.5, min(2.0, natural_duration_s / target_duration_s))
                
                audio_res = generate_tts(
                    tts_text,
                    speed=speed,
                    session_id=session_id,
                )
                
                # Attach animation beats to audio response for sync
                response = {**anim_res, **audio_res}
                if narration and narration.get("beats"):
                    response["animation_beats"] = narration["beats"]
                
                # Generate WebVTT metadata file for frontend sync
                video_url = str(anim_res.get("video_url", ""))
                if video_url:
                    try:
                        # Create VTT path next to video file (same stem)
                        video_path = Path(video_url)
                        vtt_path = video_path.parent / f"{video_path.stem}_sync.vtt"
                        
                        generate_webvtt_metadata(
                            output_path=vtt_path,
                            duration_ms=anim_res.get("duration_ms", 0),
                            fps=video_metadata.get("fps", 60.0),
                            animation_beats=narration.get("beats") if narration else None,
                            word_timestamps=audio_res.get("word_timestamps"),
                        )
                        response["metadata_vtt"] = str(vtt_path)
                    except Exception as exc:
                        logger.warning(f"WebVTT generation failed: {exc}")
                
                return response

            # animation function already returned fallback details
            if anim_res.get("image_url") and not anim_res.get("audio_url"):
                audio_res = generate_tts(slide_content, speed=0.85, session_id=session_id)
                return {**anim_res, **audio_res}
            return anim_res

        # default visual path (image)
        image_res, timed_out, _, error = run_with_timeout(
            generate_image,
            get_timeout_seconds("image"),
            concept,
            slide_content,
            learner_level,
            session_id,
        )
        if timed_out:
            return fallback_for("image", original_text=slide_content)
        if error:
            return {"warning": f"Image generation failed: {error}"}

        audio_res = generate_tts(slide_content, speed=0.85, session_id=session_id)
        return {**image_res, **audio_res}

    if action_id == 4:
        quiz_res, timed_out, _, error = run_with_timeout(
            generate_quiz,
            get_timeout_seconds("quiz"),
            slide_content,
            session_id,
            request_data.get("concept"),
            request_data.get("learner_id"),
        )
        if timed_out:
            return fallback_for("quiz", original_text=slide_content)
        if error:
            payload = fallback_for("quiz", original_text=slide_content)
            payload["warning"] = f"Quiz generation failed: {error}"
            return payload
        return quiz_res

    if action_id == 5:
        return {
            "title": "Sensory Reset",
            "break_template": (
                "Pause. Breathe in for 4, hold for 4, out for 6. "
                "Roll shoulders, drink water, then continue when ready."
            ),
            "suggested_duration_seconds": 90,
            "encouragement_text": "Reset complete—ready when you are.",
        }

    return {
        "simplified_text": slide_content,
        "warning": f"Unsupported action_id={action_id}; served original content.",
    }

def route_and_generate(request: GenerateRequest) -> Dict[str, Any]:
    """Main request router called by API endpoint."""
    request_data = request.model_dump(mode="json")
    session_id = str(request_data.get("session_id") or uuid4())
    state_vector = request_data.get("state_vector") or {}

    # Internal defaults for optional orchestration context.
    request_data["session_id"] = session_id
    request_data["state_vector"] = state_vector
    request_data["confidence"] = request_data.get("confidence") or 0.5
    request_data["concept"] = request_data.get("concept")
    request_data["content_type"] = request_data.get("content_type")
    request_data["learner_id"] = request_data.get("learner_id")
    request_data["voice_profile"] = request_data.get("voice_profile")
    request_data["source_image"] = request_data.get("source_image")

    should_preempt, composite, _ = check_hyperfocus(
        session_id=session_id, state_vector=state_vector
    )
    if should_preempt or request.action_id == 0:
        return {
            "action_id": 0,
            "content": {},
            "cache_hit": False,
            "warning": None,
            "error": None,
            "hyperfocus_override": should_preempt,
            "hyperfocus_composite": composite,
            "no_content": True,
        }

    payload = _generate_payload_for_action(request.action_id, request_data)
    cache_hit = bool(payload.get("cache_hit", False))

    # Ensure text actions always include chunks
    if request.action_id in {1, 2}:
        text_value = payload.get("simplified_text") or request.slide_content
        if not payload.get("chunks"):
            payload["chunks"] = chunk_text(str(text_value), chunk_strategy="sentence").get(
                "chunks", []
            )

    _normalize_media_urls(payload)

    return {
        "action_id": request.action_id,
        "content": payload,
        "cache_hit": cache_hit,
        "warning": payload.get("warning"),
        "error": payload.get("error"),
        "hyperfocus_override": False,
        "hyperfocus_composite": composite,
        "no_content": False,
    }
