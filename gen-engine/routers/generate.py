"""
POST /api/generate — Main Content Generation Endpoint

================================================================================
PURPOSE:
    Receives generation requests from the Orchestrator.
    Delegates to action_router based on action_id.
    Returns generated content with metadata.

DEPENDENCIES:
    - fastapi : APIRouter, HTTPException
    - pydantic : BaseModel for request/response validation
    - models.request_schemas : GenerateRequest
    - models.response_schemas : GenerateResponse
    - orchestration.action_router : route_and_generate()
    - tenacity : Retry logic for LLM/service failures

EXTERNAL SERVICES:
    - All generators (text_simplify, image_gen, kokoro_tts, manim_gen, etc.)
    - orchestration modules (hyperfocus_gate, latency_budget, prefetch_manager)

REQUEST BODY (GenerateRequest):
    {
        "action_id": int (0-5),
        "slide_content": str,
        "learner_level": "grade5" | "grade8" | "university",
        "session_id": str (UUID),
        "confidence": float (0.0-1.0),
        "state_vector": {
            "cognitive_load": float,
            "regression_count": int,
            "hyperfocus_composite": float,
            ...
        }
    }

RESPONSE BODY (GenerateResponse):
    {
        "action_id": int,
        "content": {
            "simplified_text": str | null,
            "fk_grade": float | null,
            "audio_url": str | null,
            "video_url": str | null,
            "quiz_json": dict | null,
            "chunks": list | null,
            ...
        },
        "generation_time_ms": int,
        "cache_hit": bool,
        "error": str | null (if fallback occurred)
    }

KEY FUNCTIONS:
    - post /api/generate : Main handler
        1. Validate request (Pydantic)
        2. Check hyperfocus gate (pre-emption)
        3. Apply latency budget
        4. Route to action_router
        5. Return response or fallback

ERROR HANDLING:
    - 400 BadRequest : Invalid action_id or missing fields
    - 408 RequestTimeout : Generation exceeded latency budget
    - 422 UnprocessableEntity : Validation error
    - 500 InternalServerError : Unexpected generator failure
        - Always return graceful fallback with original content

METRICS:
    - Request count by action_id
    - Response time histogram
    - Cache hit ratio
    - Error rate by type

INTEGRATION:
    - Called by Backend (NeuroAdapt orchestrator)
    - Forwards responses to Frontend via ContentRenderer
    - Logs all requests to PostgreSQL session table
================================================================================
"""

from fastapi import APIRouter, HTTPException, Response
from pydantic import ValidationError
import time
import logging
from datetime import datetime
from uuid import uuid4

from models.request_schemas import GenerateRequest
from models.response_schemas import GenerateResponse, ContentPayload
from orchestration.action_router import route_and_generate

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/generate", response_model=GenerateResponse)
async def generate_content(request: GenerateRequest) -> GenerateResponse:
    """Main content generation endpoint routed through orchestration layer."""
    start_time = time.time()

    try:
        logger.info(
            "Received generation request: action_id=%s, session_id=%s",
            request.action_id,
            request.session_id,
        )

        routing_result = await route_and_generate(request)

        # Contract behavior: action_id=0 means hold course, no content payload.
        if routing_result.get("action_id") == 0:
            logger.info("Generation pre-empted/held for session=%s", request.session_id)
            return Response(status_code=204)

        content_payload = ContentPayload(**(routing_result.get("content") or {}))
        generation_time_ms = int((time.time() - start_time) * 1000)

        response = GenerateResponse(
            action_id=routing_result.get("action_id", request.action_id),
            content=content_payload,
            generation_time_ms=generation_time_ms,
            cache_hit=bool(routing_result.get("cache_hit", False)),
            error=routing_result.get("error"),
            warning=routing_result.get("warning"),
            timestamp=datetime.now().isoformat(),
            session_id=str(request.session_id),
            request_id=f"req_{uuid4()}",
        )

        logger.info(
            "Generation completed: action_id=%s in %sms",
            response.action_id,
            generation_time_ms,
        )
        return response

    except ValidationError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        # Return graceful fallback
        fallback_chunks = []
        try:
            from generators.chunk_renderer import chunk_text

            fallback_chunks = chunk_text(request.slide_content).get("chunks", [])
        except Exception:
            fallback_chunks = []

        return GenerateResponse(
            action_id=request.action_id,
            content=ContentPayload(
                simplified_text=request.slide_content,
                chunks=fallback_chunks,
            ),
            generation_time_ms=int((time.time() - start_time) * 1000),
            cache_hit=False,
            error=str(e),
            timestamp=datetime.now().isoformat(),
            session_id=str(request.session_id),
            request_id=f"req_{uuid4()}",
        )
