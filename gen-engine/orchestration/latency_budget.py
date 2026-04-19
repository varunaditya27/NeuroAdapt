"""Latency budget and timeout helpers for generators."""

from __future__ import annotations

import os
import queue
import threading
import time
from typing import Any, Callable, Dict, Tuple

_TIMEOUTS = {
    "text_simplify": float(os.getenv("LATENCY_BUDGET_TEXT_SIMPLIFY", "5")),
    "analogy": float(os.getenv("LATENCY_BUDGET_ANALOGY", "3")),
    "quiz": float(os.getenv("LATENCY_BUDGET_QUIZ", "4")),
    "audio": float(os.getenv("LATENCY_BUDGET_AUDIO", "3")),
    "image": float(os.getenv("LATENCY_BUDGET_IMAGE", "12")),
    "manim": float(os.getenv("LATENCY_BUDGET_MANIM", "45")),
    "avatar": float(os.getenv("LATENCY_BUDGET_AVATAR", "20")),
}

_DEFAULT_TIMEOUT = 5.0


def get_timeout_seconds(kind: str) -> float:
    return max(0.1, float(_TIMEOUTS.get(kind, _DEFAULT_TIMEOUT)))


def fallback_for(kind: str, original_text: str = "") -> Dict[str, Any]:
    if kind == "text_simplify":
        return {
            "simplified_text": original_text,
            "warning": "Text simplification timed out; served original text.",
            "fallback_stage": "text_simplify_timeout",
            "generation_mode": "text_fallback",
        }
    if kind == "quiz":
        return {
            "quiz_json": [
                {
                    "id": 1,
                    "text": "Which option best matches the main idea?",
                    "options": [
                        "It introduces the topic",
                        "It disproves the topic",
                        "It is unrelated",
                        "It is random detail",
                    ],
                    "correct_index": 0,
                    "difficulty": "easy",
                }
            ],
            "warning": "Quiz generation timed out; served fallback quiz.",
            "fallback_stage": "quiz_timeout",
            "generation_mode": "quiz_fallback",
        }
    if kind in {"image", "manim", "avatar", "audio", "analogy"}:
        return {
            "warning": f"{kind} generation timed out; fallback content applied.",
            "fallback_stage": f"{kind}_timeout",
            "generation_mode": f"{kind}_fallback",
        }
    return {
        "warning": "Generation timed out; fallback content applied.",
        "fallback_stage": "unknown_timeout",
        "generation_mode": "generic_fallback",
    }


def run_with_timeout(
    func: Callable[..., Dict[str, Any]],
    timeout_seconds: float,
    *args: Any,
    **kwargs: Any,
) -> Tuple[Dict[str, Any], bool, int, str | None]:
    """
    Execute a synchronous callable with timeout.

    Returns: (result, timed_out, elapsed_ms, error)
    """
    start = time.perf_counter()

    result_queue: queue.Queue[Tuple[str, Any]] = queue.Queue(maxsize=1)

    def _target() -> None:
        try:
            result_queue.put(("result", func(*args, **kwargs)))
        except Exception as exc:  # pragma: no cover - depends on generator impl
            result_queue.put(("error", exc))

    thread = threading.Thread(target=_target, daemon=True, name="latency-budget-worker")
    thread.start()
    thread.join(timeout=max(0.1, timeout_seconds))

    elapsed_ms = int((time.perf_counter() - start) * 1000)
    if thread.is_alive():
        return {}, True, elapsed_ms, "timeout"

    try:
        tag, payload = result_queue.get_nowait()
    except queue.Empty:  # pragma: no cover - defensive
        return {}, False, elapsed_ms, "worker_no_result"

    if tag == "error":
        return {}, False, elapsed_ms, str(payload)

    if isinstance(payload, dict):
        return payload, False, elapsed_ms, None

    return {"result": payload}, False, elapsed_ms, None


def latency_budget(
    timeout_seconds: float,
    fallback_builder: Callable[..., Dict[str, Any]] | None = None,
) -> Callable[[Callable[..., Dict[str, Any]]], Callable[..., Dict[str, Any]]]:
    """Decorator wrapper for optional direct use in generators."""

    def decorator(func: Callable[..., Dict[str, Any]]) -> Callable[..., Dict[str, Any]]:
        def wrapped(*args: Any, **kwargs: Any) -> Dict[str, Any]:
            result, timed_out, _, error = run_with_timeout(func, timeout_seconds, *args, **kwargs)
            if timed_out:
                if fallback_builder:
                    return fallback_builder(*args, **kwargs)
                return {"warning": "Operation timed out."}
            if error:
                if fallback_builder:
                    fallback = fallback_builder(*args, **kwargs)
                    fallback["warning"] = f"Operation failed: {error}"
                    return fallback
                return {"warning": f"Operation failed: {error}"}
            return result

        return wrapped

    return decorator
