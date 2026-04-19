from __future__ import annotations

import hashlib

from generators import manim_gen


def test_manim_missing_binary_falls_back_to_image(monkeypatch):
    monkeypatch.setattr(manim_gen.shutil, "which", lambda _cmd: None)
    monkeypatch.setattr(
        manim_gen,
        "generate_image",
        lambda **_kwargs: {"image_url": "/tmp/fallback.svg"},
    )

    result = manim_gen.generate_manim_animation(
        concept="Projectile Motion",
        slide_content="Explain projectile path",
        learner_level="grade8",
    )

    assert result["video_url"] is None
    assert result["image_url"] == "/tmp/fallback.svg"
    assert "warning" in result


def test_manim_cache_hit_returns_existing_mp4(tmp_path, monkeypatch):
    monkeypatch.setattr(manim_gen, "_VIDEO_DIR", tmp_path)

    concept = "Newton"
    slide = "Force equals mass times acceleration"
    level = "grade8"
    key = hashlib.md5(f"{concept}:{level}:{slide}".encode("utf-8")).hexdigest()
    cached = tmp_path / f"{key}.mp4"
    cached.write_bytes(b"fake mp4")

    result = manim_gen.generate_manim_animation(concept=concept, slide_content=slide, learner_level=level)

    assert result["cache_hit"] is True
    assert result["video_url"] == str(cached)


def test_manim_render_failure_uses_static_fallback(monkeypatch):
    monkeypatch.setattr(manim_gen.shutil, "which", lambda _cmd: "/usr/bin/manim")
    monkeypatch.setattr(
        manim_gen,
        "_render_scene",
        lambda *_args, **_kwargs: (False, "syntax error", None),
    )
    monkeypatch.setattr(
        manim_gen,
        "generate_image",
        lambda **_kwargs: {"image_url": "/tmp/fallback.svg"},
    )

    result = manim_gen.generate_manim_animation(
        concept="Neural Network",
        slide_content="Nodes and weighted edges",
        learner_level="grade8",
        max_retries=1,
    )

    assert result["video_url"] is None
    assert result["image_url"] == "/tmp/fallback.svg"
    assert "warning" in result
