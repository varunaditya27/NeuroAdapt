"""
Generators Package — Content Generation Modules

Exports:
    - text_simplify : Text simplification with FK verification
    - quiz_injector : Mastery-scaled MCQ generation
    - analogy_engine : 3-analogy escape hatch
    - manim_gen : STEM animation generation
    - image_gen : Autism-safe image generation
    - kokoro_tts : Calm-preset TTS
    - liveportrait_avatar : Lip-sync avatar video
    - chunk_renderer : Progressive text reveal
    - typography_morpher : CSS state morphing
"""

from . import (
    analogy_engine,
    chunk_renderer,
    image_gen,
    kokoro_tts,
    liveportrait_avatar,
    manim_gen,
    quiz_injector,
    text_simplify,
    typography_morpher,
)

__all__ = [
    "text_simplify",
    "quiz_injector",
    "analogy_engine",
    "manim_gen",
    "image_gen",
    "kokoro_tts",
    "liveportrait_avatar",
    "chunk_renderer",
    "typography_morpher",
]
