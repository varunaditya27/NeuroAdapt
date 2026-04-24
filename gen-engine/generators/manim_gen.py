"""Tier-3 Manim animation generation with writer-reviewer retries."""

from __future__ import annotations

import ast
import hashlib
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Tuple

import requests

from generators.image_gen import generate_image

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma4:e2b")
PROMPTS_DIR = Path(__file__).resolve().parents[1] / "prompts"


def _resolve_video_dir() -> Path:
    preferred = Path(__file__).resolve().parents[1] / "cache" / "videos"
    try:
        preferred.mkdir(parents=True, exist_ok=True)
        return preferred
    except Exception:
        fallback = Path(os.getenv("GEN_ENGINE_CACHE_DIR", "/tmp/neuroadapt-gen-engine")) / "videos"
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback


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


def _call_ollama(prompt: str, system: str, timeout_seconds: float = 600.0) -> str:
    response = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json={
            "model": OLLAMA_MODEL,
            "system": system,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.35, "num_predict": 900},
        },
        timeout=timeout_seconds,
    )
    response.raise_for_status()
    return (response.json().get("response") or "").strip()


def _render_scene(
    scene_code: str, output_stem: str, timeout_seconds: float
) -> Tuple[bool, str, str | None]:
    with tempfile.TemporaryDirectory(prefix="neuroadapt_manim_") as temp_dir:
        temp_path = Path(temp_dir)
        scene_file = temp_path / "scene.py"
        scene_file.write_text(scene_code, encoding="utf-8")

        cmd = ["manim", "-ql", str(scene_file), "NeuroScene", "-o", output_stem]
        try:
            proc = subprocess.run(
                cmd,
                cwd=temp_dir,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
            )
        except subprocess.TimeoutExpired:
            return False, "manim render timed out", None

        if proc.returncode != 0:
            logs = proc.stderr or ""
            if proc.stdout:
                logs = f"{logs}\n{proc.stdout}".strip()
            return False, (logs or "manim render failed"), None

        matches = list(temp_path.rglob(f"{output_stem}.mp4"))
        if not matches:
            return False, "render finished but mp4 not found", None

        out_path = _VIDEO_DIR / f"{output_stem}.mp4"
        shutil.move(str(matches[0]), out_path)
        logs = proc.stdout or ""
        if proc.stderr:
            logs = f"{logs}\n{proc.stderr}".strip()
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
            timeout=2,
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
                generated = _call_ollama(
                    prompt=(
                        f"Create a short educational Manim scene for concept: {concept}. "
                        f"Context: {slide_content[:1200]}"
                    ),
                    system=writer_system,
                    timeout_seconds=12,
                )
                extracted = _extract_python_code(generated)
                scene_code = extracted or scene_code
            except Exception:
                pass
        else:
            reviewer_attempts += 1
            try:
                reviewed = _call_ollama(
                    prompt=(
                        "Fix the following Manim code using the error log. "
                        f"\n\nCode:\n{scene_code}\n\nError:\n{last_error}"
                    ),
                    system=reviewer_system,
                    timeout_seconds=10,
                )
                extracted = _extract_python_code(reviewed)
                scene_code = extracted or scene_code
            except Exception:
                scene_code = _default_scene_code(concept)

        is_safe, safety_reason = _is_safe_scene_code(scene_code)
        if not is_safe:
            last_error = f"unsafe_scene_code:{safety_reason}"
            scene_code = _default_scene_code(concept)

        ok, message, output_path = _render_scene(scene_code, key, timeout_seconds=20)
        if ok:
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
        last_error = message

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
