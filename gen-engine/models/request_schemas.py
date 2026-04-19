"""
Request Schemas — Pydantic Models for Input Validation

================================================================================
PURPOSE:
    Define and validate incoming request structure from Backend/Orchestrator.
    Ensure all required fields present, correct types, valid ranges.
    Auto-generate OpenAPI documentation.

DEPENDENCIES:
    - pydantic==2.13.2 : Data validation & serialization
    - typing : Type hints

INPUT MODELS:
    1. GenerateRequest : Main POST /api/generate input
    2. StateVector : Nested learner state information
    3. PrefetchRequest : Async prefetch request (optional)

GENERATE REQUEST STRUCTURE:
    {
        "action_id": int (0-5),
        "slide_content": str (1-5000 chars),
        "learner_level": "grade5" | "grade8" | "university",
        "session_id": str (UUID format),
        "confidence": float (0.0-1.0),
        "state_vector": {
            "cognitive_load": float (0.0-1.0),
            "regression_count": int (0-100),
            "hyperfocus_composite": float (0.0-1.0),
            "eye_gaze_stability": float (0.0-1.0),
            "attention_switching": float (0.0-1.0),
            "time_on_task": int (seconds),
            "engagement_level": float (0.0-1.0),
            ... (other telemetry fields)
        },
        "learner_id": str (UUID, optional),
        "concept": str (optional, explicit override),
        "content_type": "text" | "image" | "animation" | "audio" | "avatar" (optional)
    }

VALIDATION RULES:
    - action_id: Required, must be 0-5
    - slide_content: Required, non-empty, max 5000 chars
    - learner_level: Required, must match enum
    - session_id: Required, must be valid UUID
    - confidence: Required, must be 0.0-1.0
    - state_vector: Required, must have all substates (or use defaults)
    - learner_id: Optional, if provided must be valid UUID
    - concept: Optional, if provided must be non-empty

STATE VECTOR SUBSTATES:
    - cognitive_load: Required, 0.0-1.0
    - regression_count: Required, 0-100
    - hyperfocus_composite: Required, 0.0-1.0
    - eye_gaze_stability: Optional, defaults to 0.5
    - attention_switching: Optional, defaults to 0.5
    - time_on_task: Optional, defaults to 0
    - engagement_level: Optional, defaults to 0.5
    (other optional fields with sensible defaults)

VALIDATION ERRORS:
    If validation fails:
        → Return 422 Unprocessable Entity
        → Include detailed error message
        → Example:
            {
                "detail": [
                    {
                        "type": "value_error",
                        "loc": ["body", "action_id"],
                        "msg": "Action ID must be between 0 and 5",
                        "input": "invalid"
                    }
                ]
            }

KEY CLASSES:
    - GenerateRequest : Main input
    - StateVector : Nested state
    - LearnerProfile : Optional learner metadata
    - RequestMetadata : Optional request tracking

ERROR HANDLING:
    - Invalid UUID: Raise ValidationError
    - Out-of-range float: Clamp or reject
    - Missing required field: Reject
    - Type mismatch: Coerce or reject

INTEGRATION:
    - Used by routers/generate.py to validate incoming requests
    - FastAPI auto-validates using Pydantic
    - OpenAPI docs auto-generated from schemas
    - Request logging includes validated fields

RELATED:
    - response_schemas.py : Output validation

================================================================================
"""

from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import AliasChoices, BaseModel, Field, field_validator, ConfigDict


class LearnerLevel(str, Enum):
    """Enumeration of supported learner reading levels."""

    GRADE5 = "grade5"
    GRADE8 = "grade8"
    UNIVERSITY = "university"


class ContentType(str, Enum):
    """Enumeration of content types for generation."""

    TEXT = "text"
    IMAGE = "image"
    ANIMATION = "animation"
    AUDIO = "audio"
    AVATAR = "avatar"
    STEM = "stem"
    GENERAL = "general"
    VISUAL = "visual"
    VIDEO = "video"


