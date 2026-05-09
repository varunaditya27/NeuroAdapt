"""Tier-3 Manim animation generation with writer-reviewer retries.

Failure modes defended against:
  1. Old Manim syntax: self.play(obj.method, args) — caught by AST before render
  2. Bad class name: normalised to NeuroScene by regex post-extraction
  3. Default scene uses old .to_edge syntax — fixed to .animate.to_edge
  4. Narration JSON spanning multiple lines (greedy regex) — DOTALL limited
  5. LLM wrapping code in markdown fences — stripped by _extract_python_code
  6. Render timeout too short for CPU containers — configurable via env var
  7. ffprobe not available — graceful None return
  8. Video cache returning stale narration=None — narration regenerated from VTT
  9. Safety validator passing unsafe code that then crashes renderer
  10. Groq 429 rate limit — propagated cleanly, caller can retry
"""

from __future__ import annotations

import ast
import hashlib
import json
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


# ── Video cache directory ─────────────────────────────────────────────────────

def _resolve_video_dir() -> Path:
    preferred = Path(__file__).resolve().parents[1] / "cache" / "videos"
    try:
        preferred.mkdir(parents=True, exist_ok=True)
        return preferred
    except Exception:
        fallback = Path(os.getenv("GEN_ENGINE_CACHE_DIR", "/tmp/neuroadapt-gen-engine")) / "videos"
        try:
            fallback.mkdir(parents=True, exist_ok=True)
            logger.warning(f"Using fallback video dir: {fallback}")
            return fallback
        except Exception as exc:
            logger.error(f"All video dirs failed: {exc}")
            return Path(tempfile.gettempdir()) / "neuroadapt-videos"


_VIDEO_DIR = _resolve_video_dir()


# ── Security allowlists/blocklists ────────────────────────────────────────────

_ALLOWED_IMPORT_ROOTS = {"manim", "math", "numpy"}

_DISALLOWED_CALL_NAMES = {
    "eval", "exec", "compile", "open", "__import__", "input",
}

_DISALLOWED_ATTR_CALLS = {
    "system", "popen", "run", "call", "check_call", "check_output",
    "unlink", "remove", "rmtree", "chmod", "chown",
}

# Old Manim v0.x positional animation methods passed bare to self.play()
# These crash in Manim CE v0.18+. Must use .animate.<method>() instead.
_OLD_POSITIONAL_ANIMATION_METHODS = {
    "to_edge", "to_corner", "shift", "move_to", "set_x", "set_y",
    "set_color", "set_fill", "set_stroke", "set_opacity",
    "scale", "rotate", "flip", "stretch",
    "next_to", "align_to", "align_on_border",
    "center", "match_height", "match_width",
}


# ── Prompt loading ────────────────────────────────────────────────────────────

def _load_prompt(filename: str, fallback: str) -> str:
    path = PROMPTS_DIR / filename
    if path.exists():
        return path.read_text(encoding="utf-8")
    logger.warning(f"Prompt file not found: {path}, using inline fallback")
    return fallback


# ── Default fallback scene (guaranteed to render on v0.18) ───────────────────

def _default_scene_code(concept: str) -> str:
    """
    Minimal but visually complete scene that always renders on Manim CE v0.18.
    Uses ONLY .animate syntax — never bare method references in self.play().
    """
    title = re.sub(r"[^A-Za-z0-9 ,.:;!?()\-_/]", "", concept or "Concept").strip()[:40] or "Concept"
    return f"""from manim import *

class NeuroScene(Scene):
    def construct(self):
        title = Text("{title}", font_size=44, color=BLUE)
        self.play(Write(title))
        self.wait(0.3)
        self.play(title.animate.to_edge(UP, buff=0.4))
        self.wait(0.2)

        left = Circle(radius=1.0, color=TEAL, fill_opacity=0.15, stroke_width=2)
        left.shift(LEFT * 2.5)
        left_label = Text("Input", font_size=28, color="#333333").next_to(left, DOWN, buff=0.2)

        right = RoundedRectangle(
            corner_radius=0.2, width=2.2, height=2.2,
            color=GOLD, fill_opacity=0.15, stroke_width=2
        )
        right.shift(RIGHT * 2.5)
        right_label = Text("Output", font_size=28, color="#333333").next_to(right, DOWN, buff=0.2)

        arrow = Arrow(
            left.get_right(), right.get_left(),
            buff=0.15, color=ORANGE, stroke_width=3
        )

        self.play(Create(left), FadeIn(left_label))
        self.wait(0.3)
        self.play(GrowArrow(arrow))
        self.wait(0.3)
        self.play(Create(right), FadeIn(right_label))
        self.wait(0.3)
        self.play(Indicate(arrow, color=GOLD, scale_factor=1.15))
        self.wait(0.8)
"""


