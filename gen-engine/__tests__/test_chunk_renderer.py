from __future__ import annotations

from generators.chunk_renderer import chunk_text


def test_chunk_renderer_enforces_min_character_size():
    text = "I. A. This sentence is long enough to stand alone."
    result = chunk_text(text, chunk_strategy="sentence")

    chunks = result.get("chunks", [])
    assert chunks, "Expected at least one chunk"
    assert all(len(chunk["text"].strip()) >= 10 for chunk in chunks)
