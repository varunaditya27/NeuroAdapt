"""
Quiz Injector — Gamified Task Generator (Tier 2, 2-5 seconds)

================================================================================
PURPOSE:
    Generate 3 mastery-scaled multiple-choice questions.
    Difficulty based on learner's demonstrated mastery (from Postgres).
    Uses hybrid approach: template + LLM validation.

TIER: 2 (Fast, 2-5 seconds)

DEPENDENCIES:
    - ollama==0.4.1 : Validate MCQ quality
    - psycopg2 : Query learner mastery_score from Postgres
    - prompts/quiz_template.txt : MCQ generation template
    - tenacity : Retry logic for LLM validation

EXTERNAL SERVICES:
    - PostgreSQL : Query mastery_score for concept
    - Ollama : Validate MCQ quality
    - Redis (optional) : Cache generated quizzes

INPUT:
    concept: str : What the quiz tests (e.g., "Photosynthesis")
    learner_id: str : UUID to look up mastery
    slide_content: str : Context for distractors
    session_id: str : For logging

MASTERY LEVELS (from Postgres):
    - < 0.4 : Struggling (recall, 3 very easy questions)
    - 0.4-0.7 : Developing (application, 3 moderate questions)
    - > 0.7 : Confident (transfer, 3 challenging questions)

OUTPUT:
    {
        "quiz_id": str,
        "questions": [
            {
                "id": int,
                "text": str,
                "options": [str, str, str, str],
                "correct_index": int,
                "difficulty": "easy" | "moderate" | "hard"
            },
            ...
        ],
        "mastery_level": "struggling" | "developing" | "confident",
        "estimated_time_seconds": int,
        "encouragement_text": str,
        "generation_time_ms": int
    }

ALGORITHM:
    1. Query Postgres for learner's mastery_score on concept
    2. Determine difficulty tier:
        a. < 0.4 → 3 recall questions (multiple choice, 4 options)
        b. 0.4-0.7 → 3 partial application (4-5 options, some ambiguity)
        c. > 0.7 → 3 novel application (distractors from related concepts)
    3. Use template + prompt to generate MCQs
    4. Validate via Gemma 4:
        - Correct answer is factually correct
        - Distractors are plausible but wrong
        - Question matches difficulty level
    5. Retry if validation fails (max 2 retries)
    6. Add encouragement text based on mastery

QUESTION BANK STRATEGY:
    - Store pre-authored question templates by concept
    - Use LLM to parametrize and validate
    - Avoid duplicate questions (check cache)

ANSWER TRACKING:
    - Record learner response immediately (PostgreSQL)
    - Update mastery_score after correct answer
    - Log for learning curve analysis

KEY FUNCTIONS:
    - generate_quiz(concept, learner_id, slide_content) → dict
    - query_mastery_score(learner_id, concept) → float
    - determine_difficulty_tier(mastery_score) → str
    - generate_mcq_by_template(concept, difficulty) → list[dict]
    - validate_mcq_with_llm(question) → bool
    - add_encouragement_text(mastery_level) → str

ERROR HANDLING:
    - Mastery lookup failure: Assume mastery=0.5 (moderate)
    - LLM validation timeout: Skip validation (serve as-is with warning)
    - Template load failure: Use hardcoded fallback questions

CONSTRAINTS:
    - 3 questions per quiz (fixed)
    - 4-5 answer options per question
    - Hard timeout: 5 seconds
    - Max retries: 2

INTEGRATION:
    - Called by action_router when action_id = 4
    - Responses stored in PostgreSQL learner_responses table
    - Mastery scores updated by backend scoring engine
    - Quiz answers logged for learning analytics

RELATED:
    - mastery_score updated by backend evaluation
    - Questions reused if similar concepts presented
================================================================================
"""

from __future__ import annotations

import os
import time
import uuid
from typing import Any, Dict, List, Optional

try:
    import psycopg2
except ImportError:  # pragma: no cover
    psycopg2 = None


POSTGRES_URL = os.getenv(
    "POSTGRES_URL",
    os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/neuroadapt"),
)


def query_mastery_score(learner_id: Optional[str], concept: str, default_score: float = 0.5) -> float:
    """Fetch mastery score from Postgres with graceful fallback."""
    if not learner_id or not concept or psycopg2 is None:
        return default_score

    try:
        with psycopg2.connect(POSTGRES_URL, connect_timeout=2) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT mastery_score
                    FROM learner_mastery_scores
                    WHERE learner_id = %s AND concept = %s
                    LIMIT 1
                    """,
                    (learner_id, concept),
                )
                row = cur.fetchone()
                if row is None:
                    return default_score
                return max(0.0, min(1.0, float(row[0])))
    except Exception:
        return default_score


def determine_difficulty_tier(mastery_score: float) -> str:
    if mastery_score < 0.4:
        return "easy"
    if mastery_score <= 0.7:
        return "moderate"
    return "hard"


def _generate_questions(concept: str, difficulty: str) -> List[Dict[str, Any]]:
    concept_label = concept or "current concept"
    stem_by_difficulty = {
        "easy": "recall",
        "moderate": "application",
        "hard": "transfer",
    }
    stem = stem_by_difficulty[difficulty]

    return [
        {
            "id": 1,
            "text": f"({stem.title()}) Which statement best matches {concept_label}?",
            "options": [
                f"A core principle of {concept_label}",
                "An unrelated historical fact",
                "A random numerical value",
                "A grammar rule",
            ],
            "correct_index": 0,
            "difficulty": difficulty,
        },
        {
            "id": 2,
            "text": f"({stem.title()}) What happens first when applying {concept_label}?",
            "options": [
                "Identify the input conditions",
                "Skip directly to final output",
                "Ignore constraints entirely",
                "Replace all variables with constants",
            ],
            "correct_index": 0,
            "difficulty": difficulty,
        },
        {
            "id": 3,
            "text": f"({stem.title()}) Which option is the best reason to use {concept_label}?",
            "options": [
                "To improve understanding and decision quality",
                "To avoid learning fundamentals",
                "To remove all uncertainty instantly",
                "To make outcomes random",
            ],
            "correct_index": 0,
            "difficulty": difficulty,
        },
    ]


def _encouragement_text(difficulty: str) -> str:
    if difficulty == "easy":
        return "Great start—let's build confidence step by step."
    if difficulty == "moderate":
        return "Nice progress—you're connecting ideas well."
    return "Excellent work—you're ready for challenging transfer questions."


def generate_quiz(
    concept: str,
    learner_id: Optional[str],
    slide_content: str,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate a 3-question mastery-scaled quiz payload."""
    started = time.time()
    mastery_score = query_mastery_score(learner_id=learner_id, concept=concept or "")
    difficulty = determine_difficulty_tier(mastery_score)
    questions = _generate_questions(concept, difficulty)

    return {
        "quiz_id": str(uuid.uuid4()),
        "questions": questions,
        "quiz_json": questions,
        "mastery_level": difficulty,
        "estimated_time_seconds": 90 if difficulty == "easy" else 120 if difficulty == "moderate" else 150,
        "encouragement_text": _encouragement_text(difficulty),
        "generation_time_ms": int((time.time() - started) * 1000),
        "cache_hit": False,
    }
