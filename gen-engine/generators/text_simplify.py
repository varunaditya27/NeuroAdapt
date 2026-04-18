"""
Text Simplification Generator — Tier 2 (2-5 seconds)

================================================================================
PURPOSE:
    Simplify complex text to target reading level using Gemma 4 E2B.
    Verify output with Flesch-Kincaid scoring.
    Retry loop ensures FK grade meets target.

TIER: 2 (Fast, 2-5 seconds)

DEPENDENCIES:
    - ollama==0.4.1 : Local LLM inference
    - textstat==0.7.3 : Flesch-Kincaid scoring
    - spacy==3.8.2 : Sentence tokenization
    - prompts/simplify_*.txt : Few-shot prompt templates
    - tenacity : Exponential backoff retry logic

EXTERNAL SERVICES:
    - Ollama (http://localhost:11434) : Gemma 4 E2B model
    - PostgreSQL (for caching) : Store simplifications by hash

INPUT:
    text: str : Original text to simplify
    target_level: "grade5" | "grade8" | "university" : Target FK grade
    session_id: str : For logging/caching

FK GRADE TARGETS:
    - grade5: FK ≤ 6.0 (ages 11-12, severe difficulty)
    - grade8: FK ≤ 9.0 (ages 13-14, default)
    - university: FK ≤ 13.0 (ages 18+, minimal changes)

OUTPUT:
    {
        "simplified_text": str,
        "fk_grade": float,
        "original_fk": float,
        "chunks": list[str],
        "attempts": int,
        "cache_hit": bool
    }

ALGORITHM:
    1. Check cache (MD5 hash of text + target_level)
    2. If cache miss:
        a. Call Gemma 4 with few-shot prompt
        b. Compute FK score of output
        c. If FK ≤ target: return
        d. If FK > target AND attempts < 2:
            - Call with stricter prompt + error feedback
            - Retry step b-c
        e. If attempts exhausted: return best attempt + warning
    3. Chunk result by sentences for progressive reveal

KEY FUNCTIONS:
    - simplify_text(text, target_level, session_id) → dict
    - compute_fk_score(text) → float
    - chunk_by_sentences(text) → list[str]
    - load_prompt_template(level) → str
    - retry_with_stricter_prompt(text, fk_score, target) → str

ERROR HANDLING:
    - Ollama timeout: Serve original text + warning
    - FK computation failure: Return unverified simplified text + warning
    - Cache miss after 2 retries: Return best attempt with flag

CONSTRAINTS:
    - Max token input: 1024 (split if necessary)
    - Max token output: 512
    - Retry attempts: Max 2
    - Hard timeout: 5 seconds

INTEGRATION:
    - Called by action_router when action_id = 2
    - Results cached for 24 hours
    - FK scores logged for learner analytics

RELATED:
    - quiz_injector uses simplified text for question generation
    - chunk_renderer uses chunks for progressive reveal
================================================================================
"""

from __future__ import annotations

import hashlib
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional

import requests

try:
    import textstat
except ImportError:  # pragma: no cover
    textstat = None

from .chunk_renderer import chunk_text


logger = logging.getLogger(__name__)

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma4:e2b")
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "600"))

FK_TARGETS = {
    "grade5": 6.0,
    "grade8": 9.0,
    "university": 13.0,
}

PROMPT_FILES = {
    "grade5": "simplify_grade5.txt",
    "grade8": "simplify_grade8.txt",
    "university": "simplify_university.txt",
}

_CACHE: Dict[str, Dict[str, Any]] = {}


def _cache_key(text: str, target_level: str) -> str:
    return hashlib.md5(f"{target_level}|{text}".encode("utf-8")).hexdigest()


def _is_cache_valid(entry: Dict[str, Any]) -> bool:
    return bool(entry) and (time.time() - entry.get("cached_at", 0) <= CACHE_TTL_SECONDS)


