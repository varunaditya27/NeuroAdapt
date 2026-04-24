"""Action routing and generation orchestration."""

from __future__ import annotations

import os
from typing import Any, Dict

from generators.analogy_engine import generate_analogies
from generators.chunk_renderer import chunk_text
from generators.image_gen import generate_image
from generators.kokoro_tts import generate_tts
from generators.liveportrait_avatar import generate_avatar_video
from generators.manim_gen import generate_manim_animation
from generators.quiz_injector import generate_quiz
from generators.text_simplify import simplify_text
from generators.typography_morpher import morph_typography
from models.request_schemas import GenerateRequest, PrefetchRequest
from orchestration.hyperfocus_gate import check_hyperfocus
from orchestration.latency_budget import fallback_for, get_timeout_seconds, run_with_timeout
from orchestration.prefetch_manager import prefetch_manager

_LAST_CSS_BY_SESSION: Dict[str, Dict[str, str]] = {}
_MAX_SESSION_CSS_ENTRIES = max(100, int(os.getenv("MAX_SESSION_CSS_ENTRIES", "5000")))

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
    markers = ["equation", "vector", "force", "algorithm", "physics", "math", "graph", "derivative"]
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


def _prune_css_session_cache() -> None:
    overflow = len(_LAST_CSS_BY_SESSION) - _MAX_SESSION_CSS_ENTRIES
    for _ in range(max(0, overflow)):
        _LAST_CSS_BY_SESSION.pop(next(iter(_LAST_CSS_BY_SESSION)), None)


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
                get_timeout_seconds("manim"),
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
                audio_res = generate_tts(slide_content, speed=0.85, session_id=session_id)
                return {**anim_res, **audio_res}

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


def _prefetch_generator(action_id: int, request_data: dict[str, Any]) -> dict[str, Any]:
    return _generate_payload_for_action(action_id, request_data)


prefetch_manager.set_generator(_prefetch_generator)


def route_and_generate(request: GenerateRequest) -> Dict[str, Any]:
    """Main request router called by API endpoint."""
    request_data = request.model_dump(mode="json")
    session_id = request.resolved_session_id()
    state_vector = request.resolved_state_vector().model_dump(mode="json", exclude_defaults=True)

    # Compatibility context (legacy advanced payloads still accepted via model extras).
    request_data["session_id"] = session_id
    request_data["state_vector"] = state_vector
    request_data["confidence"] = request.resolved_confidence()
    request_data["concept"] = request.resolved_concept()
    request_data["content_type"] = request.resolved_content_type()
    request_data["learner_id"] = request.resolved_learner_id()
    request_data["voice_profile"] = request.resolved_voice_profile()
    request_data["source_image"] = request.resolved_source_image()

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

    prefetch_wait_seconds = max(0.0, _get_env_float("PREFETCH_WAIT_SECONDS", 0.8))
    if request.action_id == 3:
        prefetch_wait_seconds = max(
            prefetch_wait_seconds,
            _get_env_float("PREFETCH_WAIT_SECONDS_ACTION3", 4.0),
        )
    elif request.action_id == 4:
        prefetch_wait_seconds = max(
            prefetch_wait_seconds,
            _get_env_float("PREFETCH_WAIT_SECONDS_ACTION4", 1.2),
        )

    cached, cache_hit = prefetch_manager.get_cached_or_wait(
        request.action_id,
        request_data,
        timeout=prefetch_wait_seconds,
    )
    if cache_hit and cached is not None:
        payload = dict(cached)
    else:
        payload = _generate_payload_for_action(request.action_id, request_data)
        cache_hit = bool(payload.get("cache_hit", False))

    # Ensure text actions always include chunks
    if request.action_id in {1, 2}:
        text_value = payload.get("simplified_text") or request.slide_content
        if not payload.get("chunks"):
            payload["chunks"] = chunk_text(str(text_value), chunk_strategy="sentence").get(
                "chunks", []
            )

    # Typography morph for all non-hold responses.
    prev_css = _LAST_CSS_BY_SESSION.get(session_id)
    css = morph_typography(state_vector, locked_css=prev_css)
    _LAST_CSS_BY_SESSION[session_id] = css
    _prune_css_session_cache()
    payload["css_variables"] = css

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


def start_prefetch(prefetch_request: PrefetchRequest) -> Dict[str, Any]:
    request_data = {
        "session_id": str(prefetch_request.session_id),
        "slide_content": prefetch_request.slide_content,
        "learner_level": prefetch_request.learner_level.value,
        "content_type": prefetch_request.content_type.value
        if prefetch_request.content_type
        else None,
        "concept": prefetch_request.concept,
    }
    queued = prefetch_manager.start_prefetch(prefetch_request.top_actions, request_data)

    estimated_ms = 0
    for action_id in prefetch_request.top_actions[:2]:
        if action_id == 3:
            estimated_ms = max(estimated_ms, int(get_timeout_seconds("manim") * 1000))
        elif action_id == 2:
            estimated_ms = max(estimated_ms, int(get_timeout_seconds("text_simplify") * 1000))
        elif action_id == 4:
            estimated_ms = max(estimated_ms, int(get_timeout_seconds("quiz") * 1000))

    return {
        "prefetch_started": queued > 0,
        "tasks_queued": queued,
        "estimated_completion_ms": estimated_ms or 2000,
    }


def get_prefetch_status(
    action_id: int,
    session_id: str,
    slide_content: str,
    content_type: str | None = None,
    learner_level: str | None = None,
) -> Dict[str, Any]:
    request_data = {
        "session_id": session_id,
        "slide_content": slide_content,
        "content_type": content_type,
        "learner_level": learner_level,
    }
    status = prefetch_manager.get_status(action_id, request_data)
    return {
        **status,
        "action_id": action_id,
        "session_id": session_id,
    }
