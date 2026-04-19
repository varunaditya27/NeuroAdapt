"""Chunk renderer for progressive reveal text experiences (Tier 1)."""

from __future__ import annotations

import hashlib
import re
from typing import Any, List

textstat: Any = None
try:
    import textstat as _textstat
except Exception:  # pragma: no cover - optional runtime dependency
    _textstat = None
textstat = _textstat

spacy: Any = None
_spacy: Any = None
try:
    import spacy as _spacy
except Exception:  # pragma: no cover - optional runtime dependency
    _spacy = None
spacy = _spacy

_NLP: Any | None = None
_CACHE: dict[str, dict[str, Any]] = {}
_CACHE_MAX = 500


def _get_nlp() -> Any | None:
    global _NLP
    if _NLP is not None:
        return _NLP
    if spacy is None:
        return None

    try:
        _NLP = spacy.load("en_core_web_sm")
        return _NLP
    except Exception:
        return None


def _readability_grade(text: str) -> float:
    if not text.strip():
        return 0.0
    if textstat is None:
        # Lightweight fallback heuristic when textstat is unavailable.
        words = max(1, len(text.split()))
        avg_word_len = sum(len(w) for w in text.split()) / words
        return round(min(18.0, max(1.0, 0.25 * avg_word_len + words / 20)), 2)
    try:
        score = float(textstat.flesch_kincaid_grade(text))
        return round(max(0.0, min(20.0, score)), 2)
    except Exception:
        return 8.0


def _split_sentences(text: str) -> List[str]:
    nlp = _get_nlp()
    if nlp is not None:
        try:
            doc = nlp(text)
            sents = [s.text.strip() for s in doc.sents if s.text.strip()]
            if sents:
                return sents
        except Exception:
            pass

    rough = re.split(r"(?<=[.!?])\s+", text.strip())
    return [s.strip() for s in rough if s.strip()]


def _merge_short_sentences(sentences: List[str], min_words: int = 8) -> List[str]:
    merged: List[str] = []
    i = 0
    while i < len(sentences):
        current = sentences[i]
        current_words = len(current.split())
        if current_words < min_words and i + 1 < len(sentences):
            merged.append(f"{current} {sentences[i + 1]}")
            i += 2
            continue
        merged.append(current)
        i += 1
    return merged


def _enforce_min_chars(units: List[str], min_chars: int = 10) -> List[str]:
    """Ensure chunks are meaningful by merging fragments smaller than `min_chars`."""
    out: List[str] = []
    carry = ""

    for unit in units:
        current = unit.strip()
        if not current:
            continue

        if carry:
            current = f"{carry} {current}".strip()
            carry = ""

        if len(current) < min_chars:
            if out:
                out[-1] = f"{out[-1]} {current}".strip()
            else:
                carry = current
            continue

        out.append(current)

    if carry:
        if out:
            out[-1] = f"{out[-1]} {carry}".strip()
        else:
            out.append(carry)

    return out


def estimate_read_time_seconds(chunks: List[dict[str, Any]], wpm: int = 180) -> int:
    words = sum(int(chunk.get("word_count", 0)) for chunk in chunks)
    return max(1, int((words / max(120, wpm)) * 60))


def chunk_text(
    text: str,
    chunk_strategy: str = "sentence",
    preserve_formatting: bool = True,
) -> dict[str, Any]:
    """Split text into progressive chunks with readability metadata."""
    cleaned = text.strip()
    if not cleaned:
        return {
            "chunks": [],
            "total_chunks": 0,
            "estimated_read_time_seconds": 0,
        }

    cache_key = hashlib.md5(f"{chunk_strategy}:{cleaned}".encode("utf-8")).hexdigest()
    if cache_key in _CACHE:
        return _CACHE[cache_key]

    if chunk_strategy == "paragraph":
        units = [u.strip() for u in re.split(r"\n\s*\n", cleaned) if u.strip()]
    else:
        units = _split_sentences(cleaned)
        if chunk_strategy == "hybrid":
            units = _merge_short_sentences(units)

    units = _enforce_min_chars(units, min_chars=10)

    if not preserve_formatting:
        units = [" ".join(u.split()) for u in units]

    chunks: List[dict[str, Any]] = []
    for unit in units:
        words = unit.split()
        if not words:
            continue
        chunks.append(
            {
                "text": unit,
                "readability_grade": _readability_grade(unit),
                "word_count": len(words),
            }
        )

    result = {
        "chunks": chunks,
        "total_chunks": len(chunks),
        "estimated_read_time_seconds": estimate_read_time_seconds(chunks),
    }

    if len(_CACHE) >= _CACHE_MAX:
        _CACHE.pop(next(iter(_CACHE)))
    _CACHE[cache_key] = result
    return result
