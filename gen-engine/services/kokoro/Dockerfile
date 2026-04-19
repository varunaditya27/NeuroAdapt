FROM python:3.11-slim

WORKDIR /app

# Install curl for health checks and espeak-ng for local audible synthesis
RUN apt-get update && apt-get install -y \
	curl \
	espeak-ng \
	&& rm -rf /var/lib/apt/lists/*

# Install FastAPI, Uvicorn, and multipart support for form/file uploads
RUN pip install --no-cache-dir fastapi uvicorn python-multipart

# Copy application
COPY main.py .

# Expose port
EXPOSE 8880

# Run application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8880"]
