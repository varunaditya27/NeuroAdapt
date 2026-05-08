"""Router for preference history endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from backend.db import get_db
from backend.models.preference import PreferenceHistoryResponse
from backend.services.preference_service import get_preference_history

router = APIRouter(prefix="/api", tags=["preferences"])


@router.get("/preferences/{session_id}", response_model=PreferenceHistoryResponse)
async def get_preferences(
    session_id: str,
    limit: int = Query(100, ge=1, le=1000, description="Max number of records to return"),
    db: AsyncSession = Depends(get_db)
) -> PreferenceHistoryResponse:
    """Retrieve preference history for a session with pagination support."""
    result = await get_preference_history(db, session_id, limit)
    return PreferenceHistoryResponse(**result)
