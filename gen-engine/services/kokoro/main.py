"""
Kokoro TTS — Placeholder FastAPI Service for Phase 0

Simple health check endpoint for container readiness probes.
Replaced with actual TTS implementation in Phase 1.
"""

from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI(
    title="kokoro-tts",
    version="0.1.0",
    description="Placeholder Kokoro TTS service for Phase 0"
)


@app.get("/health")
def health():
    """Health check endpoint for Docker Compose and Kubernetes."""
    return JSONResponse({"status": "ok"})
