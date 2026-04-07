from pydantic import BaseModel, Field, field_validator


class StateVector(BaseModel):
    session_id: str = Field(min_length=1)
    dwell: float = Field(ge=0.0, le=1.0)
    jitter: float = Field(ge=0.0, le=1.0)
    focus: float = Field(ge=0.0, le=1.0)
    stall: float = Field(ge=0.0, le=1.0)
    pref_delta: float = Field(ge=0.0, le=1.0)

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
