"""Tier-2 quiz injector with mastery-aware difficulty."""

from __future__ import annotations

import json
import logging
import os
import re
import threading
from pathlib import Path
from typing import Any, List

from orchestration.llm_provider import call_llm

try:
    import psycopg2
    from psycopg2.pool import SimpleConnectionPool
except Exception:  # pragma: no cover - optional dependency
    psycopg2 = None
    SimpleConnectionPool = None

logger = logging.getLogger(__name__)
PROMPTS_DIR = Path(__file__).resolve().parents[1] / "prompts"

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

_POOL_LOCK = threading.Lock()
_DB_POOL: SimpleConnectionPool | None = None
_DB_POOL_DSN: str | None = None


def _db_url() -> str | None:
    return os.getenv("POSTGRES_URL") or os.getenv("DATABASE_URL")


def _max_pool_connections() -> int:
    try:
        return max(2, int(os.getenv("POSTGRES_POOL_MAXCONN", "8")))
    except ValueError:
        return 8


def _get_pool(db_url: str) -> SimpleConnectionPool | None:
    global _DB_POOL, _DB_POOL_DSN
    if SimpleConnectionPool is None:
        return None

    with _POOL_LOCK:
        if _DB_POOL is not None and _DB_POOL_DSN == db_url:
            return _DB_POOL

        if _DB_POOL is not None:
            try:
                _DB_POOL.closeall()
            except Exception:
                pass

        try:
            _DB_POOL = SimpleConnectionPool(1, _max_pool_connections(), dsn=db_url)
            _DB_POOL_DSN = db_url
        except Exception:
            _DB_POOL = None
            _DB_POOL_DSN = None
            return None

        return _DB_POOL


def query_mastery_score(session_id: str, concept_key: str) -> float:
    """Lookup mastery score from local Postgres; return neutral default on failures."""
    if psycopg2 is None:
        return 0.5

    db_url = _db_url()
    if not db_url:
        return 0.5

    query = """
        SELECT mastery_score
        FROM learner_concept_mastery
        WHERE session_id = %s AND concept_key = %s
        ORDER BY updated_at DESC
        LIMIT 1
    """

    pool = _get_pool(db_url)
    if pool is not None:
        conn = None
        try:
            conn = pool.getconn()
            with conn.cursor() as cur:
                cur.execute(query, (session_id, concept_key))
                row = cur.fetchone()
                if row and row[0] is not None:
                    return max(0.0, min(1.0, float(row[0])))
        except Exception:
            return 0.5
        finally:
            if conn is not None:
                try:
                    pool.putconn(conn)
                except Exception:
                    pass
    else:
        try:
            with psycopg2.connect(db_url, connect_timeout=2) as conn:
                with conn.cursor() as cur:
                    cur.execute(query, (session_id, concept_key))
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


def _load_quiz_prompt() -> str:
    """Load quiz generator prompt."""
    prompt_file = PROMPTS_DIR / "quiz_generator.txt"
    try:
        return prompt_file.read_text(encoding="utf-8")
    except Exception as exc:
        logger.warning(f"Failed to load quiz_generator.txt: {exc}")
        return ""


def _generate_quiz_with_llm(
    concept: str,
    slide_content: str,
    tier: str,
    timeout_seconds: float = 450.0,
) -> list[dict[str, Any]] | None:
    """Generate concept-specific quiz questions using LLM.
    
    Args:
        concept: The topic being assessed (e.g., "photosynthesis")
        slide_content: The educational content for context
        tier: Difficulty tier - "struggling", "developing", or "advanced"
        timeout_seconds: LLM call timeout
        
    Returns:
        List of 3 quiz question dicts, or None on error
    """
    system_prompt = _load_quiz_prompt()
    if not system_prompt:
        logger.warning("Quiz generator prompt not loaded")
        return None
    
    # Map tier to difficulty
    difficulty_map = {
        "struggling": "easy",
        "developing": "medium",
        "advanced": "hard",
    }
    difficulty = difficulty_map.get(tier, "medium")
    
    user_prompt = (
        f"Concept: {concept}\n"
        f"Difficulty: {difficulty}\n"
        f"Slide Content:\n{slide_content[:1500]}\n\n"
        f"Generate 3 domain-specific quiz questions for this concept at {difficulty} difficulty."
    )
    
    try:
        logger.debug(f"Quiz: Generating LLM questions for '{concept}' at {difficulty} tier")
        response = call_llm(
            prompt=user_prompt,
            system=system_prompt,
            temperature=0.3,
            max_tokens=2000,
            timeout_seconds=timeout_seconds,
            response_format={"type": "json_object"},
        )
        
        # Parse JSON array from response
        questions = json.loads(response)
        if isinstance(questions, list) and len(questions) == 3:
            # Validate structure
            for q in questions:
                if not all(k in q for k in ["id", "text", "options", "correct_index", "difficulty"]):
                    logger.warning(f"Quiz: Invalid question structure: {q}")
                    return None
                if not isinstance(q["options"], list) or len(q["options"]) != 4:
                    logger.warning(f"Quiz: Question must have exactly 4 options: {q}")
                    return None
            logger.debug(f"Quiz: Successfully generated 3 LLM questions for '{concept}'")
            return questions
        else:
            logger.warning(f"Quiz: Expected 3 questions, got {len(questions) if isinstance(questions, list) else 'non-list'}")
            return None
    except json.JSONDecodeError as exc:
        logger.warning(f"Quiz: LLM response was not valid JSON: {exc}")
        return None
    except Exception as exc:
        logger.warning(f"Quiz: LLM generation failed: {exc}")
        return None


def _question_set(
    concept_key: str,
    terms: List[str],
    tier: str,
    slide_content: str = "",
) -> list[dict[str, Any]]:
    """Generate quiz questions for the concept, preferring LLM generation with fallback templates."""
    
    # Try LLM generation first if we have content
    if slide_content and slide_content.strip():
        llm_questions = _generate_quiz_with_llm(
            concept=concept_key,
            slide_content=slide_content,
            tier=tier,
            timeout_seconds=300.0,
        )
        if llm_questions:
            return llm_questions
        logger.info(f"Quiz: LLM generation failed for '{concept_key}', falling back to templates")
    
    # Fallback to hardcoded templates
    fallback_terms = terms + ["process", "system", "energy", "model"]
    t1, t2, t3 = fallback_terms[0], fallback_terms[1], fallback_terms[2]

    if tier == "struggling":
        difficulty = "easy"
        return [
            {
                "id": 1,
                "text": "Which term is most central to this lesson?",
                "options": [concept_key, t1, t2, t3],
                "correct_index": 0,
                "difficulty": difficulty,
            },
            {
                "id": 2,
                "text": f"What is the safest summary of {concept_key}?",
                "options": [
                    "It is a core idea in this slide.",
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
) -> dict[str, Any]:
    """Generate 3 MCQs with difficulty scaled by concept mastery."""
    terms = _extract_terms(slide_content)
    concept_key = (concept or (terms[0] if terms else "core concept")).lower()

    mastery_score = query_mastery_score(session_id=session_id, concept_key=concept_key)
    tier = determine_difficulty_tier(mastery_score)
    questions = _question_set(concept_key, terms, tier, slide_content)

    return {
        "quiz_json": questions,
        "mastery_level": tier,
        "estimated_time_seconds": 90,
        "encouragement_text": _encouragement_for(tier),
        "mastery_score": mastery_score,
        "learner_id": learner_id,
    }
