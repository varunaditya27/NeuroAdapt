"""
Action Router — Tier Classification & Dispatch Logic

================================================================================
PURPOSE:
    Routes incoming requests to appropriate generator(s) based on action_id.
    Classifies generators into Tier 1 (instant), Tier 2 (fast), Tier 3 (async).
    Applies latency budgets and fallback chains.

DEPENDENCIES:
    - generators.* : All generator modules
    - orchestration.latency_budget : Enforce timeouts
    - orchestration.hyperfocus_gate : Pre-emption check
    - orchestration.prefetch_manager : Async generation
    - pydantic : Request/response validation

INPUT:
    action_id: int (0-5)
    slide_content: str
    learner_level: "grade5" | "grade8" | "university"
    confidence: float (0.0-1.0)
    state_vector: dict
    session_id: str

ROUTING LOGIC:
    action_id = 0 (Hold Course)
        → No generation, return 204 No Content
        
    action_id = 2 (Text Simplification)
        → Tier 2: text_simplify.py
        → Fallback: Serve original text + warning
        
    action_id = 3 (Visual/Audio/Video)
        → Route by content_type parameter:
           - type="image" → Tier 3: image_gen.py
           - type="animation" → Tier 3: manim_gen.py
           - type="audio" → Tier 3: kokoro_tts.py
           - type="avatar" → Tier 3: liveportrait_avatar.py
        → Async pre-fetch manager
        → Fallback chains: animation→image, audio→text, avatar→audio
        
    action_id = 4 (Gamified Quiz)
        → Tier 2: quiz_injector.py
        → Fallback: Serve hardcoded quiz
        
    action_id = 5 (Sensory Break)
        → Tier 1: Return pre-built templates (no generation)
        → No fallback needed (instant)

TIER ARCHITECTURE:
    Tier 1 (Instant, <1s):
        - typography_morpher
        - chunk_renderer
        - action_id = 5 (templates)
        → Always served immediately
        
    Tier 2 (Fast, 2-5s):
        - text_simplify
        - quiz_injector
        - analogy_engine
        → Served with latency budget enforcement
        → Fallback to original/template
        
    Tier 3 (Async, 10-45s):
        - image_gen
        - manim_gen
        - kokoro_tts
        - liveportrait_avatar
        → Pre-fetched in background
        → Served from cache if ready

ALGORITHM:
    1. Validate request (Pydantic)
    2. Check hyperfocus gate:
        if hyperfocus_composite > 0.75:
            → Override action_id to 0 (hold course)
            → Return without generation
    3. Apply latency budget decorator
    4. Route by action_id:
        a. Call appropriate generator
        b. Call typography_morpher (all)
        c. Call chunk_renderer if text (all)
    5. Catch timeout → Apply fallback chain
    6. Catch error → Apply fallback chain
    7. Return response + metrics

FALLBACK CHAINS:
    action_id = 2 (Text Simplify):
        Success → Return simplified text
        Timeout → Serve original text + warning
        Error → Serve original text + warning
        
    action_id = 3 (Visual/Audio/Video):
        animation → Success: MP4 | Timeout/Error: static image
        image → Success: PNG | Timeout/Error: text only
        audio → Success: WAV | Timeout/Error: text only
        avatar → Success: MP4 | Timeout/Error: audio only
        
    action_id = 4 (Quiz):
        Success → Return MCQs
        Timeout → Return hardcoded quiz
        Error → Return hardcoded quiz

PRE-FETCH MANAGER INTEGRATION:
    - Tier 3 requests sent to prefetch_manager
    - Manager runs background tasks
    - Frontend polls /api/generate?action_id=X to check status
    - Cache hit served immediately on status check

KEY FUNCTIONS:
    - route_and_generate(request: GenerateRequest) → GenerateResponse
    - classify_tier(action_id) → str ("tier1" | "tier2" | "tier3")
    - apply_fallback(action_id, error_type) → dict
    - apply_all_generators(content, state_vector) → dict
    - check_action_valid(action_id) → bool

ERROR HANDLING:
    - Invalid action_id: Return 400 Bad Request
    - All fallbacks exhausted: Return original content + error
    - Unexpected exception: Log + return 500 + error message

METRICS:
    - Count by action_id
    - Latency histogram by tier
    - Fallback rate by action_id
    - Error rate by type

INTEGRATION:
    - Called by routers/generate.py
    - Routes to all generators
    - Returns final GenerateResponse

RELATED:
    - latency_budget : Enforces timeouts
    - hyperfocus_gate : Pre-emption override
    - prefetch_manager : Async generation
    - All generators : Actual content production

================================================================================
"""

