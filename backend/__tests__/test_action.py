import fakeredis.aioredis
import pytest
from httpx import ASGITransport, AsyncClient

import backend.routers.action as action_router
from backend.main import create_app


@pytest.mark.asyncio
async def test_action_endpoint_applies_confidence_gate(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    await fake_redis.set("state:session-low-confidence", "[0.2, 0.2, 0.2, 0.2, 0.2]", ex=300)

    monkeypatch.setattr(action_router, "redis_client", fake_redis)
    monkeypatch.setattr(action_router, "_infer_q_values", lambda _: [0.0, 0.0, 0.0, 0.0, 0.0, 0.0])

    app = create_app()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/action", params={"session_id": "session-low-confidence"})

    assert response.status_code == 200
    body = response.json()

    assert body["action_id"] == 0
    assert body["gated"] is True
    assert 0.0 <= body["confidence"] <= 1.0
