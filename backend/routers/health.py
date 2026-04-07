from fastapi import APIRouter
from fastapi.responses import Response

from backend.db import redis_client

router = APIRouter(tags=["health"])


async def _redis_status() -> str:
    try:
        is_connected = await redis_client.ping()
        return "connected" if is_connected else "disconnected"
    except Exception:
        return "disconnected"


async def _health_payload() -> dict[str, str]:
    return {"status": "ok", "redis": await _redis_status()}


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
