"""
Chunk Renderer — Progressive Text Reveal (Tier 1, Instant <1 second)

================================================================================
PURPOSE:
    Convert text into sentence-level chunks for progressive reveal.
    Frontend displays one sentence at a time, user-paced.
    Reduces cognitive overload from wall-of-text format.

TIER: 1 (Instant, <1 second)

DEPENDENCIES:
    - spacy==3.8.2 : Sentence tokenization
    - textstat==0.7.3 : Readability analysis (optional)

EXTERNAL SERVICES:
    - None (entirely local)

INPUT:
    text: str : Text to chunk
    chunk_strategy: "sentence" | "paragraph" | "hybrid"
    preserve_formatting: bool : Keep original punctuation

OUTPUT:
    {
        "chunks": [
            {"text": "First sentence.", "readability_grade": 5.2, "word_count": 2},
            {"text": "Second sentence.", "readability_grade": 6.1, "word_count": 2},
            ...
        ],
        "total_chunks": int,
        "estimated_read_time_seconds": int
    }

CHUNKING STRATEGIES:
    - "sentence": Break by sentence boundaries
    - "paragraph": Keep existing paragraphs intact
    - "hybrid": Smart grouping (2-3 sentences per chunk if short)

ALGORITHM:
    1. Load spaCy English model
    2. Process text through spaCy NLP pipeline
    3. For each sentence:
        a. Extract text (preserve punctuation)
        b. Count words
        c. Compute FK grade (optional)
        d. Create chunk object
    4. Group into meta-chunks if hybrid strategy:
        a. If sentence < 10 words: Combine with next
        b. Else: Keep separate
    5. Return chunk list + metadata

EXAMPLE:
    Input: "Photosynthesis is the process by which plants make food. 
            They use sunlight to create glucose. This process is essential 
            for life on Earth."
    
    Output:
    [
        {"text": "Photosynthesis is the process by which plants make food.", ...},
        {"text": "They use sunlight to create glucose.", ...},
        {"text": "This process is essential for life on Earth.", ...}
    ]

KEY FUNCTIONS:
    - chunk_text(text, chunk_strategy, preserve_formatting) → dict
    - estimate_read_time(chunks) → int
    - merge_short_sentences(chunks) → list[dict]

ERROR HANDLING:
    - Empty text: Return empty chunks list
    - spaCy model not loaded: Load on first call
    - Malformed text: Return as-is (no chunking)

CONSTRAINTS:
    - Max chunk length: 500 words (will split if longer)
    - Min chunk length: 1 word
    - Timeout: <1 second (should be instant)

OPTIMIZATION:
    - Load spaCy model once on startup
    - Cache chunked results by text_hash

INTEGRATION:
    - Called by action_router for all text-based responses
    - Frontend ContentRenderer receives chunks array
    - User controls reveal pace (next button or timer)
    - Timestamps used for auto-advance (if enabled)

RELATED:
    - Used by text_simplify to chunk simplified output
    - Used by manim narration text
    - Used by analogy explanations

================================================================================
"""

from __future__ import annotations

import re
from typing import Dict, List

try:
    import spacy
except ImportError:  # pragma: no cover - dependency can be optional in some environments
    spacy = None

try:
    import textstat
except ImportError:  # pragma: no cover
    textstat = None


_NLP = None
_NLP_LOAD_ATTEMPTED = False


def _load_spacy_model():
    global _NLP, _NLP_LOAD_ATTEMPTED
    if _NLP is not None or _NLP_LOAD_ATTEMPTED or spacy is None:
        return _NLP
    _NLP_LOAD_ATTEMPTED = True
    try:
        _NLP = spacy.load("en_core_web_sm", disable=["ner", "tagger", "lemmatizer"])
    except Exception:
        _NLP = None
    return _NLP


def _split_sentences(text: str) -> List[str]:
    cleaned = (text or "").strip()
    if not cleaned:
        return []

    nlp = _load_spacy_model()
    if nlp is not None:
        doc = nlp(cleaned)
        return [sent.text.strip() for sent in doc.sents if sent.text.strip()]

    # Lightweight regex fallback when spaCy model is not available.
    parts = re.split(r"(?<=[.!?])\s+", cleaned)
    return [part.strip() for part in parts if part.strip()]


def _compute_readability_grade(text: str) -> float:
    if not text:
        return 0.0
    if textstat is None:
        # Fallback heuristic when textstat isn't available.
        words = max(1, len(text.split()))
        sentences = max(1, len(re.split(r"[.!?]+", text)) - 1)
        avg_sentence_len = words / sentences
        return round(min(20.0, max(0.0, avg_sentence_len * 0.6)), 2)
    try:
        return round(float(textstat.flesch_kincaid_grade(text)), 2)
    except Exception:
        return 0.0


def merge_short_sentences(chunks: List[Dict[str, str]], min_words: int = 10) -> List[Dict[str, str]]:
    """Merge very short sentence chunks with the following chunk for smoother reveal."""
    if not chunks:
        return []

    merged: List[Dict[str, str]] = []
    buffer = None

    for chunk in chunks:
        word_count = len(chunk["text"].split())
        if buffer is None and word_count < min_words:
            buffer = chunk["text"]
            continue

        if buffer is not None:
            text = f"{buffer} {chunk['text']}".strip()
            merged.append({"text": text})
            buffer = None
        else:
            merged.append(chunk)

    if buffer is not None:
        if merged:
            merged[-1]["text"] = f"{merged[-1]['text']} {buffer}".strip()
        else:
            merged.append({"text": buffer})

    return merged


def estimate_read_time(chunks: List[Dict[str, str]], words_per_minute: int = 180) -> int:
    total_words = sum(len(chunk.get("text", "").split()) for chunk in chunks)
    if total_words <= 0:
        return 0
    return max(1, int((total_words / max(1, words_per_minute)) * 60))


def chunk_text(
    text: str,
    chunk_strategy: str = "sentence",
    preserve_formatting: bool = True,
) -> Dict[str, object]:
    """
    Convert full text into progressive reveal chunks with readability metadata.
    """
    raw_sentences = _split_sentences(text)

    if chunk_strategy == "paragraph":
        paragraphs = [p.strip() for p in (text or "").split("\n\n") if p.strip()]
        chunks = [{"text": p} for p in paragraphs]
    else:
        chunks = [{"text": s if preserve_formatting else s.strip()} for s in raw_sentences]
        if chunk_strategy == "hybrid":
            chunks = merge_short_sentences(chunks)

    enriched_chunks: List[Dict[str, object]] = []
    for chunk in chunks:
        chunk_text_value = chunk.get("text", "").strip()
        if not chunk_text_value:
            continue
        enriched_chunks.append(
            {
                "text": chunk_text_value,
                "readability_grade": _compute_readability_grade(chunk_text_value),
                "word_count": len(chunk_text_value.split()),
            }
        )

    return {
        "chunks": enriched_chunks,
        "total_chunks": len(enriched_chunks),
        "estimated_read_time_seconds": estimate_read_time(enriched_chunks),
    }
