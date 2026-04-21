"""Tier-2 text simplification with FK verification and retries."""

from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path
from typing import Any, Tuple

import requests

try:
    import textstat
except Exception:  # pragma: no cover - optional runtime dependency
    textstat = None

from generators.chunk_renderer import chunk_text

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma4:e2b")
PROMPTS_DIR = Path(__file__).resolve().parents[1] / "prompts"

TARGETS = {
    "grade5": 6.0,
    "grade8": 9.0,
    "university": 13.0,
}

_CACHE: dict[str, dict[str, Any]] = {}
_CACHE_MAX = 1000


def compute_fk_grade(text: str) -> float:
    if not text.strip():
        return 0.0
    if textstat is None:
        words = text.split()
        avg_word_len = sum(len(w) for w in words) / max(1, len(words))
        return round(min(20.0, max(1.0, avg_word_len * 0.6)), 2)
    try:
        return round(float(textstat.flesch_kincaid_grade(text)), 2)
    except Exception:
        return 8.0


def _load_prompt(target_level: str) -> str:
    candidates = [
        PROMPTS_DIR / f"simplify_{target_level}.txt",
        PROMPTS_DIR / "simplify_grade8.txt",
    ]
    for file_path in candidates:
        if file_path.exists():
            return file_path.read_text(encoding="utf-8")

    return (
        "Simplify the given educational content while preserving meaning. "
        "Use short sentences and concrete words."
    )


def _heuristic_simplify(text: str) -> str:
    replacements = {
        "utilize": "use",
        "approximately": "about",
        "demonstrates": "shows",
        "subsequently": "then",
        "therefore": "so",
        "additionally": "also",
        "facilitate": "help",
        "mitochondria": "mitochondria",
    }

    simplified = text
    for src, dst in replacements.items():
        simplified = re.sub(rf"\b{re.escape(src)}\b", dst, simplified, flags=re.IGNORECASE)

    parts = re.split(r"(?<=[.!?])\s+", simplified)
    flattened = []
    for sentence in parts:
        words = sentence.split()
        if len(words) <= 20:
            flattened.append(sentence.strip())
            continue

        midpoint = len(words) // 2
        first = " ".join(words[:midpoint]).strip(" ,;") + "."
        second = " ".join(words[midpoint:]).strip(" ,;")
        if second and second[-1] not in ".!?":
            second += "."
        flattened.extend([first, second])

    return " ".join(s for s in flattened if s).strip()


def _build_prompt(base_prompt: str, text: str, target_level: str, strict: bool = False) -> str:
    strict_note = (
        "\nSTRICT MODE: Use very short sentences (< 16 words), simple words, and active voice only."
        if strict
        else ""
    )
    return (
        f"{base_prompt}\n\n"
        f"Target level: {target_level}.\n"
        f"Preserve all facts. Do not add new claims.{strict_note}\n\n"
        f"Original text:\n{text}\n\n"
        "Simplified text:"
    )


def _call_ollama(prompt: str, timeout_seconds: float = 120.0) -> str:
    response = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json={
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.2, "top_p": 0.9, "num_predict": 512},
        },
        timeout=timeout_seconds,
    )
    response.raise_for_status()
    payload = response.json()
    return (payload.get("response") or "").strip()


def _cache_get(key: str) -> dict[str, Any] | None:
    return _CACHE.get(key)


def _cache_put(key: str, value: dict[str, Any]) -> None:
    if len(_CACHE) >= _CACHE_MAX:
        _CACHE.pop(next(iter(_CACHE)))
    _CACHE[key] = value


def simplify_text(text: str, target_level: str = "grade8", session_id: str | None = None) -> dict[str, Any]:
    """Simplify text and verify against FK target with one strict retry."""
    normalized_level = str(target_level)
    fk_target = TARGETS.get(normalized_level, TARGETS["grade8"])

    cache_key = hashlib.md5(f"{normalized_level}:{text}".encode("utf-8")).hexdigest()
    cached = _cache_get(cache_key)
    if cached is not None:
        return {**cached, "cache_hit": True}

    original_fk = compute_fk_grade(text)
    best_text = _heuristic_simplify(text)
    best_fk = compute_fk_grade(best_text)
    attempts = 0
    warning = None
    service_warning = None

    base_prompt = _load_prompt(normalized_level)

    for attempt in range(1, 3):
        attempts = attempt
        strict = attempt > 1
        prompt = _build_prompt(base_prompt, text, normalized_level, strict=strict)

        try:
            candidate = _call_ollama(prompt, timeout_seconds=60.0 if not strict else 90.0)
        except Exception as exc:
            if attempt < 2:
                continue
            service_warning = f"LLM unavailable on strict retry; heuristic fallback used ({exc})."
            candidate = _heuristic_simplify(text)

        if not candidate:
            if attempt < 2:
                # Allow strict retry before giving up.
                continue
            service_warning = (
                service_warning or "LLM returned empty output twice; heuristic fallback used."
            )
            candidate = _heuristic_simplify(text)

        candidate_fk = compute_fk_grade(candidate)
        if candidate_fk < best_fk:
            best_text, best_fk = candidate, candidate_fk

        if candidate_fk <= fk_target:
            best_text, best_fk = candidate, candidate_fk
            break

    if best_fk > fk_target:
        warning = (
            f"FK target not fully met (target≤{fk_target}, actual={best_fk}). "
            "Serving best available simplification."
        )

    if service_warning:
        warning = f"{warning} {service_warning}".strip() if warning else service_warning

    chunks_payload = chunk_text(best_text, chunk_strategy="sentence")

    result = {
        "simplified_text": best_text,
        "fk_grade": best_fk,
        "original_fk": original_fk,
        "chunks": chunks_payload.get("chunks", []),
        "attempts": attempts,
        "warning": warning,
        "cache_hit": False,
    }
    _cache_put(cache_key, result)
    return result


def simplify_with_fk_target(text: str, target_fk: float) -> Tuple[str, float]:
    """Helper for tests and internal checks."""
    result = simplify_text(text, target_level="grade8")
    simplified = result.get("simplified_text", text)
    fk_grade = float(result.get("fk_grade", compute_fk_grade(simplified)))
    if fk_grade > target_fk:
        simplified = _heuristic_simplify(simplified)
        fk_grade = compute_fk_grade(simplified)
    return simplified, fk_grade
