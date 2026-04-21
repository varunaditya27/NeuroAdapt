from __future__ import annotations

from generators import analogy_engine as ae


def test_analogy_engine_returns_analogy_types():
    result = ae.generate_analogies("Momentum", "Momentum is mass times velocity.")

    assert isinstance(result.get("analogies"), list)
    assert len(result["analogies"]) == 3
    assert isinstance(result.get("analogy_types"), list)
    assert len(result["analogy_types"]) == 3


def test_analogy_engine_replaces_low_distinctness_outputs(monkeypatch):
    duplicated = [
        {
            "id": 1,
            "title": "A",
            "source_domain": "sports",
            "explanation": "Same explanation repeated for all analogies.",
            "example": "Same example.",
        },
        {
            "id": 2,
            "title": "B",
            "source_domain": "nature",
            "explanation": "Same explanation repeated for all analogies.",
            "example": "Same example.",
        },
        {
            "id": 3,
            "title": "C",
            "source_domain": "tech",
            "explanation": "Same explanation repeated for all analogies.",
            "example": "Same example.",
        },
    ]

    monkeypatch.setattr(ae, "_try_ollama", lambda *_args, **_kwargs: duplicated)

    result = ae.generate_analogies("Neural Networks", "Neural networks learn patterns.")

    # Distinctness guard should switch to curated template set.
    assert result["analogies"][0]["title"] == "Nature Lens"
    assert result.get("warning") is not None
