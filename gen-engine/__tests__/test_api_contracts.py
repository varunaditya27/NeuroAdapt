from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def _state_vector(**overrides):
    base = {
        "cognitive_load": 0.4,
        "regression_count": 1,
        "hyperfocus_composite": 0.2,
        "eye_gaze_stability": 0.7,
        "attention_switching": 0.3,
        "time_on_task": 120,
        "engagement_level": 0.6,
        "micro_pause_ratio": 0.1,
        "idle_time_bonus": 0.0,
    }
    base.update(overrides)
    return base


def test_generate_action_one_includes_hyperfocus_override_field():
    response = client.post(
        "/api/generate",
        json={
            "action_id": 1,
            "slide_content": "Sentence one. Sentence two.",
            "learner_level": "grade8",
            "session_id": str(uuid4()),
            "confidence": 0.75,
            "state_vector": _state_vector(),
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert "hyperfocus_override" in payload
    assert payload["hyperfocus_override"] is False
    assert isinstance(payload["content"].get("chunks"), list)


def test_generate_returns_204_on_hyperfocus_override():
    response = client.post(
        "/api/generate",
        json={
            "action_id": 2,
            "slide_content": "Dense technical paragraph that should not run when protected.",
            "learner_level": "grade8",
            "session_id": str(uuid4()),
            "confidence": 0.9,
            "state_vector": _state_vector(hyperfocus_composite=0.9),
        },
    )

    assert response.status_code == 204
    assert response.content == b""


def test_prefetch_accepts_action_candidates_alias():
    response = client.post(
        "/api/prefetch",
        json={
            "session_id": str(uuid4()),
            "action_candidates": [1, 2],
            "slide_content": "Newton's first law states that an object at rest stays at rest.",
        },
    )

    assert response.status_code == 202
    payload = response.json()
    assert payload["prefetch_started"] in {True, False}
    assert payload["tasks_queued"] >= 0


def test_health_includes_documented_reachability_and_capacity_fields():
    response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert "ollama_reachable" in payload
    assert "kokoro_reachable" in payload
    assert "disk_space_gb" in payload
    assert "cache_size_mb" in payload