# TODO: Define action_id routing logic
# TODO: Implement tier classification
# TODO: Implement routing by action_id
# TODO: Implement routing by content_type for action_id=3
# TODO: Implement hyperfocus gate check
# TODO: Implement fallback chains
# TODO: Call typography_morpher for all
# TODO: Call chunk_renderer for text responses
# TODO: Add latency budget decorator
# TODO: Add error handling
# TODO: Add metrics recording

from __future__ import annotations

from typing import Any, Dict, Optional

from generators.analogy_engine import generate_analogies
from generators.chunk_renderer import chunk_text
from generators.quiz_injector import generate_quiz
from generators.text_simplify import simplify_text
from generators.typography_morpher import morph_typography
from models.request_schemas import GenerateRequest
from orchestration.hyperfocus_gate import should_pre_empt
from orchestration.latency_budget import execute_with_timeout


def classify_tier(action_id: int, content_type: Optional[str] = None) -> str:
    if action_id in {0, 1, 5}:
        return "tier1"
    if action_id in {2, 4}:
        return "tier2"
    if action_id == 3:
        if content_type in {"animation", "image", "audio", "avatar"}:
            return "tier3"
        return "tier2"
    return "tier1"


def check_action_valid(action_id: int) -> bool:
    return action_id in {0, 1, 2, 3, 4, 5}


def _merge_messages(*messages: Optional[str]) -> Optional[str]:
    parts = [message.strip() for message in messages if message and message.strip()]
    if not parts:
        return None
    deduped = []
    for item in parts:
        if item not in deduped:
            deduped.append(item)
    return " | ".join(deduped)


def _state_dict(request: GenerateRequest) -> Dict[str, Any]:
    return request.state_vector.model_dump() if request.state_vector is not None else {}


def _base_content_with_css(request: GenerateRequest) -> Dict[str, Any]:
    css_variables = morph_typography(_state_dict(request))
    return {"css_variables": css_variables}