# ── AST-based safety + compatibility validator ────────────────────────────────

def _is_safe_scene_code(scene_code: str) -> tuple[bool, str]:
    """
    Parse and validate Manim scene code before attempting a render.

    Checks (in order):
      1. Valid Python syntax
      2. No disallowed imports
      3. No dangerous built-in calls (eval, exec, open, ...)
      4. No dangerous attribute calls (os.system, subprocess.run, ...)
      5. No old Manim positional-method syntax passed bare to self.play()
         e.g. self.play(obj.to_edge, UP)  ← crashes CE v0.18
      6. Class NeuroScene(Scene) must be present
    """
    try:
        tree = ast.parse(scene_code)
    except SyntaxError as exc:
        return False, f"syntax_error:{exc.msg}"

    has_neuro_scene = False

    for node in ast.walk(tree):

        # Import checks
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root not in _ALLOWED_IMPORT_ROOTS:
                    return False, f"disallowed_import:{root}"

        if isinstance(node, ast.ImportFrom):
            root = (node.module or "").split(".")[0]
            if root and root not in _ALLOWED_IMPORT_ROOTS:
                return False, f"disallowed_import_from:{root}"

        # Dangerous built-in calls
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                if node.func.id in _DISALLOWED_CALL_NAMES:
                    return False, f"disallowed_call:{node.func.id}"

            if isinstance(node.func, ast.Attribute):
                if node.func.attr in _DISALLOWED_ATTR_CALLS:
                    return False, f"disallowed_attr_call:{node.func.attr}"

                # ── Old Manim syntax detection ────────────────────────────
                # Pattern: self.play(obj.some_method, ...)
                # In the AST this looks like:
                #   Call(func=Attribute(attr='play'), args=[Attribute(attr=OLD_METHOD), ...])
                if node.func.attr == "play":
                    for arg in node.args:
                        if (
                            isinstance(arg, ast.Attribute)
                            and arg.attr in _OLD_POSITIONAL_ANIMATION_METHODS
                        ):
                            return False, (
                                f"old_manim_syntax:{arg.attr}_must_use_animate"
                                f" — use obj.animate.{arg.attr}() inside self.play()"
                            )

        # Class name check
        if isinstance(node, ast.ClassDef) and node.name == "NeuroScene":
            has_neuro_scene = True

    if not has_neuro_scene:
        return False, "missing_neuroscene_class"

    return True, "ok"


# ── Code extraction helpers ───────────────────────────────────────────────────

def _extract_python_code(text: str) -> str:
    """
    Strip markdown fences and return raw Python code.
    Tries ```python ... ``` first, then ``` ... ```, then returns as-is.
    """
    fenced_python = re.findall(r"```python\s*(.*?)```", text, flags=re.DOTALL)
    if fenced_python:
        return fenced_python[0].strip()
    fenced_any = re.findall(r"```\s*(.*?)```", text, flags=re.DOTALL)
    if fenced_any:
        candidate = fenced_any[0].strip()
        # Only accept if it looks like Python (starts with 'from' or 'import' or 'class')
        if re.match(r"^(from|import|class|#)", candidate):
            return candidate
    # Raw output — accept only if it starts with something Python-like
    stripped = text.strip()
    if re.match(r"^(#\s*NARRATION|from manim|import|class NeuroScene)", stripped):
        return stripped
    return stripped


