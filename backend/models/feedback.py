from typing import Optional

from pydantic import BaseModel, Field, field_validator

from shared_config import ACTION_SPACE, STATE_VECTOR_DIM


class FeedbackPayload(BaseModel):
    session_id: str = Field(min_length=1)
    event: str = Field(min_length=1)
    chosen_format: Optional[str] = None
    current_state: list[float] = Field(min_length=STATE_VECTOR_DIM, max_length=STATE_VECTOR_DIM)
    action_taken: int = Field(ge=0, lt=ACTION_SPACE)

    @field_validator("current_state")
    @classmethod
    def validate_state_range(cls, value: list[float]) -> list[float]:
        for index, signal in enumerate(value):
            if not 0.0 <= signal <= 1.0:
                raise ValueError(f"current_state[{index}] must be in [0, 1]")
        return value


class FeedbackResponse(BaseModel):
    reward: float
    stored: bool
