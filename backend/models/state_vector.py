from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


class StateVector(BaseModel):
    session_id: str = Field(min_length=1)
    dwell: float = Field(default=0.0, ge=0.0, le=1.0)
    jitter: float = Field(default=0.0, ge=0.0, le=1.0)
    focus: float = Field(default=0.0, ge=0.0, le=1.0)
    stall: float = Field(default=0.0, ge=0.0, le=1.0)
    pref_delta: float = Field(default=0.0, ge=0.0, le=1.0)
    timestamp: str | None = Field(default=None)
    event_type: str | None = Field(default=None)
    lesson_metadata: dict[str, Any] | None = Field(default=None)
    duration_ms: int | None = Field(default=None)

    @model_validator(mode="before")
    @classmethod
    def accept_observer_vector_shape(cls, data: Any) -> Any:
        if not isinstance(data, dict) or "state_vector" not in data:
            return data

        vector = data.get("state_vector")
        if not isinstance(vector, list) or len(vector) != 5:
            return data

        mapped = dict(data)
        mapped["dwell"] = vector[0]
        mapped["jitter"] = vector[1]
        mapped["focus"] = vector[2]
        mapped["stall"] = vector[3]
        mapped["pref_delta"] = vector[4]
        return mapped

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("session_id cannot be blank")
        return value

    def as_list(self) -> list[float]:
        return [self.dwell, self.jitter, self.focus, self.stall, self.pref_delta]


class TrajectoryWindow(BaseModel):
    session_id: str = Field(min_length=1)
    vectors: list[list[float]] = Field(default_factory=list, max_length=3)
