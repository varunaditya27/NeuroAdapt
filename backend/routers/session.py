"""Router for session management endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from backend.db import get_db
from backend.models.session import SessionInit, SessionResponse
from backend.services.session_manager import create_session

router = APIRouter(prefix="/api", tags=["session"])


@router.post("/session", response_model=SessionResponse)
async def post_session(payload: SessionInit, db: AsyncSession = Depends(get_db)) -> SessionResponse:
    """Initialize a new learning session for a student."""
    result = await create_session(db, payload.student_id)
    return SessionResponse(**result)
