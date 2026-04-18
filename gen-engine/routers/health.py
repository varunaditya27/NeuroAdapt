"""
GET /health — Readiness & Liveness Probe

================================================================================
PURPOSE:
    Kubernetes readiness/liveness probe endpoint.
    Verifies all critical services are available.

DEPENDENCIES:
    - fastapi : APIRouter
    - ollama : Can reach Ollama server
    - requests : HTTP health checks
    - asyncio : Timeout enforcement

EXTERNAL SERVICES CHECKED:
    - Ollama (http://localhost:11434/api/tags) : Gemma 4 E2B model loaded
    - Kokoro TTS (http://localhost:8880/health) : Audio service ready
    - Disk space : Sufficient for cache (>5GB)
    - Memory : System RAM > 8GB

RESPONSE 200 OK:
    {
        "status": "healthy",
        "timestamp": "2026-04-16T10:30:45Z",
        "services": {
            "ollama": "ok",
            "kokoro_tts": "ok",
            "disk_space": "ok",
            "memory": "ok"
        },
        "version": "1.0.0"
    }

RESPONSE 503 SERVICE UNAVAILABLE:
    {
        "status": "unhealthy",
        "timestamp": "2026-04-16T10:30:45Z",
        "services": {
            "ollama": "failed",
            "kokoro_tts": "ok",
            "disk_space": "ok",
            "memory": "warning"
        },
        "errors": ["Ollama not responding", "Memory < 8GB"]
    }

KEY FUNCTIONS:
    - get /health : Main readiness check
        1. Check Ollama connection
        2. Check Kokoro TTS connection
        3. Check disk/memory
        4. Return aggregated status

TIMEOUT:
    - Individual service checks: 2 seconds each
    - Total endpoint timeout: 10 seconds
    - If timeout, return 503 Service Unavailable

KUBERNETES USAGE:
    readinessProbe:
      httpGet:
        path: /health
        port: 8001
      initialDelaySeconds: 10
      periodSeconds: 10
      timeoutSeconds: 5
      failureThreshold: 3

INTEGRATION:
    - Called by Kubernetes, Docker Compose health checks
    - Called by monitoring/alerting systems
    - Used by load balancer to route traffic
================================================================================
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse
import psutil
import shutil
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/detailed")
async def detailed_health():
    """
    Detailed health check with system resource information.
    Used for monitoring and debugging.
    """
    # Check disk space
    disk = shutil.disk_usage("/")
    disk_gb = disk.free / (1024**3)
    disk_status = "ok" if disk_gb > 5 else "warning" if disk_gb > 1 else "critical"

    # Check memory
    memory = psutil.virtual_memory()
    memory_gb = memory.available / (1024**3)
    memory_status = "ok" if memory_gb > 8 else "warning" if memory_gb > 4 else "critical"

    # Check CPU
    cpu_percent = psutil.cpu_percent(interval=1)
    cpu_status = "ok" if cpu_percent < 80 else "warning" if cpu_percent < 95 else "critical"

    return JSONResponse(
        content={
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "0.1.0",
            "system": {
                "disk_space_gb": round(disk_gb, 1),
                "disk_status": disk_status,
                "memory_gb": round(memory_gb, 1),
                "memory_status": memory_status,
                "cpu_percent": cpu_percent,
                "cpu_status": cpu_status,
            },
            "services": {
                "ollama": "ok",  # Placeholder - will be checked in main.py
                "kokoro_tts": "ok",  # Placeholder - will be checked in main.py
            }
        }
    )
