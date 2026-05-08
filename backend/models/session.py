from pydantic import BaseModel, Field


class SessionInit(BaseModel):
    """Request model for session initialization."""
    student_id: str = Field(min_length=1, description="Unique identifier for the learner")


class SessionResponse(BaseModel):
    """Response model for session initialization."""
    session_id: str = Field(description="Unique session identifier")
    student_id: str = Field(description="Student identifier")
    created_at: str = Field(description="ISO 8601 timestamp of session creation")
