"""Tier-3 Manim animation generation with writer-reviewer retries."""

from __future__ import annotations

import ast
import hashlib
import logging
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Tuple


from generators.image_gen import generate_image
from orchestration.llm_provider import call_llm

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).resolve().parents[1] / "prompts"


def _resolve_video_dir() -> Path:
    preferred = Path(__file__).resolve().parents[1] / "cache" / "videos"
    try:
        preferred.mkdir(parents=True, exist_ok=True)
        return preferred
    except Exception:
        # Fallback: use /tmp with app name prefix
        fallback = Path(os.getenv("GEN_ENGINE_CACHE_DIR", "/tmp/neuroadapt-gen-engine")) / "videos"
        try:
            fallback.mkdir(parents=True, exist_ok=True)
            logger.warning(f"Using fallback video directory: {fallback} (cache/ not writable)")
            return fallback
        except Exception as e:
            logger.error(f"Both cache and fallback directories failed: {e}")
            # Final fallback: use system temp directory
            return Path(tempfile.gettempdir()) / "neuroadapt-videos"


_VIDEO_DIR = _resolve_video_dir()

_ALLOWED_IMPORT_ROOTS = {"manim", "math", "numpy", "np"}
_DISALLOWED_CALL_NAMES = {
    "eval",
    "exec",
    "compile",
    "open",
    "__import__",
    "input",
}
_DISALLOWED_ATTR_CALLS = {
    "system",
    "popen",
    "run",
    "call",
    "check_call",
    "check_output",
    "unlink",
    "remove",
    "rmtree",
}


def _load_prompt(filename: str, fallback: str) -> str:
    file_path = PROMPTS_DIR / filename
    if file_path.exists():
        return file_path.read_text(encoding="utf-8")
    return fallback


def _default_scene_code(concept: str) -> str:
    title = re.sub(r"[^A-Za-z0-9 ,.:;!?()\-_/]", "", concept or "Concept").strip() or "Concept"
    return f"""from manim import *

class NeuroScene(Scene):
    def construct(self):
        title = Text(\"{title[:50]}\", font_size=42)
        self.play(Write(title))
        self.wait(0.8)
        self.play(title.animate.to_edge(UP))

        left = Circle(radius=1.1, color=BLUE)
        right = Square(side_length=2.0, color=GREEN)
        right.shift(RIGHT * 3)

        arrow = Arrow(left.get_right(), right.get_left(), buff=0.2, color=YELLOW)
        self.play(Create(left), Create(right), GrowArrow(arrow))
        self.wait(1.5)
"""


def _is_safe_scene_code(scene_code: str) -> tuple[bool, str]:
    try:
        tree = ast.parse(scene_code)
    except SyntaxError as exc:
        return False, f"syntax_error:{exc.msg}"

    has_neuro_scene = False

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root not in _ALLOWED_IMPORT_ROOTS:
                    return False, f"disallowed_import:{root}"

        if isinstance(node, ast.ImportFrom):
            root = (node.module or "").split(".")[0]
            if root and root not in _ALLOWED_IMPORT_ROOTS:
                return False, f"disallowed_import_from:{root}"

        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in _DISALLOWED_CALL_NAMES:
                return False, f"disallowed_call:{node.func.id}"

            if isinstance(node.func, ast.Attribute):
                attr_name = node.func.attr
                if attr_name in _DISALLOWED_ATTR_CALLS:
                    return False, f"disallowed_attr_call:{attr_name}"

        if isinstance(node, ast.ClassDef) and node.name == "NeuroScene":
            has_neuro_scene = True

    if not has_neuro_scene:
        return False, "missing_neuroscene"

    return True, "ok"


def _extract_python_code(text: str) -> str:
    fenced = re.findall(r"```python\s*(.*?)```", text, flags=re.DOTALL)
    if fenced:
        return str(fenced[0].strip())
    fenced_any = re.findall(r"```\s*(.*?)```", text, flags=re.DOTALL)
    if fenced_any:
        return str(fenced_any[0].strip())
    return text.strip()


def _call_llm(prompt: str, system: str, timeout_seconds: float = 600.0) -> str:
    """Call LLM via dynamic provider (Groq or Ollama)."""
    return call_llm(
        prompt=prompt,
        system=system,
        temperature=0.35,
        max_tokens=8192,
        timeout_seconds=timeout_seconds,
    )


