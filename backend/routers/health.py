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
