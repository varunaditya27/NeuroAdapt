"""Response schemas for Gen Engine API contracts."""

from datetime import datetime
from typing import Dict, List, Optional

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


class ContentPayload(BaseModel):
    """Workflow-relevant output payload across action paths."""

    # Text simplification (action_id=2)
    simplified_text: Optional[str] = Field(None, description="FK-verified simplified text")
    fk_grade: Optional[float] = Field(
        None, ge=0.0, le=20.0, description="Flesch-Kincaid grade of output"
    )
    original_fk: Optional[float] = Field(None, ge=0.0, le=20.0, description="Original FK grade")
    chunks: Optional[List[ChunkMetadata]] = Field(None, description="Progressive reveal chunks")

    quiz_json: Optional[List[Question]] = Field(None, description="Generated quiz questions")

    image_url: Optional[str] = Field(None, description="Generated image URL")
    video_url: Optional[str] = Field(None, description="Generated animation/video URL")
    audio_url: Optional[str] = Field(None, description="Generated audio URL")
    word_timestamps: Optional[List[WordTimestamp]] = Field(
        None, description="Per-word timing for dyslexia support"
    )

    break_template: Optional[str] = Field(None, description="Pre-built break content")
    suggested_duration_seconds: Optional[int] = Field(
        None, ge=0, description="Suggested break duration"
    )

    encouragement_text: Optional[str] = Field(None, description="Motivational text")
    title: Optional[str] = Field(None, description="Content title")
    warning: Optional[str] = Field(None, description="Fallback or degradation warning")
    fallback_stage: Optional[str] = Field(None, description="Fallback stage if any")
    generation_mode: Optional[str] = Field(None, description="Generation/fallback mode")
    css_variables: Optional[Dict[str, str]] = Field(None, description="Typography CSS variables")

    model_config = ConfigDict(extra="ignore")


class GenerateResponse(BaseModel):
    """Main response model for successful generation."""

    action_id: int = Field(..., ge=0, le=5, description="Action that was performed")
    content: ContentPayload = Field(..., description="Generated content payload")

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
                    "encouragement_text": "Great job working through this complex topic!",
                },
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


class LLMProviderInfo(BaseModel):
    """LLM provider status reported by /health."""

    name: str = Field(..., description="Provider name (e.g., 'ollama', 'openai')")
    healthy: bool = Field(..., description="Whether the provider is currently reachable/healthy")
    error: Optional[str] = Field(None, description="Last error message from provider check, if any")

    model_config = ConfigDict(extra="allow")


class HealthResponse(BaseModel):
    """Response model for health check endpoint."""

    status: str = Field(..., description="Overall health status")
    timestamp: str = Field(..., description="Health check timestamp")
    groq_reachable: bool = Field(..., description="Whether Groq is configured and ready")
    ollama_reachable: bool = Field(..., description="Whether Ollama is currently reachable")
    kokoro_reachable: bool = Field(..., description="Whether Kokoro TTS is currently reachable")
    llm_provider: Optional[LLMProviderInfo] = Field(None, description="Active LLM provider status")
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
