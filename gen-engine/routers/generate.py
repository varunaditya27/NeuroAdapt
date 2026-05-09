"""Generation API route."""

from __future__ import annotations

import logging
import time
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Response

from models.request_schemas import GenerateRequest
from models.response_schemas import ContentPayload, GenerateResponse
from orchestration.action_router import route_and_generate

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post(
    "/generate",
    response_model=GenerateResponse,
    responses={
        204: {"description": "Hold-course (no content due to action_id=0 or hyperfocus protection)"}
    },
)
async def generate_content(request: GenerateRequest) -> GenerateResponse | Response:
    """Main generation endpoint used by backend/orchestrator."""
    start = time.perf_counter()

    try:
        routed: dict[str, Any] = route_and_generate(request)
    except Exception:
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        logger.exception("Generation routing failed")
        raise HTTPException(status_code=500, detail="Generation routing failed")

    if routed.get("no_content"):
        elapsed_ms = int((time.perf_counter() - start) * 1000)
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
    )

    return response
