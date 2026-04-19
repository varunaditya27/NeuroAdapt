from __future__ import annotations

from pathlib import Path


def test_required_prompt_assets_exist_and_are_non_empty():
    prompts_dir = Path(__file__).resolve().parents[1] / "prompts"
    required = [
        "simplify_grade5.txt",
        "simplify_grade8.txt",
        "simplify_university.txt",
        "manim_expert.txt",
        "manim_reviewer.txt",
        "image_gen_base.txt",
        "analogy_generator.txt",
    ]

    missing = [name for name in required if not (prompts_dir / name).exists()]
    assert not missing, f"Missing required prompt files: {missing}"

    empty = [name for name in required if (prompts_dir / name).exists() and not (prompts_dir / name).read_text(encoding='utf-8').strip()]
    assert not empty, f"Prompt files must not be empty: {empty}"