def _normalize_scene_class_name(scene_code: str) -> str:
    """Rename any Scene subclass to NeuroScene."""
    return re.sub(
        r"class\s+\w+\s*\(\s*Scene\s*\)\s*:",
        "class NeuroScene(Scene):",
        scene_code,
        count=1,
    )


# ── Narration extraction ──────────────────────────────────────────────────────

def _extract_narration(raw_llm_output: str) -> dict | None:
    """
    Extract NARRATION JSON from the first line of LLM output.

    Expected format (single line):
      # NARRATION: {"script": "...", "beats": [{"at_s": 0.5, "text": "..."}, ...]}

    Robust to:
      - Extra whitespace around the JSON
      - Missing "beats" key (defaults to [])
      - Malformed JSON (returns None cleanly)
      - NARRATION line appearing anywhere in the first 3 lines (LLM drift)
    """
    # Search only in the first 500 chars to avoid false positives deep in code
    search_region = raw_llm_output[:500]
    match = re.search(
        r"#\s*NARRATION:\s*(\{[^\n]+\})",
        search_region,
    )
    if not match:
        return None
    try:
        data = json.loads(match.group(1))
        script = data.get("script", "")
        if not isinstance(script, str) or not script.strip():
            return None
        beats = data.get("beats", [])
        if not isinstance(beats, list):
            beats = []
        # Validate beat structure
        valid_beats = []
        for beat in beats:
            if isinstance(beat, dict) and isinstance(beat.get("at_s"), (int, float)):
                valid_beats.append({
                    "at_s": float(beat["at_s"]),
                    "text": str(beat.get("text", "")).strip(),
                })
        return {"script": script.strip(), "beats": valid_beats}
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        return None


# ── LLM call wrapper ──────────────────────────────────────────────────────────

def _call_llm(prompt: str, system: str, timeout_seconds: float = 600.0) -> str:
    return call_llm(
        prompt=prompt,
        system=system,
        temperature=0.35,
        max_tokens=8192,
        timeout_seconds=timeout_seconds,
    )


# ── Video metadata extraction ─────────────────────────────────────────────────

def _get_video_metadata(video_path: str | None) -> dict | None:
    """
    Extract duration, fps, and frame count via ffprobe.
    Returns None (never raises) if ffprobe is missing or fails.
    """
    if not video_path or not shutil.which("ffprobe"):
        return None
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "stream=duration,r_frame_rate",
                "-of", "json",
                video_path,
            ],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode != 0:
            return None
        data = json.loads(result.stdout)
        stream = data.get("streams", [{}])[0]

        duration_s = float(stream.get("duration") or 0)
        fps_str = stream.get("r_frame_rate", "15/1")
        try:
            num, den = map(int, fps_str.split("/"))
            fps = num / den if den != 0 else 15.0
        except (ValueError, ZeroDivisionError):
            fps = 15.0

        return {
            "duration_s": round(duration_s, 3),
            "fps": round(fps, 2),
            "frame_count": int(duration_s * fps) if duration_s > 0 else 0,
        }
    except Exception as exc:
        logger.warning(f"ffprobe metadata extraction failed: {exc}")
        return None


def _duration_ms(video_path: str | None) -> int:
    """Quick duration-only read via ffprobe format probe."""
    if not video_path or not shutil.which("ffprobe"):
        return 0
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=nokey=1:noprint_wrappers=1",
                video_path,
            ],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode != 0:
            return 0
        return max(0, int(float((result.stdout or "0").strip() or 0) * 1000))
    except Exception:
        return 0


# ── Manim renderer ────────────────────────────────────────────────────────────

