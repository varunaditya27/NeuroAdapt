"""Tier-2 analogy engine (escape hatch)."""

from __future__ import annotations

import math
import os
import re
from collections import Counter
from typing import Any

import requests

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma4:e2b")

_TOKEN_RE = re.compile(r"[a-zA-Z][a-zA-Z\-]{2,}")
_STOPWORDS = {
    "the",
    "and",
    "that",
    "this",
    "with",
    "from",
    "into",
    "over",
    "under",
    "about",
    "through",
    "where",
    "while",
    "when",
    "which",
    "their",
    "there",
    "because",
}


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


def _tokenize(text: str) -> list[str]:
    return [
        token
        for token in _TOKEN_RE.findall((text or "").lower())
        if token not in _STOPWORDS
    ]


def _cosine_similarity(left: str, right: str) -> float:
    left_counts = Counter(_tokenize(left))
    right_counts = Counter(_tokenize(right))
    if not left_counts or not right_counts:
        return 0.0

    vocab = set(left_counts) | set(right_counts)
    dot = sum(left_counts.get(term, 0) * right_counts.get(term, 0) for term in vocab)
    left_norm = math.sqrt(sum(value * value for value in left_counts.values()))
    right_norm = math.sqrt(sum(value * value for value in right_counts.values()))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return float(dot / (left_norm * right_norm))


def _max_pair_similarity(analogies: list[dict[str, Any]]) -> float:
    if len(analogies) < 2:
        return 0.0

    blocks: list[str] = []
    for analogy in analogies:
        blocks.append(
            " ".join(
                [
                    str(analogy.get("title", "")),
                    str(analogy.get("explanation", "")),
                    str(analogy.get("example", "")),
                ]
            )
        )

    max_similarity = 0.0
    for idx in range(len(blocks)):
        for jdx in range(idx + 1, len(blocks)):
            max_similarity = max(max_similarity, _cosine_similarity(blocks[idx], blocks[jdx]))
    return max_similarity


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

    warning: str | None = None
    max_similarity = _max_pair_similarity(analogies)
    if max_similarity >= 0.60:
        analogies = _template_analogies(concept_value)
        max_similarity = _max_pair_similarity(analogies)
        warning = (
            "Analogy distinctness guard replaced highly similar model output with curated templates."
        )

    analogy_types = [str(item.get("source_domain", "general")) for item in analogies]

    return {
        "analogies": analogies,
        "analogy_types": analogy_types,
        "encouragement_text": "Nice question—trying new perspectives is exactly how deep learning happens.",
        "learner_level": learner_level,
        "distinctness_max_similarity": round(max_similarity, 3),
        "warning": warning,
    }
