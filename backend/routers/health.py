from fastapi import APIRouter
from fastapi.responses import Response

from backend.services.state_store import cache_status

router = APIRouter(tags=["health"])

async def _health_payload() -> dict[str, str]:
    state_cache = cache_status()
    return {
        "status": "ok",
        "state_store": "memory",
        "state_cache_entries": str(state_cache["entries"]),
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
    ]
    return Response("\n".join(lines) + "\n", media_type="text/plain; version=0.0.4")
