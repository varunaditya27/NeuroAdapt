"""
Response Schemas — Pydantic Models for Output Serialization

================================================================================
PURPOSE:
    Define and validate outgoing response structure to Frontend.
    Ensure all fields are serializable, correct types, valid values.
    Auto-generate OpenAPI documentation.

DEPENDENCIES:
    - pydantic==2.13.2 : Data validation & serialization
    - typing : Type hints
    - datetime : Timestamps

RESPONSE MODELS:
    1. GenerateResponse : Main POST /api/generate output
    2. ContentPayload : Nested content by action_id
    3. ErrorResponse : Error case response
    4. HealthResponse : GET /health response

================================================================================
"""

from datetime import datetime
from typing import Optional, Dict, List

from pydantic import BaseModel, Field, field_validator, ConfigDict


class ChunkMetadata(BaseModel):
    """Metadata for text chunks in progressive reveal."""

    text: str = Field(..., description="The chunk text content")
    readability_grade: float = Field(..., ge=0.0, le=20.0, description="Flesch-Kincaid grade level")
    word_count: int = Field(..., ge=1, description="Number of words in chunk")


class Question(BaseModel):
    """Quiz question structure."""

    id: int = Field(..., ge=0, description="Question identifier")
    text: str = Field(..., description="Question text")
    options: List[str] = Field(..., min_length=4, max_length=4, description="Four answer options")
    correct_index: int = Field(..., ge=0, le=3, description="Index of correct answer (0-3)")
    difficulty: str = Field(..., description="Difficulty level (easy/medium/hard)")


class WordTimestamp(BaseModel):
    """Word-level timestamp for audio synchronization."""

    word: str = Field(..., description="The spoken word")
    start_ms: int = Field(..., ge=0, description="Start time in milliseconds")
    end_ms: int = Field(..., ge=0, description="End time in milliseconds")


class Analogy(BaseModel):
    """Analogy structure for escape hatch."""

    id: int = Field(..., ge=0, description="Analogy identifier")
    title: str = Field(..., description="Short title for the analogy")
    source_domain: str = Field(..., description="Domain (sports/nature/tech/everyday)")
    explanation: str = Field(..., description="How the analogy maps to the concept")
    example: str = Field(..., description="Concrete example using the analogy")


class CSSVariables(BaseModel):
    """Typography and styling CSS variables."""

    font_size_base: Optional[str] = Field(None, alias="--font-size-base")
    font_weight_body: Optional[str] = Field(None, alias="--font-weight-body")
    line_height: Optional[str] = Field(None, alias="--line-height")
    letter_spacing: Optional[str] = Field(None, alias="--letter-spacing")
    paragraph_margin: Optional[str] = Field(None, alias="--paragraph-margin")
    color_contrast: Optional[str] = Field(None, alias="--color-contrast")
    animation_duration: Optional[str] = Field(None, alias="--animation-duration")

    model_config = ConfigDict(populate_by_name=True)