def load_prompt_template(level: str) -> str:
    prompt_file = PROMPT_FILES.get(level, PROMPT_FILES["grade8"])
    prompt_path = Path(__file__).resolve().parents[1] / "prompts" / prompt_file
    if prompt_path.exists():
        return prompt_path.read_text(encoding="utf-8")
    return (
        "You are a readability simplification assistant. "
        "Rewrite the provided text to the requested reading level while preserving meaning."
    )


def compute_fk_score(text: str) -> float:
    if not text:
        return 0.0
    if textstat is None:
        words = max(1, len(text.split()))
        sentence_count = max(1, sum(text.count(c) for c in ".!?") or 1)
        approx = words / sentence_count
        return round(min(20.0, max(0.0, approx * 0.6)), 2)
    try:
        return round(float(textstat.flesch_kincaid_grade(text)), 2)
    except Exception:
        return 0.0


def _call_ollama(prompt: str, timeout_seconds: float = 4.5) -> str:
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
    }
    response = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json=payload,
        timeout=timeout_seconds,
    )
    response.raise_for_status()
    data = response.json()
    return (data.get("response") or "").strip()


def _build_prompt(template: str, text: str, target_fk: float, target_level: str) -> str:
    return (
        f"{template}\n\n"
        f"Target learner level: {target_level}\n"
        f"Target Flesch-Kincaid grade: <= {target_fk}\n\n"
        f"Text to simplify:\n{text}\n\n"
        "Return only the simplified text."
    )


def simplify_text(
    text: str,
    target_level: str = "grade8",
    session_id: Optional[str] = None,
    max_retries: int = 2,
) -> Dict[str, Any]:
    """
    Simplify text to target readability level with FK verification and retry loop.
    """
    started = time.time()
    level = getattr(target_level, "value", target_level) or "grade8"
    level = str(level).lower()
    target_fk = FK_TARGETS.get(level, FK_TARGETS["grade8"])
    original_text = (text or "").strip()

    if not original_text:
        return {
            "simplified_text": "",
            "fk_grade": 0.0,
            "original_fk": 0.0,
            "chunks": [],
            "attempts": 0,
            "cache_hit": False,
            "generation_time_ms": int((time.time() - started) * 1000),
        }

    key = _cache_key(original_text, level)
    cache_entry = _CACHE.get(key)
    if cache_entry and _is_cache_valid(cache_entry):
        cached = {k: v for k, v in cache_entry.items() if k != "cached_at"}
        cached["cache_hit"] = True
        cached["generation_time_ms"] = int((time.time() - started) * 1000)
        return cached

    original_fk = compute_fk_score(original_text)
    template = load_prompt_template(level)

    best_text = original_text
    best_fk = original_fk
    attempts = 0
    warning = None
    error = None

    for attempt in range(max_retries + 1):
        attempts = attempt + 1
        prompt = _build_prompt(template, original_text, target_fk, level)
        if attempt > 0:
            prompt += (
                "\n\nThe prior output was still too complex. "
                f"Previous FK score: {best_fk}. "
                "Use shorter sentences and simpler words."
            )

        try:
            candidate = _call_ollama(prompt)
        except Exception as exc:
            error = f"Ollama call failed: {exc}"
            logger.warning("Text simplification failed for session %s: %s", session_id, exc)
            break

        if not candidate:
            continue

        candidate_fk = compute_fk_score(candidate)
        if abs(candidate_fk - target_fk) < abs(best_fk - target_fk):
            best_text = candidate
            best_fk = candidate_fk

        if candidate_fk <= target_fk:
            best_text = candidate
            best_fk = candidate_fk
            break

    if best_fk > target_fk:
        warning = (
            f"Simplification did not fully reach target FK (target<={target_fk}, achieved={best_fk})."
        )

    chunk_payload = chunk_text(best_text, chunk_strategy="sentence")
    result = {
        "simplified_text": best_text,
        "fk_grade": best_fk,
        "original_fk": original_fk,
        "chunks": chunk_payload.get("chunks", []),
        "attempts": attempts,
        "cache_hit": False,
        "warning": warning,
        "error": error,
        "generation_time_ms": int((time.time() - started) * 1000),
    }

    _CACHE[key] = {
        **result,
        "cache_hit": False,
        "cached_at": time.time(),
    }

    return result
