from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db import get_db
from backend.models.state_vector import StateVector
from backend.services.state_store import persist_state, set_cached_state

router = APIRouter(prefix="/api", tags=["state"])


@router.post("/state")
async def post_state(
    payload: StateVector,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str | bool]:
    vector = payload.as_list()
    set_cached_state(payload.session_id, vector)

    persisted = False
    try:
        await persist_state(db, payload.session_id, vector)
        await db.commit()
        persisted = True
    except Exception:
        await db.rollback()

    return {"status": "ok", "session_id": payload.session_id, "persisted": persisted}