class ContentPayload(BaseModel):
    """Union of all possible content payloads based on action_id."""

    # Text simplification (action_id=2)
    simplified_text: Optional[str] = Field(None, description="FK-verified simplified text")
    fk_grade: Optional[float] = Field(
        None, ge=0.0, le=20.0, description="Flesch-Kincaid grade of output"
    )
    original_fk: Optional[float] = Field(None, ge=0.0, le=20.0, description="Original FK grade")
    chunks: Optional[List[ChunkMetadata]] = Field(None, description="Progressive reveal chunks")

    # Quiz generation (action_id=4)
    quiz_json: Optional[List[Question]] = Field(None, description="Generated quiz questions")
    mastery_level: Optional[str] = Field(None, description="Learner's mastery tier")
    estimated_time_seconds: Optional[int] = Field(
        None, ge=0, description="Estimated quiz completion time"
    )

    # Analogy generation (action_id=2, escape hatch)
    analogies: Optional[List[Analogy]] = Field(
        None, description="Three analogies for concept explanation"
    )
    analogy_types: Optional[List[str]] = Field(
        None,
        description="Analogy domain labels aligned with each analogy entry",
    )

    # Visual generation (action_id=3)
    image_url: Optional[str] = Field(None, description="Generated image URL")
    video_url: Optional[str] = Field(None, description="Generated animation/video URL")
    avatar_video_url: Optional[str] = Field(None, description="Generated avatar video URL")
    duration_ms: Optional[int] = Field(None, ge=0, description="Video duration in milliseconds")
    render_logs: Optional[str] = Field(
        None, description="Render diagnostics output for animation generation"
    )
    writer_attempts: Optional[int] = Field(
        None, ge=0, description="Writer attempt count for Manim generation"
    )
    reviewer_attempts: Optional[int] = Field(
        None, ge=0, description="Reviewer attempt count for Manim generation"
    )
    generation_mode: Optional[str] = Field(
        None, description="Runtime generation mode (e.g., sd_generated, svg_fallback)"
    )
    fallback_stage: Optional[str] = Field(
        None, description="Fallback stage identifier when degradation occurs"
    )
    safety_prompt_applied: Optional[bool] = Field(
        None, description="Whether autism-safe prompt constraints were applied"
    )
    safety_verified: Optional[bool] = Field(
        None, description="Whether output passed explicit post-generation safety verification"
    )
    safety_verification_method: Optional[str] = Field(
        None, description="Safety verification method used"
    )

    # Audio generation (action_id=3)
    audio_url: Optional[str] = Field(None, description="Generated audio URL")
    word_timestamps: Optional[List[WordTimestamp]] = Field(
        None, description="Per-word timing for dyslexia support"
    )
    timestamp_confidence: Optional[str] = Field(
        None, description="Timestamp confidence label (high/heuristic)"
    )

    # Typography morphing (all actions)
    css_variables: Optional[CSSVariables] = Field(None, description="Typography CSS variables")

    # Sensory break (action_id=5)
    break_template: Optional[str] = Field(None, description="Pre-built break content")
    suggested_duration_seconds: Optional[int] = Field(
        None, ge=0, description="Suggested break duration"
    )

    # Common encouragement text
    encouragement_text: Optional[str] = Field(None, description="Motivational text")

    # Title for breaks
    title: Optional[str] = Field(None, description="Content title")


class GenerateResponse(BaseModel):
    """Main response model for successful generation."""

    action_id: int = Field(..., ge=0, le=5, description="Action that was performed")
    content: ContentPayload = Field(..., description="Generated content payload")
    generation_time_ms: int = Field(..., ge=0, description="Time taken to generate content")
    cache_hit: bool = Field(..., description="Whether content came from cache")
    hyperfocus_override: bool = Field(
        ..., description="Whether generation was bypassed due to hyperfocus protection"
    )
    error: Optional[str] = Field(None, description="Error message if fallback was applied")
    warning: Optional[str] = Field(None, description="Warning about degraded quality")
    timestamp: str = Field(..., description="Response timestamp (ISO 8601)")
    session_id: str = Field(..., description="Session identifier")
    request_id: str = Field(..., description="Unique request identifier for tracing")

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, v: str) -> str:
        """Ensure timestamp is valid ISO 8601."""
        try:
            datetime.fromisoformat(v.replace("Z", "+00:00"))
            return v
        except ValueError:
            raise ValueError(f"Invalid ISO 8601 timestamp: {v}")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "action_id": 2,
                "content": {
                    "simplified_text": "Photosynthesis is how plants make their own food. They use sunlight to create a sugar called glucose. This sugar gives them energy to grow.",
                    "fk_grade": 7.2,
                    "original_fk": 14.8,
                    "chunks": [
                        {
                            "text": "Photosynthesis is how plants make their own food.",
                            "readability_grade": 6.5,
                            "word_count": 8,
                        }
                    ],
                    "css_variables": {"--font-size-base": "16px", "--line-height": "1.6"},
                    "encouragement_text": "Great job working through this complex topic!",
                },
                "generation_time_ms": 1250,
                "cache_hit": False,
                "timestamp": "2026-04-18T14:30:00Z",
                "session_id": "550e8400-e29b-41d4-a716-446655440000",
                "request_id": "req_123456",
            }
        }
    )


