from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def test_generate_action_one_accepts_workflow_minimal_request():
    response = client.post(
        "/api/generate",
        json={
            "action_id": 1,
            "slide_content": "Sentence one. Sentence two.",
            "learner_level": "grade8",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["action_id"] == 1
    assert "cache_hit" not in payload
    assert "hyperfocus_override" not in payload
    assert "request_id" not in payload
    assert isinstance(payload["content"].get("chunks"), list)


def test_generate_returns_204_on_hyperfocus_override():
    response = client.post(
        "/api/generate",
        json={
            "action_id": 0,
            "slide_content": "No-op action should return no content.",
            "learner_level": "grade8",
        },
    )

    assert response.status_code == 204
    assert response.content == b""


def test_prefetch_rejects_action_candidates_alias():
    response = client.post(
        "/api/prefetch",
        json={
            "session_id": str(uuid4()),
            "action_candidates": [1, 2],
            "slide_content": "Newton's first law states that an object at rest stays at rest.",
        },
    )

    assert response.status_code == 422


def test_health_includes_documented_reachability_and_capacity_fields():
    response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert "ollama_reachable" in payload
    assert "kokoro_reachable" in payload
    assert "disk_space_gb" in payload
    assert "cache_size_mb" in payload
    assert "cache" in payload
    assert "prompts" in payload
    assert "services" in payload
    assert isinstance(payload["services"], dict)

    if payload["services"]:
        first_service = next(iter(payload["services"].values()))
        assert "status" in first_service
        assert "checked_seconds_ago" in first_service


def test_generate_rejects_non_workflow_fields():
    response = client.post(
        "/api/generate",
        json={
            "action_id": 3,
            "slide_content": "Explain this with narration and an avatar.",
            "learner_level": "grade8",
            "voice_profile": "af_bella",
        },
    )

    assert response.status_code == 422
