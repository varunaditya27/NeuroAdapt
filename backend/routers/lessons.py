"""Router for lesson catalogue endpoints."""

from fastapi import APIRouter
from backend.models.lesson import LessonsListResponse
from backend.services.lesson_service import get_all_lessons

router = APIRouter(prefix="/api", tags=["lessons"])


@router.get("/lessons", response_model=LessonsListResponse)
async def get_lessons() -> LessonsListResponse:
    """Fetch dynamic lesson catalogue with all available subjects and topics."""
    result = await get_all_lessons()
    return LessonsListResponse(**result)
