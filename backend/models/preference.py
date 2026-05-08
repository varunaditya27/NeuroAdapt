from pydantic import BaseModel, Field
from typing import List, Optional


class PreferenceEntry(BaseModel):
    """Single preference log entry."""
    id: int
    session_id: str
    chosen_format: str
    pref_delta: Optional[float] = None
    created_at: str


class PreferenceHistoryResponse(BaseModel):
    """Response model for preference history."""
    session_id: str
    preferences: List[PreferenceEntry]
    count: int = Field(description="Total number of preferences returned")
