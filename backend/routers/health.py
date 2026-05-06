from fastapi import APIRouter
from fastapi.responses import Response

from backend.db import redis_client
from backend.services.state_store import cache_status

router = APIRouter(tags=["health"])


async def _redis_status() -> str:
    try:
        is_connected = await redis_client.ping()
        return "connected" if is_connected else "disconnected"
    except Exception:
        return "disconnected"


async def _health_payload() -> dict[str, str]:
    state_cache = cache_status()
    return {
        "status": "ok",
        "state_store": "memory",
        "state_cache_entries": str(state_cache["entries"]),
        "redis": await _redis_status(),
        "redis_required": "false",
    }


@router.get("/")
async def root() -> dict[str, str]:
    return {"status": "ok", "docs": "/docs", "health": "/health"}


@router.get("/favicon.ico", include_in_schema=False)
async def favicon() -> Response:
    return Response(status_code=204)


@router.get("/health")
async def health_check() -> dict[str, str]:
    return await _health_payload()


@router.get("/api/health")
async def health_check_api() -> dict[str, str]:
    return await _health_payload()


@router.get("/metrics")
async def metrics() -> Response:
    payload = await _health_payload()
    lines = [
        "# HELP neuroadapt_backend_up Backend process health.",
        "# TYPE neuroadapt_backend_up gauge",
        "neuroadapt_backend_up 1",
        "# HELP neuroadapt_backend_state_cache_entries In-memory state cache entries.",
        "# TYPE neuroadapt_backend_state_cache_entries gauge",
        f"neuroadapt_backend_state_cache_entries {payload['state_cache_entries']}",
        "# HELP neuroadapt_backend_redis_required Whether Redis is required for the demo path.",
        "# TYPE neuroadapt_backend_redis_required gauge",
        "neuroadapt_backend_redis_required 0",
    ]
    return Response("\n".join(lines) + "\n", media_type="text/plain; version=0.0.4")
