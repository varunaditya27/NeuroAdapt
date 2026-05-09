FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    curl \
    espeak-ng \
    libsndfile1 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install real Kokoro neural TTS (kokoro-fastapi wraps the kokoro-onnx model)
# kokoro-onnx provides CPU-only inference, no GPU required
RUN pip install --no-cache-dir \
    fastapi \
    uvicorn \
    python-multipart \
    kokoro-onnx==0.4.4 \
    soundfile \
    numpy

# Download Kokoro ONNX model + voices metadata into /app
RUN curl -L -o /app/kokoro-v1.0.onnx \
        https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx && \
    curl -L -o /app/voices.bin \
        https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin

# Pre-download the ONNX voice model at build time so first request is fast
# kokoro-onnx v0.4.x uses model file kokoro-v1.0.onnx + voices.json
RUN python -c "from kokoro_onnx import Kokoro; Kokoro('kokoro-v1.0.onnx', 'voices.bin')" || true

COPY main.py .

EXPOSE 8880
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8880"]
