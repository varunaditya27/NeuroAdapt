"""Generation and prefetch API routes."""

from __future__ import annotations

import time
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, Response

from models.request_schemas import GenerateRequest, PrefetchRequest
from models.response_schemas import ContentPayload, GenerateResponse
from orchestration.action_router import get_prefetch_status, route_and_generate, start_prefetch

router = APIRouter()


def _record_generate_metrics(
    action_id: int,
    status: str,
    generation_time_ms: int,
    cache_hit: bool,
    fallback_stage: str | None = None,
    hyperfocus_override: bool = False,
    learner_level: str | None = None,
    fk_result: str | None = None,
) -> None:
    """Best-effort Prometheus recording, kept local to avoid hard import coupling."""
    try:
        from main import (  # type: ignore
            CACHE_HITS,
            CACHE_MISSES,
            FALLBACK_EVENTS,
            FK_VERIFICATION_RESULTS,
            HYPERFOCUS_OVERRIDES,
            PROMETHEUS_AVAILABLE,
            REQUEST_COUNT,
            REQUEST_LATENCY,
            TIMEOUT_EVENTS,
        )
    except Exception:
        return

    if not PROMETHEUS_AVAILABLE:
        return

    action = str(action_id)
    REQUEST_COUNT.labels(action_id=action, status=status).inc()
    REQUEST_LATENCY.labels(action_id=action).observe(max(0.0, generation_time_ms / 1000.0))

    if cache_hit:
        CACHE_HITS.labels(action_id=action).inc()
    else:
        CACHE_MISSES.labels(action_id=action).inc()

    if fallback_stage:
        stage = str(fallback_stage)
        FALLBACK_EVENTS.labels(action_id=action, stage=stage).inc()
        if "timeout" in stage:
            TIMEOUT_EVENTS.labels(action_id=action, stage=stage).inc()

    if hyperfocus_override:
        HYPERFOCUS_OVERRIDES.labels(reason="hyperfocus_gate").inc()

    if fk_result and learner_level:
        FK_VERIFICATION_RESULTS.labels(target_level=str(learner_level), result=str(fk_result)).inc()


@router.post(
    "/generate",
    response_model=GenerateResponse,
    responses={204: {"description": "Hold-course (no content due to action_id=0 or hyperfocus protection)"}},
)
async def generate_content(request: GenerateRequest):
    """Main generation endpoint used by backend/orchestrator."""
    start = time.perf_counter()

    try:
        routed = route_and_generate(request)
    except Exception as exc:
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        _record_generate_metrics(
            action_id=int(request.action_id),
            status="error",
            generation_time_ms=elapsed_ms,
            cache_hit=False,
        )
        raise HTTPException(status_code=500, detail=f"Generation routing failed: {exc}") from exc

    if routed.get("no_content"):
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        _record_generate_metrics(
            action_id=int(routed.get("action_id", request.action_id)),
            status="no_content",
            generation_time_ms=elapsed_ms,
            cache_hit=False,
            hyperfocus_override=bool(routed.get("hyperfocus_override", False)),
        )
        return Response(status_code=204)

    generation_time_ms = int((time.perf_counter() - start) * 1000)
    payload = routed.get("content", {})
    learner_level = str(getattr(request.learner_level, "value", request.learner_level))

    fk_result: str | None = None
    if int(routed.get("action_id", request.action_id)) == 2:
        target_by_level = {"grade5": 6.0, "grade8": 9.0, "university": 13.0}
        target = target_by_level.get(learner_level, 9.0)
        fk_grade = payload.get("fk_grade")
        if isinstance(fk_grade, (int, float)):
            fk_result = "met" if float(fk_grade) <= target else "missed"
        else:
            fk_result = "unknown"

    response = GenerateResponse(
        action_id=int(routed.get("action_id", request.action_id)),
        content=ContentPayload(**payload),
        generation_time_ms=generation_time_ms,
        cache_hit=bool(routed.get("cache_hit", False)),
        hyperfocus_override=bool(routed.get("hyperfocus_override", False)),
        error=routed.get("error"),
        warning=routed.get("warning"),
        timestamp=datetime.utcnow().isoformat() + "Z",
        session_id=str(request.session_id),
        request_id=request.request_id or f"req_{int(time.time() * 1000)}",
    )

    _record_generate_metrics(
        action_id=response.action_id,
        status="success",
        generation_time_ms=generation_time_ms,
        cache_hit=response.cache_hit,
        fallback_stage=payload.get("fallback_stage"),
        learner_level=learner_level,
        fk_result=fk_result,
    )

    return response


@router.post("/prefetch", status_code=202)
async def prefetch_content(request: PrefetchRequest):
    """Queue speculative generation tasks for top candidate actions."""
    return start_prefetch(request)


@router.get("/prefetch/status")
async def prefetch_status(
    action_id: int = Query(..., ge=0, le=5),
    session_id: str = Query(..., min_length=1),
    slide_content: str = Query(..., min_length=1),
    content_type: str | None = Query(default=None),
):
    """Check whether a prefetch candidate is ready."""
    return get_prefetch_status(
        action_id=action_id,
        session_id=session_id,
        slide_content=slide_content,
        content_type=content_type,
    )
