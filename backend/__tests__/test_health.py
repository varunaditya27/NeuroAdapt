import fakeredis.aioredis
import pytest
from httpx import ASGITransport, AsyncClient

import backend.routers.health as health_router
from backend.main import create_app


@pytest.mark.asyncio
async def test_root_endpoint_returns_ok_metadata() -> None:
    app = create_app()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "docs": "/docs", "health": "/health"}


@pytest.mark.asyncio
async def test_favicon_endpoint_returns_no_content() -> None:
    app = create_app()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/favicon.ico")

    assert response.status_code == 204


@pytest.mark.asyncio
async def test_health_endpoint_reports_redis_connected(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr(health_router, "redis_client", fake_redis)

    app = create_app()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "redis": "connected"}


@pytest.mark.asyncio
async def test_health_api_alias_reports_redis_connected(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr(health_router, "redis_client", fake_redis)

    app = create_app()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "redis": "connected"}
