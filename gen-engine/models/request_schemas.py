"""Request schemas for Gen Engine API contracts."""

from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class LearnerLevel(str, Enum):
    """Enumeration of supported learner reading levels."""

    GRADE5 = "grade5"
    GRADE8 = "grade8"
    UNIVERSITY = "university"


class StateVector(BaseModel):
    """Internal hyperfocus compatibility vector with safe defaults."""

    cognitive_load: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Current cognitive load estimate (0.0=low, 1.0=overloaded)",
    )
    regression_count: int = Field(
        default=0,
        ge=0,
        le=100,
        description="Number of regressions in current session",
    )
    hyperfocus_composite: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Optional pre-computed hyperfocus composite score",
    )
    eye_gaze_stability: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Eye gaze stability measure (0.0=unstable, 1.0=very stable)",
    )
    attention_switching: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Rate of attention switching (0.0=stable, 1.0=highly switching)",
    )
    time_on_task: int = Field(default=0, ge=0, description="Seconds spent on current task")
    engagement_level: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Current engagement level estimate"
    )
    micro_pause_ratio: float = Field(
        default=0.1, ge=0.0, le=1.0, description="Ratio of micro-pauses to total time"
    )
    idle_time_bonus: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Bonus for sustained idle periods"
    )
    idle_time: float = Field(
        default=0.0, ge=0.0, description="Idle time in seconds over recent observation window"
    )
    keystroke_cv: float = Field(
        default=1.0, ge=0.0, description="Coefficient of variation for keystroke cadence"
    )
    gaze_dispersion: float = Field(
        default=1.0,
        ge=0.0,
        description="Normalized gaze dispersion (lower means tighter fixation cluster)",
    )
    scroll_velocity: float = Field(
        default=0.0, description="Signed scroll velocity for recent observation window"
    )
    session_duration: float = Field(
        default=0.0, ge=0.0, description="Elapsed session duration in seconds"
    )
    learner_avg_duration: float = Field(
        default=1.0, ge=0.0, description="Learner baseline average session duration in seconds"
    )
    keystroke_cadence: float = Field(
        default=0.0, ge=0.0, description="Raw keystroke cadence signal"
    )
    response_latency: float = Field(
        default=0.0, ge=0.0, description="Interaction response latency in seconds"
    )
    preference_delta: float = Field(
        default=0.0, description="Preference delta signal from feedback loop"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "cognitive_load": 0.7,
                "regression_count": 3,
                "hyperfocus_composite": 0.85,
                "eye_gaze_stability": 0.8,
                "attention_switching": 0.2,
                "time_on_task": 450,
                "engagement_level": 0.9,
                "micro_pause_ratio": 0.05,
                "idle_time_bonus": 0.1,
            }
        }
    )


class GenerateRequest(BaseModel):
    """Workflow-defined request for POST /api/generate."""

    action_id: int = Field(
        ...,
        ge=0,
        le=5,
        description="Action to perform (0=hold, 1=nudge, 2=simplify, 3=video, 4=game, 5=break)",
    )
    slide_content: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="Content to transform (text, concept description, etc.)",
    )
    learner_level: LearnerLevel = Field(..., description="Target reading/complexity level")

    @field_validator("action_id")
    @classmethod
    def validate_action_id(cls, v: int) -> int:
        """Ensure action_id is within valid range."""
        if not (0 <= v <= 5):
            raise ValueError(f"Action ID must be between 0 and 5, got {v}")
        return v

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "action_id": 2,
                "slide_content": "Photosynthesis is the biochemical process by which autotrophic organisms convert light energy into chemical energy stored in glucose molecules.",
                "learner_level": "grade8",
            }
        }
    )


class PrefetchRequest(BaseModel):
    """
    Request model for async prefetch endpoint.

    Used to pre-generate content for likely next actions.
    """

    session_id: UUID = Field(..., description="Session to prefetch for")
    top_actions: list[int] = Field(
        ...,
        min_length=1,
        max_length=3,
        description="Action IDs to prefetch (ordered by Q-value)",
    )
    slide_content: str = Field(
        ..., min_length=1, max_length=5000, description="Current slide content for prefetch context"
    )
    learner_level: LearnerLevel = Field(
        default=LearnerLevel.GRADE8, description="Learner's current level"
    )

    @field_validator("top_actions")
    @classmethod
    def validate_top_actions(cls, v: list[int]) -> list[int]:
        """Ensure all action IDs are valid."""
        for action_id in v:
            if not (0 <= action_id <= 5):
                raise ValueError(f"All action IDs must be between 0 and 5, got {action_id}")
        return v

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "session_id": "550e8400-e29b-41d4-a716-446655440000",
                "top_actions": [3, 4, 2],
                "slide_content": "Mitochondria are the powerhouse of the cell...",
                "learner_level": "grade8",
            }
        },
    )
