"""Tier-3 image generation with autism-safe constraints and graceful fallback."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any

AUTISM_SAFE_NEGATIVE_PROMPT = (
    "high contrast, cluttered, busy background, neon colors, flashing elements, "
    "multiple faces, photorealistic crowds, chaotic composition, sharp geometric "
    "patterns, intense shadows, harsh lighting, saturated colors"
)


def _resolve_cache_dir() -> Path:
    preferred = Path(__file__).resolve().parents[1] / "cache" / "images"
    try:
        preferred.mkdir(parents=True, exist_ok=True)
        return preferred
    except Exception:
        fallback = Path(os.getenv("GEN_ENGINE_CACHE_DIR", "/tmp/neuroadapt-gen-engine")) / "images"
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback


_CACHE_DIR = _resolve_cache_dir()

_PIPE: Any | None = None
_PIPE_DEVICE = "cpu"


def _cache_key(concept: str, slide_content: str, learner_level: str) -> str:
    return hashlib.md5(f"{concept}:{learner_level}:{slide_content}".encode("utf-8")).hexdigest()


def _build_prompt(concept: str, slide_content: str, learner_level: str) -> str:
    learner_hint = {
        "grade5": "Use simple visual symbols and very clear composition.",
        "grade8": "Use simple but slightly richer context with one focal subject.",
        "university": "Use conceptually precise but minimal visual mapping.",
    }.get(str(learner_level), "Keep composition clean and minimal.")

    subject = concept or "the lesson concept"
    context = (slide_content or "").strip()[:240]
    context_line = f"Context hint: {context}." if context else ""

    return (
        f"A simple, clean illustration of {subject}. "
        "Soft muted pastel palette. One focal element. Generous white space. "
        "Calming composition, diffused lighting, educational clarity. "
        f"{learner_hint} {context_line}"
    ).strip()


def _write_svg_placeholder(file_path: Path, concept: str) -> None:
    safe_text = (concept or "Concept Illustration").replace("&", "and").replace("<", "")
    svg = f"""<svg xmlns='http://www.w3.org/2000/svg' width='768' height='512' viewBox='0 0 768 512'>
  <rect width='100%' height='100%' fill='#F9F7F0'/>
  <rect x='84' y='96' width='600' height='320' rx='24' fill='#A8DADC' opacity='0.65'/>
  <circle cx='220' cy='220' r='52' fill='#F1E8D9'/>
  <circle cx='560' cy='300' r='40' fill='#D4D4D8'/>
  <text x='384' y='256' font-size='28' text-anchor='middle' fill='#1A1A1A' font-family='Inter,Arial,sans-serif'>
    {safe_text[:54]}
  </text>
  <text x='384' y='292' font-size='14' text-anchor='middle' fill='#4B5563' font-family='Inter,Arial,sans-serif'>
    calm fallback visual (autism-safe palette)
  </text>
</svg>"""
    file_path.write_text(svg, encoding="utf-8")


def _load_diffusion_pipeline() -> Any | None:
    global _PIPE, _PIPE_DEVICE
    if _PIPE is not None:
        return _PIPE

    try:
        import torch
        from diffusers import StableDiffusionPipeline as _StableDiffusionPipeline

        StableDiffusionPipeline: Any = _StableDiffusionPipeline

        _PIPE_DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
        dtype = torch.float16 if _PIPE_DEVICE == "cuda" else torch.float32
        _PIPE = StableDiffusionPipeline.from_pretrained(
            os.getenv("SD_MODEL_ID", "runwayml/stable-diffusion-v1-5"),
            torch_dtype=dtype,
        )
        _PIPE = _PIPE.to(_PIPE_DEVICE)
        return _PIPE
    except Exception:
        return None


def generate_image(
    concept: str,
    slide_content: str = "",
    learner_level: str = "grade8",
    session_id: str | None = None,
) -> dict[str, Any]:
    """Generate an autism-safe educational image, or SVG fallback."""
    key = _cache_key(concept, slide_content, learner_level)
    png_path = _CACHE_DIR / f"{key}.png"
    svg_path = _CACHE_DIR / f"{key}.svg"

    if png_path.exists():
        return {
            "image_url": str(png_path),
            "format": "png",
            "width": 512,
            "height": 512,
            "safety_prompt_applied": True,
            "safety_verified": False,
            "safety_verification_method": "not_performed",
            "generation_mode": "sd_generated_cache",
            "cache_hit": True,
        }
    if svg_path.exists():
        return {
            "image_url": str(svg_path),
            "format": "svg",
            "width": 768,
            "height": 512,
            "safety_prompt_applied": True,
            "safety_verified": False,
            "safety_verification_method": "not_performed",
            "generation_mode": "svg_fallback_cache",
            "fallback_stage": "image_fallback_cache",
            "cache_hit": True,
            "warning": "Served calm SVG fallback visual.",
        }

    prompt = _build_prompt(concept, slide_content, learner_level)
    pipeline = _load_diffusion_pipeline()

    if pipeline is not None:
        try:
            image = pipeline(
                prompt=prompt,
                negative_prompt=AUTISM_SAFE_NEGATIVE_PROMPT,
                num_inference_steps=int(os.getenv("SD_INFERENCE_STEPS", "20")),
                guidance_scale=float(os.getenv("SD_GUIDANCE_SCALE", "7.0")),
                height=512,
                width=512,
            ).images[0]
            image.save(png_path)
            return {
                "image_url": str(png_path),
                "format": "png",
                "width": 512,
                "height": 512,
                "safety_prompt_applied": True,
                "safety_verified": False,
                "safety_verification_method": "prompt_only",
                "generation_mode": "sd_generated",
                "cache_hit": False,
                "prompt_used": prompt,
                "device": _PIPE_DEVICE,
            }
        except Exception as exc:
            _write_svg_placeholder(svg_path, concept)
            return {
                "image_url": str(svg_path),
                "format": "svg",
                "width": 768,
                "height": 512,
                "safety_prompt_applied": True,
                "safety_verified": False,
                "safety_verification_method": "not_performed",
                "generation_mode": "svg_fallback",
                "fallback_stage": "image_diffusion_failure",
                "cache_hit": False,
                "warning": f"Diffusion fallback used: {exc}",
            }

    _write_svg_placeholder(svg_path, concept)
    return {
        "image_url": str(svg_path),
        "format": "svg",
        "width": 768,
        "height": 512,
        "safety_prompt_applied": True,
        "safety_verified": False,
        "safety_verification_method": "not_performed",
        "generation_mode": "svg_fallback",
        "fallback_stage": "image_diffusion_unavailable",
        "cache_hit": False,
        "warning": "Stable Diffusion unavailable; served calm SVG fallback visual.",
    }
