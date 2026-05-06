import pytest
from httpx import ASGITransport, AsyncClient

from backend.db import get_db
from backend.main import create_app
from backend.services.state_store import clear_state_cache, set_cached_state


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
    clear_state_cache()
    set_cached_state("session-feedback", [0.1, 0.2, 0.3, 0.4, 0.5])

    dummy_session = DummySession()

    async def override_get_db():
        yield dummy_session

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
    assert isinstance(body["reward"], float)
    assert body["stored"] is True
    assert dummy_session.executed is True
    assert dummy_session.committed is True