class ErrorDetail(BaseModel):
    """Detailed error information."""

    type: str = Field(..., description="Error type (e.g., 'GenerationTimeout')")
    message: str = Field(..., description="Human-readable error message")
    action_id: Optional[int] = Field(None, ge=0, le=5, description="Action that failed")
    fallback_applied: bool = Field(..., description="Whether fallback was applied")
    fallback_strategy: Optional[str] = Field(None, description="What fallback was used")


class ErrorResponse(BaseModel):
    """Response model for generation errors."""

    error: ErrorDetail = Field(..., description="Detailed error information")
    generation_time_ms: int = Field(..., ge=0, description="Time spent before error")
    timestamp: str = Field(..., description="Error timestamp (ISO 8601)")
    request_id: str = Field(..., description="Request identifier for tracing")

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, v: str) -> str:
        """Ensure timestamp is valid ISO 8601."""
        try:
            datetime.fromisoformat(v.replace("Z", "+00:00"))
            return v
        except ValueError:
            raise ValueError(f"Invalid ISO 8601 timestamp: {v}")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "error": {
                    "type": "GenerationTimeout",
                    "message": "Animation generation exceeded 45s timeout",
                    "action_id": 3,
                    "fallback_applied": True,
                    "fallback_strategy": "static_image",
                },
                "generation_time_ms": 45000,
                "timestamp": "2026-04-18T14:30:45Z",
                "request_id": "req_123456",
            }
        }
    )


class ServiceHealth(BaseModel):
    """Per-service health details returned by /health."""

    status: str = Field(..., description="Service status (up/down)")
    error: Optional[str] = Field(None, description="Last check error message, if any")
    last_check: Optional[str] = Field(
        None, description="Last dependency probe timestamp (ISO 8601)"
    )
    checked_seconds_ago: Optional[float] = Field(
        None, ge=0.0, description="Seconds since last probe"
    )

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        valid_statuses = ["up", "down"]
        if v not in valid_statuses:
            raise ValueError(f"Service status must be one of {valid_statuses}, got {v}")
        return v


class CacheHealth(BaseModel):
    """Cache summary reported by /health."""

    entries: int = Field(..., ge=0, description="Current cache entry count")
    max_size: int = Field(..., ge=1, description="Configured maximum cache entry count")


class PromptHealth(BaseModel):
    """Prompt template loading summary reported by /health."""

    loaded: int = Field(..., ge=0, description="Loaded prompt template count")
    required: int = Field(..., ge=0, description="Required prompt template count")
    missing_required: List[str] = Field(
        default_factory=list, description="Missing required prompt template names"
    )


class HealthResponse(BaseModel):
    """Response model for health check endpoint."""

    status: str = Field(..., description="Overall health status")
    timestamp: str = Field(..., description="Health check timestamp")
    ollama_reachable: bool = Field(..., description="Whether Ollama is currently reachable")
    kokoro_reachable: bool = Field(..., description="Whether Kokoro TTS is currently reachable")
    disk_space_gb: float = Field(..., ge=0.0, description="Free disk space in GB")
    cache_size_mb: float = Field(..., ge=0.0, description="Generation cache footprint in MB")
    services: Dict[str, ServiceHealth] = Field(..., description="Per-service health details")
    cache: Optional[CacheHealth] = Field(None, description="In-memory cache summary")
    prompts: Optional[PromptHealth] = Field(None, description="Prompt template readiness summary")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        """Ensure status is valid."""
        valid_statuses = ["healthy", "degraded", "unhealthy"]
        if v not in valid_statuses:
            raise ValueError(f"Status must be one of {valid_statuses}, got {v}")
        return v

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, v: str) -> str:
        """Ensure timestamp is valid ISO 8601."""
        try:
            datetime.fromisoformat(v.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError(f"Invalid ISO 8601 timestamp: {v}") from exc
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "healthy",
                "timestamp": "2026-04-18T14:30:00Z",
                "ollama_reachable": True,
                "kokoro_reachable": True,
                "disk_space_gb": 45.2,
                "cache_size_mb": 1830,
                "services": {
                    "Ollama": {
                        "status": "up",
                        "error": None,
                        "last_check": "2026-04-18T14:29:59.000000",
                        "checked_seconds_ago": 1.0,
                    }
                },
                "cache": {"entries": 5, "max_size": 100},
                "prompts": {"loaded": 7, "required": 7, "missing_required": []},
            }
        }
    )