class StateVector(BaseModel):
    """
    Nested model containing real-time learner state information.

    All values are normalized 0.0-1.0 except where noted.
    Used by hyperfocus gate and orchestration logic.
    """

    # Core required fields from orchestrator.
    cognitive_load: float = Field(
        ..., ge=0.0, le=1.0, description="Current cognitive load estimate (0.0=low, 1.0=overloaded)"
    )
    regression_count: int = Field(
        ..., ge=0, le=100, description="Number of regressions in current session"
    )
    hyperfocus_composite: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Optional pre-computed hyperfocus composite score (compatibility path)",
    )

    # Optional fields with defaults
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

    # Compatibility fields used by documented hyperfocus detector inputs.
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

    # Additional observer-compatible telemetry fields (optional).
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


class LearnerProfile(BaseModel):
    """Optional learner metadata for personalization."""

    learner_id: Optional[UUID] = Field(None, description="Unique learner identifier")
    preferred_voice: Optional[str] = Field(None, description="Preferred TTS voice identifier")
    dyslexia_profile: Optional[bool] = Field(
        None, description="Whether learner has dyslexia accommodations"
    )
    autism_profile: Optional[bool] = Field(
        None, description="Whether learner has autism accommodations"
    )
    adhd_profile: Optional[bool] = Field(
        None, description="Whether learner has ADHD accommodations"
    )


class GenerateRequest(BaseModel):
    """
    Main request model for POST /api/generate endpoint.

    Validates all incoming generation requests from the orchestrator.
    """

    # Required core fields
    action_id: int = Field(
        ...,
        ge=0,
        le=5,
        description="Action to perform (0=hold, 1=chunk, 2=simplify, 3=visual, 4=quiz, 5=break)",
    )
    slide_content: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="Content to transform (text, concept description, etc.)",
    )
    learner_level: LearnerLevel = Field(..., description="Target reading/complexity level")
    session_id: UUID = Field(..., description="Unique session identifier")
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Orchestrator confidence in this action (0.0-1.0)"
    )
    state_vector: StateVector = Field(..., description="Real-time learner state information")

    # Optional fields
    learner_profile: Optional[LearnerProfile] = Field(
        None, description="Learner-specific preferences and accommodations"
    )
    concept: Optional[str] = Field(
        None,
        min_length=1,
        max_length=200,
        validation_alias=AliasChoices("concept", "concept_id"),
        description="Explicit concept override (if different from slide_content)",
    )
    content_type: Optional[ContentType] = Field(
        None, description="Specific content type for action_id=3 (visual generation)"
    )
    request_id: Optional[str] = Field(None, description="Client-provided request ID for tracing")

    @field_validator("action_id")
    @classmethod
    def validate_action_id(cls, v: int) -> int:
        """Ensure action_id is within valid range."""
        if not (0 <= v <= 5):
            raise ValueError(f"Action ID must be between 0 and 5, got {v}")
        return v

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        """Ensure confidence is within valid range."""
        if not (0.0 <= v <= 1.0):
            raise ValueError(f"Confidence must be between 0.0 and 1.0, got {v}")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "action_id": 2,
                "slide_content": "Photosynthesis is the biochemical process by which autotrophic organisms convert light energy into chemical energy stored in glucose molecules.",
                "learner_level": "grade8",
                "session_id": "550e8400-e29b-41d4-a716-446655440000",
                "confidence": 0.85,
                "state_vector": {
                    "cognitive_load": 0.7,
                    "regression_count": 3,
                    "hyperfocus_composite": 0.85,
                    "eye_gaze_stability": 0.8,
                    "attention_switching": 0.2,
                    "time_on_task": 450,
                    "engagement_level": 0.9,
                },
                "concept": "photosynthesis",
                "content_type": "text",
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
        validation_alias=AliasChoices("top_actions", "action_candidates"),
        description="Action IDs to prefetch (ordered by Q-value)",
    )
    slide_content: str = Field(
        ..., min_length=1, max_length=5000, description="Current slide content for prefetch context"
    )
    learner_level: LearnerLevel = Field(
        default=LearnerLevel.GRADE8, description="Learner's current level"
    )
    content_type: Optional[ContentType] = Field(
        None, description="Optional content type hint for action_id=3 prefetch"
    )
    concept: Optional[str] = Field(
        None,
        min_length=1,
        max_length=200,
        validation_alias=AliasChoices("concept", "concept_id"),
        description="Optional concept hint used by visual generators",
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
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "session_id": "550e8400-e29b-41d4-a716-446655440000",
                "action_candidates": [3, 4, 2],
                "slide_content": "Mitochondria are the powerhouse of the cell...",
                "learner_level": "grade8",
            }
        },
    )
