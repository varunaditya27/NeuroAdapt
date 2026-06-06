"""Analytics API router.

All endpoints resolve user_id server-side via auth_resolver.get_current_user_id().
No user_id query parameter is accepted.
"""

from __future__ import annotations

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


@router.get("/user-summary")
async def user_summary(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return user identity strip fields."""
    user_id = get_current_user_id(request)
    return await get_user_summary(db, user_id)


@router.get("/stability")
async def stability(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return Cognitive Stability Score and trends."""
    user_id = get_current_user_id(request)
    return await get_stability(db, user_id)


@router.get("/overload")
async def overload(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return cognitive overload spike frequencies."""
    user_id = get_current_user_id(request)
    return await get_overload(db, user_id)


@router.get("/modalities")
async def modalities(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return modality preference shares."""
    user_id = get_current_user_id(request)
    return await get_modalities(db, user_id)


@router.post("/modality-event", status_code=201)
async def modality_event(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Record a modality preference event.

    Body: { "modality": "simplified_text"|"video_audio"|"quiz"|"sensory_break"|"standard",
            "source": "selection"|"acceptance"|"dismissal" }
    """
    user_id = get_current_user_id(request)
    body = await request.json()

    modality = body.get("modality", "standard")
    source = body.get("source", "selection")

    payload = json.dumps({"modality": modality, "source": source})

    await db.execute(
        text(
            """
            INSERT INTO session_events (user_id, event_type, payload)
            VALUES (:user_id, 'modality_preference', :payload)
            """
        ),
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
    """Generate and download a PDF analytics report."""
    user_id = get_current_user_id(request)
    pdf_bytes = await generate_pdf_report(db, user_id)
    from datetime import datetime, timezone

    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="neuroadapt_report_{date_str}.pdf"',
        },
    )