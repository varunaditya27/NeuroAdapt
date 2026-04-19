from __future__ import annotations

from uuid import uuid4

from models.request_schemas import GenerateRequest, PrefetchRequest


def _state_vector() -> dict:
    return {
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


def test_generate_request_accepts_concept_id_alias():
    req = GenerateRequest.model_validate(
        {
            "action_id": 2,
            "slide_content": "Conservation of energy describes...",
            "learner_level": "grade8",
            "session_id": str(uuid4()),
            "confidence": 0.8,
            "state_vector": _state_vector(),
            "concept_id": "conservation_of_energy",
        }
    )

    assert req.concept == "conservation_of_energy"


def test_prefetch_request_accepts_concept_id_alias():
    req = PrefetchRequest.model_validate(
        {
            "session_id": str(uuid4()),
            "action_candidates": [3],
            "slide_content": "Newton's second law states...",
            "concept_id": "newton_second_law",
        }
    )

    assert req.top_actions == [3]
    assert req.concept == "newton_second_law"


def test_generate_request_accepts_stem_and_general_content_types():
    stem_req = GenerateRequest.model_validate(
        {
            "action_id": 3,
            "slide_content": "Draw a free-body diagram.",
            "learner_level": "grade8",
            "session_id": str(uuid4()),
            "confidence": 0.82,
            "state_vector": _state_vector(),
            "content_type": "stem",
        }
    )
    general_req = GenerateRequest.model_validate(
        {
            "action_id": 3,
            "slide_content": "Summarize the causes of World War I.",
            "learner_level": "grade8",
            "session_id": str(uuid4()),
            "confidence": 0.82,
            "state_vector": _state_vector(),
            "content_type": "general",
        }
    )

    assert stem_req.content_type is not None
    assert stem_req.content_type.value == "stem"
    assert general_req.content_type is not None
    assert general_req.content_type.value == "general"
