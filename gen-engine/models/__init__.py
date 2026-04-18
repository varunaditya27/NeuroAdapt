"""
Models Package — Pydantic Schema Definitions

Exports:
    - request_schemas : Input validation (GenerateRequest, StateVector)
    - response_schemas : Output serialization (GenerateResponse, etc)
"""

from .request_schemas import (
    ContentType,
    GenerateRequest,
    LearnerLevel,
    LearnerProfile,
    PrefetchRequest,
    StateVector,
)
from .response_schemas import (
    Analogy,
    CSSVariables,
    ChunkMetadata,
    ContentPayload,
    ErrorDetail,
    ErrorResponse,
    GenerateResponse,
    HealthResponse,
    Question,
    WordTimestamp,
)

__all__ = [
    "GenerateRequest",
    "StateVector",
    "LearnerLevel",
    "ContentType",
    "LearnerProfile",
    "PrefetchRequest",
    "GenerateResponse",
    "ContentPayload",
    "ErrorResponse",
    "ErrorDetail",
    "HealthResponse",
    "ChunkMetadata",
    "Question",
    "WordTimestamp",
    "Analogy",
    "CSSVariables",
]
