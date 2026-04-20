import fakeredis.aioredis
import pytest
from httpx import ASGITransport, AsyncClient

import backend.routers.feedback as feedback_router
from backend.db import get_db
from backend.main import create_app


class DummySession:
    def __init__(self) -> None:
        self.executed = False
        self.committed = False
        self.rolled_back = False

    async def execute(self, *_args, **_kwargs) -> None:
        self.executed = True

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True


@pytest.mark.asyncio
async def test_feedback_returns_reward_and_marks_stored(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    await fake_redis.set("state:session-feedback", "[0.1,0.2,0.3,0.4,0.5]", ex=300)

    dummy_session = DummySession()

    async def override_get_db():
        yield dummy_session

    monkeypatch.setattr(feedback_router, "redis_client", fake_redis)
    monkeypatch.setattr(feedback_router, "compute_reward", lambda event, chosen_format=None: 1.25)

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db

    payload = {
        "session_id": "session-feedback",
        "event": "complete",
        "chosen_format": "video",
        "current_state": [0.2, 0.2, 0.2, 0.2, 0.2],
        "action_taken": 2,
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/feedback", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["reward"] == 1.25
    assert body["stored"] is True
    assert dummy_session.executed is True
    assert dummy_session.committed is True
