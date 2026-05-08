from pydantic import BaseModel, Field
from typing import List, Optional, Any


class StateSnapshot(BaseModel):
    """Single state snapshot entry."""
    id: int
    session_id: str
    state: Optional[Any] = None
    created_at: str


class StateHistoryResponse(BaseModel):
    """Response model for state history."""
    session_id: str
    states: List[StateSnapshot]
    count: int = Field(description="Total number of state snapshots returned")
    limit: Optional[int] = None
