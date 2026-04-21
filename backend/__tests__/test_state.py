import json

import fakeredis.aioredis
import pytest
from httpx import ASGITransport, AsyncClient

import backend.routers.action as action_router
import backend.routers.state as state_router
from backend.main import create_app


@pytest.mark.asyncio
async def test_state_post_caches_vector_with_ttl(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr(state_router, "redis_client", fake_redis)
    monkeypatch.setattr(action_router, "redis_client", fake_redis)

    app = create_app()

    payload = {
        "session_id": "session-123",
        "dwell": 0.25,
        "jitter": 0.35,
        "focus": 0.75,
        "stall": 0.10,
        "pref_delta": 0.60,
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/state", json=payload)

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "session_id": "session-123"}

    cached = await fake_redis.get("state:session-123")
    assert cached is not None
    assert json.loads(cached) == [0.25, 0.35, 0.75, 0.10, 0.60]

    ttl = await fake_redis.ttl("state:session-123")
    assert 0 < ttl <= 300
