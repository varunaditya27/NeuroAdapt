"""Tier-2 quiz injector with mastery-aware difficulty."""

from __future__ import annotations

import os
import re
from typing import Dict, List

try:
    import psycopg2  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    psycopg2 = None

_STOPWORDS = {
    "the",
    "and",
    "that",
    "this",
    "with",
    "from",
    "for",
    "have",
    "into",
    "your",
    "their",
    "about",
    "when",
    "where",
    "which",
    "while",
}


def _db_url() -> str | None:
    return os.getenv("POSTGRES_URL") or os.getenv("DATABASE_URL")


def query_mastery_score(session_id: str, concept_key: str) -> float:
    """Lookup mastery score from local Postgres; return neutral default on failures."""
    if psycopg2 is None:
        return 0.5

    db_url = _db_url()
    if not db_url:
        return 0.5

    try:
        with psycopg2.connect(db_url, connect_timeout=2) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT mastery_score
                    FROM learner_concept_mastery
                    WHERE session_id = %s AND concept_key = %s
                    ORDER BY updated_at DESC
                    LIMIT 1
                    """,
                    (session_id, concept_key),
                )
                row = cur.fetchone()
                if row and row[0] is not None:
                    return max(0.0, min(1.0, float(row[0])))
    except Exception:
        return 0.5

    return 0.5


def determine_difficulty_tier(mastery_score: float) -> str:
    if mastery_score < 0.4:
        return "struggling"
    if mastery_score < 0.7:
        return "developing"
    return "confident"


def _extract_terms(text: str, limit: int = 8) -> List[str]:
    words = re.findall(r"[A-Za-z][A-Za-z\-]{3,}", text.lower())
    uniq: List[str] = []
    for w in words:
        if w in _STOPWORDS:
            continue
        if w not in uniq:
            uniq.append(w)
        if len(uniq) >= limit:
            break
    return uniq


def _encouragement_for(tier: str) -> str:
    if tier == "struggling":
        return "Nice effort—focus on the key idea first, then build from there."
    if tier == "developing":
        return "Great progress—you're connecting concepts well."
    return "Awesome—you're ready for transfer-level questions."


def _question_set(concept_key: str, terms: List[str], tier: str) -> List[dict]:
    fallback_terms = terms + ["process", "system", "energy", "model"]
    t1, t2, t3 = fallback_terms[0], fallback_terms[1], fallback_terms[2]

    if tier == "struggling":
        difficulty = "easy"
        return [
            {
                "id": 1,
                "text": f"Which term is most central to this lesson?",
                "options": [concept_key, t1, t2, t3],
                "correct_index": 0,
                "difficulty": difficulty,
            },
            {
                "id": 2,
                "text": f"What is the safest summary of {concept_key}?",
                "options": [
                    f"It is a core idea in this slide.",
                    "It is unrelated trivia.",
                    "It is always false.",
                    "It replaces every concept.",
                ],
                "correct_index": 0,
                "difficulty": difficulty,
            },
            {
                "id": 3,
                "text": "What should you do first when reviewing this topic?",
                "options": [
                    "Identify the main concept and one example.",
                    "Memorize all details at once.",
                    "Skip definitions entirely.",
                    "Ignore context and only read formulas.",
                ],
                "correct_index": 0,
                "difficulty": difficulty,
            },
        ]

    if tier == "developing":
        difficulty = "medium"
        return [
            {
                "id": 1,
                "text": f"Which statement best applies {concept_key} in context?",
                "options": [
                    f"Use {concept_key} to explain how parts relate.",
                    "Use random facts with no relation.",
                    "Assume the opposite without evidence.",
                    "Avoid examples entirely.",
                ],
                "correct_index": 0,
                "difficulty": difficulty,
            },
            {
                "id": 2,
                "text": "Which is the strongest learning strategy here?",
                "options": [
                    "Connect each key term to one concrete example.",
                    "Read quickly and skip reflection.",
                    "Only memorize headings.",
                    "Ignore uncertain points.",
                ],
                "correct_index": 0,
                "difficulty": difficulty,
            },
            {
                "id": 3,
                "text": f"If {t1} changes, what should you do next?",
                "options": [
                    "Re-evaluate related concepts before concluding.",
                    "Assume nothing else is affected.",
                    "Delete all previous notes.",
                    "Ignore the change entirely.",
                ],
                "correct_index": 0,
                "difficulty": difficulty,
            },
        ]

    difficulty = "hard"
    return [
        {
            "id": 1,
            "text": f"Which transfer use-case best demonstrates deep understanding of {concept_key}?",
            "options": [
                "Applying the idea to a new domain with justified mapping.",
                "Repeating one definition verbatim.",
                "Listing terms without relationships.",
                "Choosing an answer by guesswork.",
            ],
            "correct_index": 0,
            "difficulty": difficulty,
        },
        {
            "id": 2,
            "text": "Which response reflects critical evaluation?",
            "options": [
                "Compare assumptions, evidence, and outcomes.",
                "Accept the first explanation blindly.",
                "Dismiss all alternative views.",
                "Treat every claim as equally strong.",
            ],
            "correct_index": 0,
            "difficulty": difficulty,
        },
        {
            "id": 3,
            "text": f"How should {t2} and {t3} be handled in a complex scenario?",
            "options": [
                "Model their interaction before final conclusions.",
                "Treat them as unrelated by default.",
                "Ignore constraints and edge cases.",
                "Use only one variable and discard context.",
            ],
            "correct_index": 0,
            "difficulty": difficulty,
        },
    ]


def generate_quiz(
    slide_content: str,
    session_id: str,
    concept: str | None = None,
    learner_id: str | None = None,
) -> Dict:
    """Generate 3 MCQs with difficulty scaled by concept mastery."""
    terms = _extract_terms(slide_content)
    concept_key = (concept or (terms[0] if terms else "core concept")).lower()

    mastery_score = query_mastery_score(session_id=session_id, concept_key=concept_key)
    tier = determine_difficulty_tier(mastery_score)
    questions = _question_set(concept_key, terms, tier)

    return {
        "quiz_json": questions,
        "mastery_level": tier,
        "estimated_time_seconds": 90,
        "encouragement_text": _encouragement_for(tier),
        "mastery_score": mastery_score,
        "learner_id": learner_id,
    }
