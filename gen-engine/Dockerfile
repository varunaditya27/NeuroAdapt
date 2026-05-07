# gen-engine Dockerfile
# Production container for Generative Synthesis Engine
#
# BUILD:
#   docker build -t neuroadapt/gen-engine:1.0.0 .
#
# RUN:
#   docker run -p 8001:8001 \
#     -e OLLAMA_URL=http://ollama:11434 \
#     -e KOKORO_TTS_URL=http://kokoro-tts:8880 \
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

FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    ffmpeg \
    pkg-config \
    build-essential \
    libcairo2-dev \
    libpango1.0-dev \
    libffi-dev \
    texlive \
    texlive-latex-extra \
    texlive-fonts-recommended \
    dvipng \
    dvisvgm \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd --create-home --shell /bin/bash app

# Set working directory
WORKDIR /home/app

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Create necessary directories
RUN mkdir -p /home/app/logs /home/app/cache && \
    chown -R app:app /home/app

# Switch to non-root user
USER app

# Set environment variables
ENV PYTHONPATH=/home/app
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