def _render_scene(
    scene_code: str, output_stem: str, timeout_seconds: float = 600.0
) -> Tuple[bool, str, str | None]:
    logger.debug(f"Rendering scene with code length: {len(scene_code)}, timeout: {timeout_seconds}s")
    with tempfile.TemporaryDirectory(prefix="neuroadapt_manim_") as temp_dir:
        temp_path = Path(temp_dir)
        scene_file = temp_path / "scene.py"
        scene_file.write_text(scene_code, encoding="utf-8")
        logger.debug(f"Wrote scene to {scene_file}")

        cmd = ["manim", "-ql", str(scene_file), "NeuroScene", "-o", output_stem]
        try:
            logger.debug(f"Running manim command: {' '.join(cmd)}")
            proc = subprocess.run(
                cmd,
                cwd=temp_dir,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
            )
        except subprocess.TimeoutExpired:
            logger.error(f"Manim render timed out after {timeout_seconds}s")
            return False, "manim render timed out", None

        if proc.returncode != 0:
            logs = proc.stderr or ""
            if proc.stdout:
                logs = f"{logs}\n{proc.stdout}".strip()
            logger.error(f"Manim render failed (rc={proc.returncode}): {logs[:500]}")
            return False, (logs or "manim render failed"), None

        matches = list(temp_path.rglob(f"{output_stem}.mp4"))
        if not matches:
            logger.error(f"Render finished but mp4 not found for stem={output_stem}")
            return False, "render finished but mp4 not found", None

        logger.debug(f"Found mp4 at {matches[0]}, moving to {_VIDEO_DIR}")
        out_path = _VIDEO_DIR / f"{output_stem}.mp4"
        shutil.move(str(matches[0]), out_path)
        logs = proc.stdout or ""
        if proc.stderr:
            logs = f"{logs}\n{proc.stderr}".strip()
        logger.info(f"Manim render succeeded, saved to {out_path}")
        return True, (logs or "ok"), str(out_path)


def _duration_ms(video_path: str | None) -> int:
    if not video_path:
        return 0
    if shutil.which("ffprobe") is None:
        return 0

    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=nokey=1:noprint_wrappers=1",
                video_path,
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            return 0
        value = float((result.stdout or "0").strip() or 0)
        return max(0, int(value * 1000))
    except Exception:
        return 0


