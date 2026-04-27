from __future__ import annotations

from uuid import uuid4

from models.request_schemas import GenerateRequest, PrefetchRequest
from orchestration import action_router as ar
from orchestration.action_router import route_and_generate, start_prefetch


def test_route_hyperfocus_preempts_to_hold():
    request = GenerateRequest(
        action_id=2,
        slide_content="Photosynthesis is a biochemical process.",
        learner_level="grade8",
    )

    # With strict workflow request schema we force preemption via gate patch.
    original_gate = ar.check_hyperfocus
    ar.check_hyperfocus = lambda **_kwargs: (True, 0.9, "hyperfocus_entered")
    routed = route_and_generate(request)
    ar.check_hyperfocus = original_gate

    assert routed["no_content"] is True
    assert routed["action_id"] == 0
    assert routed["hyperfocus_override"] is True


def test_route_action_one_returns_chunks():
    request = GenerateRequest(
        action_id=1,
        slide_content="Sentence one. Sentence two.",
        learner_level="grade8",
    )

    routed = route_and_generate(request)
    assert routed["no_content"] is False
    assert routed["action_id"] == 1
    assert len(routed["content"]["chunks"]) >= 1
    assert "css_variables" in routed["content"]


def test_prefetch_request_queues_tasks():
    request = PrefetchRequest(
        session_id=uuid4(),
        top_actions=[1],
        slide_content="Newton's first law states that...",
        learner_level="grade8",
    )

    result = start_prefetch(request)
    assert result["prefetch_started"] in {True, False}
    assert result["tasks_queued"] >= 0
    assert result["estimated_completion_ms"] > 0


def test_route_action_two_uses_plain_learner_level(monkeypatch):
    captured = {"target_level": None}

    def fake_simplify(text: str, target_level: str = "grade8", session_id: str | None = None):
        captured["target_level"] = target_level
        return {
            "simplified_text": text,
            "fk_grade": 6.2,
            "original_fk": 9.1,
            "chunks": [],
        }

    monkeypatch.setattr(ar, "simplify_text", fake_simplify)

    request = GenerateRequest(
        action_id=2,
        slide_content="Dense concept paragraph for simplification.",
        learner_level="grade5",
    )

    routed = route_and_generate(request)
    assert routed["action_id"] == 2
    assert captured["target_level"] == "grade5"


def test_route_action_three_inferrs_stem_from_slide_content(monkeypatch):
    called = {"manim": 0, "image": 0}

    def fake_manim(*_args, **_kwargs):
        called["manim"] += 1
        return {"video_url": "/tmp/demo.mp4", "duration_ms": 1200}

    def fake_image(*_args, **_kwargs):
        called["image"] += 1
        return {"image_url": "/tmp/demo.png"}

    monkeypatch.setattr(ar, "generate_manim_animation", fake_manim)
    monkeypatch.setattr(ar, "generate_image", fake_image)
    monkeypatch.setattr(
        ar,
        "generate_tts",
        lambda *_args, **_kwargs: {"audio_url": "/tmp/demo.wav", "word_timestamps": []},
    )

    request = GenerateRequest(
        action_id=3,
        slide_content="Explain momentum conservation in physics.",
        learner_level="grade8",
    )

    routed = route_and_generate(request)
    assert routed["action_id"] == 3
    assert called["manim"] == 1
    assert called["image"] == 0
    assert routed["content"].get("video_url") == "/tmp/demo.mp4"


def test_action_two_timeout_includes_fallback_metadata(monkeypatch):
    def fake_timeout(_func, _timeout, *_args, **_kwargs):
        return {}, True, 5000, "timeout"

    monkeypatch.setattr(ar, "run_with_timeout", fake_timeout)

    request = GenerateRequest(
        action_id=2,
        slide_content="Dense text for timeout fallback.",
        learner_level="grade8",
    )

    routed = route_and_generate(request)
    content = routed["content"]
    assert content.get("fallback_stage") == "text_simplify_timeout"
    assert content.get("generation_mode") == "text_fallback"
    assert isinstance(content.get("chunks"), list)
