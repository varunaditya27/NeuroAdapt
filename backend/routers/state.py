import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db import get_db
from backend.models.state_vector import StateVector
from backend.services.state_store import persist_state, set_cached_state, persist_lesson_event

router = APIRouter(prefix="/api", tags=["state"])
logger = logging.getLogger(__name__)


@router.post("/state")
async def post_state(
    payload: StateVector,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str | bool | None]:
    vector = payload.as_list()
    set_cached_state(payload.session_id, vector)

    if payload.event_type == "lesson_completion":
        logger.info(
            "Lesson completed: session=%s subject=%s topic=%s duration=%dms",
            payload.session_id,
            payload.lesson_metadata.get("subject") if payload.lesson_metadata else "?",
            payload.lesson_metadata.get("topic") if payload.lesson_metadata else "?",
            payload.duration_ms or 0,
        )
        try:
            await persist_lesson_event(
                db, payload.session_id,
                payload.lesson_metadata or {},
                payload.duration_ms,
                vector,
            )
        except Exception:
            pass  # Best-effort; state_snapshots is the primary write

    persisted = False
    try:
        await persist_state(db, payload.session_id, vector)
        await db.commit()
        persisted = True
    except Exception:
        await db.rollback()

    return {
        "status": "ok",
        "session_id": payload.session_id,
        "persisted": persisted,
        "event_type": payload.event_type,
    }