async def route_and_generate(request: GenerateRequest) -> Dict[str, Any]:
    """Route request to generators and return contract-shaped content payload data."""
    if not check_action_valid(request.action_id):
        raise ValueError(f"Invalid action_id: {request.action_id}")

    session_id = str(request.session_id)
    state = _state_dict(request)

    # Hyperfocus protective override: no intervention.
    if should_pre_empt(session_id=session_id, state_vector=state):
        return {
            "action_id": 0,
            "tier": "tier1",
            "content": None,
            "cache_hit": False,
            "warning": "Hyperfocus protection active; interventions paused.",
            "error": None,
            "generation_latency_ms": 0,
        }

    action_id = request.action_id
    content: Dict[str, Any] = _base_content_with_css(request)
    cache_hit = False
    error = None
    warning = None
    total_latency_ms = 0

    if action_id == 0:
        return {
            "action_id": 0,
            "tier": "tier1",
            "content": None,
            "cache_hit": False,
            "warning": None,
            "error": None,
            "generation_latency_ms": 0,
        }

    if action_id == 1:
        chunk_payload = chunk_text(request.slide_content, chunk_strategy="sentence")
        content.update(
            {
                "simplified_text": request.slide_content,
                "chunks": chunk_payload.get("chunks", []),
            }
        )
        warning = "Action 1 routed as lightweight nudge with chunked text payload."

    elif action_id == 2:
        fallback = {
            "simplified_text": request.slide_content,
            "fk_grade": None,
            "original_fk": None,
            "chunks": chunk_text(request.slide_content).get("chunks", []),
            "cache_hit": False,
            "warning": "Served original text fallback.",
        }
        simplify_result, simplify_error, simplify_warning, latency_ms = await execute_with_timeout(
            simplify_text,
            request.slide_content,
            action_id=2,
            timeout_seconds=None,
            fallback_value=fallback,
            target_level=request.learner_level.value,
            session_id=session_id,
        )
        total_latency_ms += latency_ms
        cache_hit = bool(simplify_result.get("cache_hit", False))
        content.update(
            {
                "simplified_text": simplify_result.get("simplified_text", request.slide_content),
                "fk_grade": simplify_result.get("fk_grade"),
                "original_fk": simplify_result.get("original_fk"),
                "chunks": simplify_result.get("chunks", chunk_text(request.slide_content).get("chunks", [])),
            }
        )
        error = _merge_messages(error, simplify_result.get("error"), simplify_error)
        warning = _merge_messages(warning, simplify_result.get("warning"), simplify_warning)

    elif action_id == 3:
        content_type = request.content_type.value
        chunk_payload = chunk_text(request.slide_content, chunk_strategy="hybrid")
        content.update(
            {
                "simplified_text": request.slide_content,
                "chunks": chunk_payload.get("chunks", []),
            }
        )

        if content_type == "audio":
            warning = "Audio generation path is not yet enabled; served text payload fallback."
        elif content_type == "image":
            warning = "Image generation path is not yet enabled; served text payload fallback."
        elif content_type == "animation":
            warning = "Animation generation path is not yet enabled; served text payload fallback."
        elif content_type == "avatar":
            warning = "Avatar generation path is not yet enabled; served text payload fallback."
        else:
            warning = "Content type not specified for action 3; served text payload fallback."

    elif action_id == 4:
        fallback_quiz = generate_quiz(
            concept=request.concept or "current concept",
            learner_id=None,
            slide_content=request.slide_content,
            session_id=session_id,
        )
        quiz_result, quiz_error, quiz_warning, latency_ms = await execute_with_timeout(
            generate_quiz,
            request.concept or "current concept",
            None,
            request.slide_content,
            action_id=4,
            timeout_seconds=None,
            fallback_value=fallback_quiz,
            session_id=session_id,
        )
        total_latency_ms += latency_ms

        # Optional companion analogies for conceptual escape hatch.
        analogy_result, analogy_error, analogy_warning, latency_ms = await execute_with_timeout(
            generate_analogies,
            request.concept or "current concept",
            request.slide_content,
            action_id=4,
            timeout_seconds=3,
            fallback_value={"analogies": []},
            learner_level=request.learner_level.value,
            session_id=session_id,
        )
        total_latency_ms += latency_ms

        content.update(
            {
                "quiz_json": quiz_result.get("quiz_json") or quiz_result.get("questions", []),
                "mastery_level": quiz_result.get("mastery_level"),
                "estimated_time_seconds": quiz_result.get("estimated_time_seconds"),
                "encouragement_text": quiz_result.get("encouragement_text"),
                "analogy_json": analogy_result.get("analogies", []),
            }
        )
        cache_hit = bool(quiz_result.get("cache_hit", False)) and bool(analogy_result.get("cache_hit", False))
        error = _merge_messages(error, quiz_result.get("error"), quiz_error, analogy_result.get("error"), analogy_error)
        warning = _merge_messages(
            warning,
            quiz_result.get("warning"),
            quiz_warning,
            analogy_result.get("warning"),
            analogy_warning,
        )

    elif action_id == 5:
        content.update(
            {
                "title": "Sensory Break",
                "break_template": "Pause for a short reset: look away from the screen, breathe slowly, and stretch your shoulders.",
                "suggested_duration_seconds": 180,
                "encouragement_text": "Great effort so far. A brief reset can sharpen focus for the next segment.",
            }
        )

    tier = classify_tier(action_id, request.content_type.value)
    return {
        "action_id": action_id,
        "tier": tier,
        "content": content,
        "cache_hit": cache_hit,
        "warning": warning,
        "error": error,
        "generation_latency_ms": total_latency_ms,
    }
