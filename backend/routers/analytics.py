from __future__ import annotations

"""Analytics API router.

All endpoints resolve user_id server-side via auth_resolver.get_current_user_id().
No user_id query parameter is accepted.
"""

"""Analytics API router."""



import json
import logging

from fastapi import APIRouter, Depends, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import Response

from backend.db import get_db
from backend.services.analytics_service import (
    get_modalities,
    get_overload,
    get_stability,
    get_user_summary,
)
from backend.services.auth_resolver import get_current_user_id
from backend.services.report_service import generate_pdf_report

router = APIRouter(prefix="/api/analytics", tags=["analytics"])
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Placeholder data — shown when no real data exists yet
# ---------------------------------------------------------------------------

_PLACEHOLDER_USER_SUMMARY = {
    "name": "Learner",
    "member_since": "June 2026",
    "total_sessions": 0,
    "current_streak": 0,
    "_placeholder": True,
}

_PLACEHOLDER_STABILITY = {
    "current_score": 72.4,
    "daily":   {"mean": 72.4, "delta": None,  "sufficient_data": True},
    "weekly":  {"mean": 69.1, "delta": +3.3,  "sufficient_data": True},
    "monthly": {"mean": 65.8, "delta": +6.6,  "sufficient_data": True},
    "_placeholder": True,
}

_PLACEHOLDER_OVERLOAD = {
    "spikes_this_week": 2,
    "spikes_last_week": 5,
    "weekly_delta": -3,
    "avg_spikes_per_session": 0.4,
    "sessions_with_zero_spikes": 3,
    "_placeholder": True,
}

_PLACEHOLDER_MODALITIES = {
    "total_events": 0,
    "modalities": {
        "standard":       {"count": 8,  "share": 0.32},
        "simplified_text":{"count": 7,  "share": 0.28},
        "quiz":           {"count": 5,  "share": 0.20},
        "video":          {"count": 3,  "share": 0.12},
        "sensory_break":  {"count": 2,  "share": 0.08},
        "audio":          {"count": 0,  "share": 0.00},
    },
    "no_data": False,
    "_placeholder": True,
}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/user-summary")
async def user_summary(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    user_id = get_current_user_id(request)
    result = await get_user_summary(db, user_id)
    if result.get("total_sessions", 0) == 0:
        return _PLACEHOLDER_USER_SUMMARY
    return result


@router.get("/stability")
async def stability(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    user_id = get_current_user_id(request)
    result = await get_stability(db, user_id)
    if result.get("current_score") is None:
        return _PLACEHOLDER_STABILITY
    return result


@router.get("/overload")
async def overload(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    user_id = get_current_user_id(request)
    result = await get_overload(db, user_id)
    # Switch to real data once there are sessions with snapshots
    if result.get("spikes_this_week") == 0 and result.get("sessions_with_zero_spikes") == 0:
        return _PLACEHOLDER_OVERLOAD
    return result


@router.get("/modalities")
async def modalities(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    user_id = get_current_user_id(request)
    result = await get_modalities(db, user_id)
    if result.get("no_data"):
        return _PLACEHOLDER_MODALITIES
    return result


@router.post("/modality-event", status_code=201)
async def modality_event(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    user_id = get_current_user_id(request)
    body = await request.json()
    modality = body.get("modality", "standard")
    source = body.get("source", "selection")
    payload = json.dumps({"modality": modality, "source": source})
    await db.execute(
        text("""
            INSERT INTO session_events (user_id, event_type, payload)
            VALUES (:user_id, 'modality_preference', :payload)
        """),
        {"user_id": user_id, "payload": payload},
    )
    await db.commit()
    logger.info("Modality event recorded: user=%s modality=%s source=%s", user_id, modality, source)
    return {"status": "created"}


@router.get("/report/pdf")
async def report_pdf(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Response:
    user_id = get_current_user_id(request)
    pdf_bytes = await generate_pdf_report(db, user_id)
    from datetime import datetime, timezone
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="neuroadapt_report_{date_str}.pdf"'},
    )