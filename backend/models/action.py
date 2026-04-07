from pydantic import BaseModel, Field


class ActionResponse(BaseModel):
    action_id: int = Field(ge=0)
    confidence: float = Field(ge=0.0, le=1.0)
    gated: bool
    action_name: str
