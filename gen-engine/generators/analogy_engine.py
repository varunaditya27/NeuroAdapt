"""Tier-2 analogy engine (escape hatch)."""

from __future__ import annotations

import os
from typing import Any

import requests

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma4:e2b")


def _template_analogies(concept: str) -> list[dict[str, Any]]:
    concept_title = concept.strip() or "this concept"
    return [
        {
            "id": 1,
            "title": "Nature Lens",
            "source_domain": "nature",
            "explanation": (
                f"Think of {concept_title} like a garden ecosystem: each part has a role, "
                "and outcomes depend on how those parts interact over time."
            ),
            "example": (
                "If one part changes, nearby parts adjust too—just like plants, water, and sunlight."
            ),
        },
        {
            "id": 2,
            "title": "Sports Lens",
            "source_domain": "sports",
            "explanation": (
                f"Imagine {concept_title} as a team strategy. A single player matters, "
                "but coordination across roles determines the final result."
            ),
            "example": "Strong passing patterns beat isolated effort, even with talented players.",
        },
        {
            "id": 3,
            "title": "Tech Lens",
            "source_domain": "tech",
            "explanation": (
                f"Treat {concept_title} like a distributed system: inputs, rules, and feedback loops "
                "produce reliable output when components stay aligned."
            ),
            "example": "When one service slows down, the whole pipeline can lag unless it adapts.",
        },
    ]


def _try_ollama(
    concept: str, slide_content: str, timeout_seconds: float = 2.8
) -> list[dict[str, Any]] | None:
    prompt = (
        "Generate exactly 3 analogies for an educational concept."
        " Use three distinct domains: nature, sports, tech."
        " Return strict JSON list with keys: id,title,source_domain,explanation,example."
        f"\n\nConcept: {concept}\nContext: {slide_content[:800]}"
    )

    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "format": "json",
                "options": {"temperature": 0.4, "num_predict": 500},
            },
            timeout=timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json().get("response", "")
        import json

        maybe = json.loads(payload)
        if isinstance(maybe, list) and len(maybe) >= 3:
            cleaned: list[dict[str, Any]] = []
            for idx, row in enumerate(maybe[:3], start=1):
                cleaned.append(
                    {
                        "id": int(row.get("id", idx)),
                        "title": str(row.get("title", f"Analogy {idx}")),
                        "source_domain": str(row.get("source_domain", "general")),
                        "explanation": str(row.get("explanation", "")),
                        "example": str(row.get("example", "")),
                    }
                )
            return cleaned
    except Exception:
        return None

    return None


def generate_analogies(
    concept: str,
    slide_content: str,
    learner_level: str = "grade8",
) -> dict[str, Any]:
    """Return 3 analogies in distinct domains."""
    concept_value = concept or "the concept"
    analogies = _try_ollama(concept_value, slide_content) or _template_analogies(concept_value)

    return {
        "analogies": analogies,
        "encouragement_text": "Nice question—trying new perspectives is exactly how deep learning happens.",
        "learner_level": learner_level,
    }
