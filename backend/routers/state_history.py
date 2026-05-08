"""Router for state history analytics endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from backend.db import get_db
from backend.models.state_history import StateHistoryResponse
from backend.services.state_history_service import get_state_history

router = APIRouter(prefix="/api", tags=["state_history"])


@router.get("/state-history/{session_id}", response_model=StateHistoryResponse)
async def get_state_history_endpoint(
    session_id: str,
    limit: int = Query(100, ge=1, le=1000, description="Max number of records to return"),
    db: AsyncSession = Depends(get_db)
) -> StateHistoryResponse:
    """Retrieve state history snapshots for a session with configurable limit."""
    result = await get_state_history(db, session_id, limit)
    return StateHistoryResponse(**result)
