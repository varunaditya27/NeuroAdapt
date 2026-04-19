"""Detailed health endpoints for system diagnostics."""

from __future__ import annotations

from datetime import datetime

import psutil
import shutil
from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get("/detailed")
async def detailed_health() -> JSONResponse:
    """Return system-level health information for debugging/observability."""
    disk = shutil.disk_usage("/")
    disk_gb = disk.free / (1024**3)
    disk_status = "ok" if disk_gb > 5 else "warning" if disk_gb > 1 else "critical"

    memory = psutil.virtual_memory()
    memory_gb = memory.available / (1024**3)
    memory_status = "ok" if memory_gb > 8 else "warning" if memory_gb > 4 else "critical"

    cpu_percent = psutil.cpu_percent(interval=0.2)
    cpu_status = "ok" if cpu_percent < 80 else "warning" if cpu_percent < 95 else "critical"

    overall_status = "healthy"
    if "critical" in {disk_status, memory_status, cpu_status}:
        overall_status = "degraded"

    return JSONResponse(
        content={
            "status": overall_status,
            "timestamp": datetime.now().isoformat(),
            "version": "0.2.0",
            "system": {
                "disk_space_gb": round(disk_gb, 1),
                "disk_status": disk_status,
                "memory_gb": round(memory_gb, 1),
                "memory_status": memory_status,
                "cpu_percent": round(cpu_percent, 1),
                "cpu_status": cpu_status,
            },
        }
    )