def generate_manim_animation(
    concept: str,
    slide_content: str,
    learner_level: str = "grade8",
    session_id: str | None = None,
    max_retries: int = 2,
) -> dict[str, Any]:
    """Generate animation; fall back to static image if unavailable."""
    key = hashlib.md5(f"{concept}:{learner_level}:{slide_content}".encode("utf-8")).hexdigest()
    cached_video = _VIDEO_DIR / f"{key}.mp4"
    if cached_video.exists():
        duration_ms = _duration_ms(str(cached_video))
        return {
            "video_url": str(cached_video),
            "duration_ms": duration_ms,
            "cache_hit": True,
            "writer_attempts": 0,
            "reviewer_attempts": 0,
            "render_logs": None,
            "generation_mode": "manim_generated_cache",
        }

    if shutil.which("manim") is None:
        logger.warning("Manim binary not found in PATH")
        fallback = generate_image(
            concept=concept, slide_content=slide_content, learner_level=learner_level
        )
        return {
            "video_url": None,
            "duration_ms": 0,
            "image_url": fallback.get("image_url"),
            "warning": "Manim not installed; served static visual fallback.",
            "render_logs": "manim binary not available",
            "writer_attempts": 0,
            "reviewer_attempts": 0,
            "cache_hit": False,
            "generation_mode": "manim_fallback_static_image",
            "fallback_stage": "manim_unavailable",
        }

    writer_system = _load_prompt(
        "manim_expert.txt",
        "You are a Manim expert. Return only valid Python code defining class NeuroScene(Scene).",
    )
    reviewer_system = _load_prompt(
        "manim_reviewer.txt",
        "You fix Manim code. Return only corrected Python code defining class NeuroScene(Scene).",
    )

    scene_code = _default_scene_code(concept)
    writer_attempts = 0
    reviewer_attempts = 0
    last_error = ""

    for attempt in range(max_retries + 1):
        writer_attempts += 1
        if attempt == 0:
            try:
                logger.debug(f"Manim: Writer attempt {writer_attempts} with timeout=450s")
                generated = _call_llm(
                    prompt=(
                        f"Create a short educational Manim scene for concept: {concept}.\n"
                        f"Context: {slide_content[:1200]}\n\n"
                        f"CRITICAL REQUIREMENTS:\n"
                        f"- The class name must be exactly NeuroScene\n"
                        f"- The first line must be: from manim import *\n"
                        f"- Return only runnable Python code\n"
                        f"- Use Manim Community Edition v0.18 compatible code\n"
                    ),
                    system=writer_system,
                    timeout_seconds=450,
                )
                logger.debug(f"Manim: Writer LLM returned {len(generated)} chars")

                def _normalize_scene_class_name(scene_code: str) -> str:
                    return re.sub(
                        r"class\s+\w+\s*\(\s*Scene\s*\)\s*:",
                        "class NeuroScene(Scene):",
                        scene_code,
                        count=1,
                    )
                extracted = _extract_python_code(generated)
                if extracted:
                    scene_code = _normalize_scene_class_name(extracted)
                    logger.debug(f"Manim: Extracted {len(scene_code)} chars of Python code")
                else:
                    logger.warning("Manim: LLM returned no Python code")
            except Exception as exc:
                logger.warning(f"Manim writer LLM call failed: {exc}")
                pass
        else:
            reviewer_attempts += 1
            try:
                logger.debug(f"Manim: Reviewer attempt {reviewer_attempts} with timeout=900s")
                reviewed = _call_llm(
                    prompt=(
                        "Fix the following Manim code using the error log. "
                        f"\n\nCode:\n{scene_code}\n\nError:\n{last_error}"
                    ),
                    system=reviewer_system,
                    timeout_seconds=900,
                )
                logger.debug(f"Manim: Reviewer LLM returned {len(reviewed)} chars")
                extracted = _extract_python_code(reviewed)
                if extracted:
                    scene_code = _normalize_scene_class_name(extracted)
                    logger.debug(f"Manim: Extracted {len(scene_code)} chars of reviewed code")
                else:
                    logger.warning("Manim: Reviewer LLM returned no Python code")
            except Exception as exc:
                logger.warning(f"Manim reviewer LLM call failed: {exc}")
                scene_code = _default_scene_code(concept)

        is_safe, safety_reason = _is_safe_scene_code(scene_code)
        if not is_safe:
            logger.warning(f"Manim: Safety check failed: {safety_reason}")
            last_error = f"unsafe_scene_code:{safety_reason}"
            scene_code = _default_scene_code(concept)
        else:
            logger.debug("Manim: Safety check passed")

        logger.debug(f"Manim: Rendering scene (attempt {attempt + 1}/{max_retries + 1})")
        ok, message, output_path = _render_scene(scene_code, key, timeout_seconds=60)
        if ok:
            logger.info(f"Manim: Successfully rendered to {output_path}")
            duration_ms = _duration_ms(output_path)
            return {
                "video_url": output_path,
                "duration_ms": duration_ms,
                "cache_hit": False,
                "writer_attempts": writer_attempts,
                "reviewer_attempts": reviewer_attempts,
                "render_logs": message,
                "generation_mode": "manim_generated",
            }
        logger.warning(f"Manim: Render failed: {message}")
        last_error = message

    logger.error(f"Manim: All retries exhausted. Last error: {last_error}")
    fallback = generate_image(
        concept=concept, slide_content=slide_content, learner_level=learner_level
    )
    return {
        "video_url": None,
        "duration_ms": 0,
        "image_url": fallback.get("image_url"),
        "warning": f"Manim failed after retries; static fallback used ({last_error}).",
        "writer_attempts": writer_attempts,
        "reviewer_attempts": reviewer_attempts,
        "render_logs": last_error,
        "cache_hit": False,
        "generation_mode": "manim_fallback_static_image",
        "fallback_stage": "manim_retry_exhausted",
    }
