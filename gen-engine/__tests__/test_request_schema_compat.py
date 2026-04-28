from __future__ import annotations

from uuid import uuid4

import pytest
from pydantic import ValidationError

from models.request_schemas import GenerateRequest, PrefetchRequest


def test_generate_request_accepts_workflow_minimal_shape():
    req = GenerateRequest.model_validate(
        {
            "action_id": 2,
            "slide_content": "Conservation of energy describes...",
            "learner_level": "grade8",
        }
    )

    assert req.action_id == 2
    assert req.learner_level.value == "grade8"


def test_generate_request_rejects_non_workflow_fields():
    with pytest.raises(ValidationError):
        GenerateRequest.model_validate(
            {
                "action_id": 3,
                "slide_content": "Draw a free-body diagram.",
                "learner_level": "grade8",
                "content_type": "stem",
            }
        )


def test_prefetch_request_accepts_minimal_shape():
    req = PrefetchRequest.model_validate(
        {
            "session_id": str(uuid4()),
            "top_actions": [3],
            "slide_content": "Newton's second law states...",
        }
    )

    assert req.top_actions == [3]


def test_prefetch_request_rejects_alias_and_extras():
    with pytest.raises(ValidationError):
        PrefetchRequest.model_validate(
            {
                "session_id": str(uuid4()),
                "action_candidates": [3],
                "slide_content": "Newton's second law states...",
            }
        )
