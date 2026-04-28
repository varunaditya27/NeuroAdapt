from __future__ import annotations

from PIL import Image

from generators import image_gen


def test_image_safety_heuristic_flags_high_saturation_image():
    neon = Image.new("RGB", (64, 64), (255, 0, 255))

    is_safe, method, reason = image_gen._verify_generated_image_safety(neon)

    assert is_safe is False
    assert method == "heuristic_postcheck"
    assert "saturation" in reason or "contrast" in reason


def test_image_safety_heuristic_accepts_calm_palette_image():
    calm = Image.new("RGB", (64, 64), (168, 218, 220))

    is_safe, method, reason = image_gen._verify_generated_image_safety(calm)

    assert is_safe is True
    assert method == "heuristic_postcheck"
    assert reason == "passed"
