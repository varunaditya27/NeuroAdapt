# gen-engine Dockerfile
# Production container for Generative Synthesis Engine
#
# BUILD:
#   docker build -t neuroadapt/gen-engine:1.0.0 .
#
# RUN:
#   docker run -p 8001:8001 \
#     -e OLLAMA_URL=http://ollama:11434 \
#     -e TTS_URL=http://kokoro-tts:8880 \
#     neuroadapt/gen-engine:1.0.0
#
# DEPENDENCIES:
#   - Ollama service (http://ollama:11434)
#   - Kokoro TTS service (http://kokoro-tts:8880)
#   - Stable Diffusion (local, downloaded first run)
#   - Manim (installed via pip, requires ffmpeg)
#
# NOTES:
#   - Non-root user 'app' for security
#   - Layer caching optimized for fast builds
#   - Health check configured for orchestration

# TODO: Define base image (python:3.11-slim)
# TODO: Install system dependencies (ffmpeg, etc)
# TODO: Create non-root user
# TODO: Copy requirements.txt and install packages
# TODO: Copy source code
# TODO: Set environment variables
# TODO: Expose port 8001
# TODO: Define HEALTHCHECK
# TODO: Set entrypoint (uvicorn main:app)
