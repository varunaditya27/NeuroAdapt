import pytest
from httpx import ASGITransport, AsyncClient

from backend.main import create_app
from backend.services.state_store import clear_state_cache, get_cached_state


@pytest.mark.asyncio
async def test_state_post_caches_vector_with_ttl(monkeypatch: pytest.MonkeyPatch) -> None:
    clear_state_cache()

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
    body = response.json()
    assert body["status"] == "ok"
    assert body["session_id"] == "session-123"

    assert get_cached_state("session-123") == [0.25, 0.35, 0.75, 0.10, 0.60]