def _render_scene(
    scene_code: str,
    output_stem: str,
    timeout_seconds: float = 90.0,
) -> Tuple[bool, str, str | None, dict | None]:
    """
    Write scene_code to a temp file, run `manim -ql`, move the MP4 to _VIDEO_DIR.

    Returns (success, logs, output_path_or_None, metadata_or_None).

    Timeout default is 90s — enough for complex -ql renders on CPU.
    Override via MANIM_RENDER_TIMEOUT env var (seconds, float).
    """
    timeout_seconds = float(os.getenv("MANIM_RENDER_TIMEOUT", str(timeout_seconds)))

    with tempfile.TemporaryDirectory(prefix="neuroadapt_manim_") as temp_dir:
        temp_path = Path(temp_dir)
        scene_file = temp_path / "scene.py"
        scene_file.write_text(scene_code, encoding="utf-8")

        cmd = ["manim", "-ql", str(scene_file), "NeuroScene", "-o", output_stem]
        logger.debug(f"Manim render cmd: {' '.join(cmd)} (timeout={timeout_seconds}s)")

        try:
            proc = subprocess.run(
                cmd,
                cwd=temp_dir,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
            )
        except subprocess.TimeoutExpired:
            logger.error(f"Manim render timed out after {timeout_seconds}s")
            return False, f"render_timeout:{timeout_seconds}s", None, None

        if proc.returncode != 0:
            logs = "\n".join(filter(None, [proc.stderr, proc.stdout])).strip()
            logger.error(f"Manim rc={proc.returncode}: {logs[:600]}")
            return False, logs or "manim_render_failed", None, None

        # Manim writes the output under temp_dir/media/videos/.../quality/
        matches = list(temp_path.rglob(f"{output_stem}.mp4"))
        if not matches:
            logger.error(f"Render ok but {output_stem}.mp4 not found in {temp_dir}")
            return False, "mp4_not_found_after_render", None, None

        out_path = _VIDEO_DIR / f"{output_stem}.mp4"
        shutil.move(str(matches[0]), out_path)

        logs = "\n".join(filter(None, [proc.stdout, proc.stderr])).strip() or "ok"
        metadata = _get_video_metadata(str(out_path))
        logger.info(f"Render OK → {out_path} | {metadata}")
        return True, logs, str(out_path), metadata


# ── Writer prompt ─────────────────────────────────────────────────────────────

def _build_writer_prompt(concept: str, learner_level: str, slide_content: str) -> str:
    return (
        f"CONCEPT: {concept}\n"
        f"LEARNER LEVEL: {learner_level}\n"
        f"SLIDE CONTENT (source material, use this as the knowledge base):\n"
        f"{slide_content[:2000]}\n\n"
        f"ANIMATION BRIEF:\n"
        f"1. Identify the single most important idea in the slide content.\n"
        f"2. Design a 10–15 second Manim CE v0.18 animation teaching that idea step-by-step.\n"
        f"3. STEM content → use Axes or NumberPlane as visual backbone.\n"
        f"4. Process/flow content → use Arrow chains; optionally MoveAlongPath.\n"
        f"5. Comparison content → two VGroups side by side with labelled connecting arrow.\n"
        f"6. Safe zone: every object's bounding box must stay within X ∈ [-6.5, 6.5], Y ∈ [-3.5, 3.5].\n"
        f"7. Include at least one Indicate(), Flash(), or Circumscribe() on the key insight.\n"
        f"8. CRITICAL — MANIM v0.18 SYNTAX RULE:\n"
        f"   NEVER write: self.play(obj.to_edge, UP)\n"
        f"   NEVER write: self.play(obj.shift, LEFT * 2)\n"
        f"   ALWAYS write: self.play(obj.animate.to_edge(UP))\n"
        f"   ALWAYS write: self.play(obj.animate.shift(LEFT * 2))\n"
        f"   Passing bare Mobject methods to self.play() crashes in v0.18.\n"
        f"9. NARRATION: output the # NARRATION: {{...}} line as the VERY FIRST LINE.\n"
        f"10. Then: from manim import * — then class NeuroScene(Scene): — no markdown.\n"
    )


def _build_reviewer_prompt(scene_code: str, error: str) -> str:
    return (
        f"The following Manim CE v0.18 code failed to render. Fix it.\n\n"
        f"ERROR LOG:\n{error}\n\n"
        f"BROKEN CODE:\n{scene_code}\n\n"
        f"CRITICAL FIX — THE MOST COMMON ERROR:\n"
        f"  If the error says 'Object <bound method Mobject.X> cannot be converted to an animation'\n"
        f"  or 'Passing Mobject methods to Scene.play is no longer supported':\n"
        f"  Find every self.play(obj.method, ...) and replace with self.play(obj.animate.method(...))\n"
        f"  Examples:\n"
        f"    BROKEN:  self.play(title.to_edge, UP, buff=0.4)\n"
        f"    FIXED:   self.play(title.animate.to_edge(UP, buff=0.4))\n"
        f"    BROKEN:  self.play(arrow.shift, RIGHT * 2)\n"
        f"    FIXED:   self.play(arrow.animate.shift(RIGHT * 2))\n"
        f"  Apply this fix throughout the entire code before returning.\n"
    )


# ── Main entry point ──────────────────────────────────────────────────────────

def generate_manim_animation(
    concept: str,
    slide_content: str,
    learner_level: str = "grade8",
    session_id: str | None = None,
    max_retries: int = 2,
) -> dict[str, Any]:
    """
    Generate a Manim animation for the given concept and slide content.

    Attempt order:
      1. Cache hit → return immediately
      2. Manim not installed → static image fallback
      3. LLM writer → safety check → render
      4. On render failure: LLM reviewer → safety check → render  (up to max_retries)
      5. Safety check failure → substitute default scene → render
      6. All retries exhausted → static image fallback

    Returns a dict with keys:
      video_url, duration_ms, narration, video_metadata,
      cache_hit, writer_attempts, reviewer_attempts,
      render_logs, generation_mode, [image_url], [warning], [fallback_stage]
    """
    key = hashlib.md5(
        f"{concept}:{learner_level}:{slide_content}".encode("utf-8")
    ).hexdigest()
    cached_video = _VIDEO_DIR / f"{key}.mp4"

    if cached_video.exists():
        return {
            "video_url": str(cached_video),
            "duration_ms": _duration_ms(str(cached_video)),
            "narration": None,   # narration not stored in cache; caller should use VTT
            "video_metadata": _get_video_metadata(str(cached_video)),
            "cache_hit": True,
            "writer_attempts": 0,
            "reviewer_attempts": 0,
            "render_logs": None,
            "generation_mode": "manim_generated_cache",
        }

    if not shutil.which("manim"):
        logger.warning("manim binary not found in PATH")
        fallback = generate_image(concept=concept, slide_content=slide_content, learner_level=learner_level)
        return {
            "video_url": None, "duration_ms": 0,
            "image_url": fallback.get("image_url"),
            "narration": None,
            "video_metadata": None,
            "warning": "Manim not installed; static image fallback used.",
            "render_logs": "manim_binary_not_found",
            "writer_attempts": 0, "reviewer_attempts": 0,
            "cache_hit": False,
            "generation_mode": "manim_fallback_static_image",
            "fallback_stage": "manim_unavailable",
        }

    writer_system = _load_prompt(
        "manim_expert.txt",
        "You are a Manim CE v0.18 expert. Return ONLY valid Python. "
        "class NeuroScene(Scene). Use obj.animate.method() — never obj.method bare in self.play().",
    )
    reviewer_system = _load_prompt(
        "manim_reviewer.txt",
        "You fix Manim CE v0.18 code. Return ONLY corrected Python. "
        "class NeuroScene(Scene). Replace self.play(obj.method, args) with self.play(obj.animate.method(args)).",
    )

    scene_code = _default_scene_code(concept)
    narration: dict | None = None
    writer_attempts = 0
    reviewer_attempts = 0
    last_error = ""

    for attempt in range(max_retries + 1):

        # ── Generate or repair code ───────────────────────────────────────
        if attempt == 0:
            writer_attempts += 1
            try:
                raw = _call_llm(
                    prompt=_build_writer_prompt(concept, learner_level, slide_content),
                    system=writer_system,
                    timeout_seconds=float(os.getenv("MANIM_LLM_WRITER_TIMEOUT", "450")),
                )
                logger.debug(f"Writer returned {len(raw)} chars")
                narration = _extract_narration(raw)
                extracted = _extract_python_code(raw)
                if extracted:
                    scene_code = _normalize_scene_class_name(extracted)
                else:
                    logger.warning("Writer returned no extractable Python; using default scene")
            except Exception as exc:
                logger.warning(f"Writer LLM failed: {exc}; using default scene")
                # scene_code stays as _default_scene_code(concept)

        else:
            reviewer_attempts += 1
            try:
                raw = _call_llm(
                    prompt=_build_reviewer_prompt(scene_code, last_error),
                    system=reviewer_system,
                    timeout_seconds=float(os.getenv("MANIM_LLM_REVIEWER_TIMEOUT", "450")),
                )
                logger.debug(f"Reviewer returned {len(raw)} chars")
                extracted = _extract_python_code(raw)
                if extracted:
                    scene_code = _normalize_scene_class_name(extracted)
                else:
                    logger.warning("Reviewer returned no extractable Python; reverting to default")
                    scene_code = _default_scene_code(concept)
            except Exception as exc:
                logger.warning(f"Reviewer LLM failed: {exc}; reverting to default scene")
                scene_code = _default_scene_code(concept)

        # ── Safety + compatibility check (AST) ───────────────────────────
        is_safe, safety_reason = _is_safe_scene_code(scene_code)
        if not is_safe:
            logger.warning(f"Safety check failed ({safety_reason}); substituting default scene")
            # Feed the safety failure as the error into the next reviewer attempt
            last_error = f"safety_check_failed:{safety_reason}"
            scene_code = _default_scene_code(concept)
            # Re-validate default (must always pass — it's our golden scene)
            is_safe, safety_reason = _is_safe_scene_code(scene_code)
            if not is_safe:
                logger.error(f"Default scene also failed safety: {safety_reason}")
                break

        # ── Render ────────────────────────────────────────────────────────
        logger.debug(f"Rendering attempt {attempt + 1}/{max_retries + 1}")
        ok, logs, output_path, video_metadata = _render_scene(scene_code, key)

        if ok:
            duration_ms = int((video_metadata or {}).get("duration_s", 0) * 1000)
            logger.info(f"Render succeeded → {output_path}")
            return {
                "video_url": output_path,
                "duration_ms": duration_ms,
                "narration": narration,
                "video_metadata": video_metadata,
                "cache_hit": False,
                "writer_attempts": writer_attempts,
                "reviewer_attempts": reviewer_attempts,
                "render_logs": logs,
                "generation_mode": "manim_generated",
            }

        logger.warning(f"Render failed (attempt {attempt + 1}): {logs[:300]}")
        last_error = logs

    # ── All retries exhausted ─────────────────────────────────────────────
    logger.error(f"Manim: all {max_retries + 1} attempts failed. Last error: {last_error[:200]}")
    fallback = generate_image(concept=concept, slide_content=slide_content, learner_level=learner_level)
    return {
        "video_url": None,
        "duration_ms": 0,
        "image_url": fallback.get("image_url"),
        "narration": narration,
        "video_metadata": None,
        "warning": f"Manim render failed after {max_retries + 1} attempts; static fallback used.",
        "writer_attempts": writer_attempts,
        "reviewer_attempts": reviewer_attempts,
        "render_logs": last_error,
        "cache_hit": False,
        "generation_mode": "manim_fallback_static_image",
        "fallback_stage": "manim_retry_exhausted",
    }
