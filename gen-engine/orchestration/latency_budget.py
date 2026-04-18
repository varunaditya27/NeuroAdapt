"""
Latency Budget — Per-Modality Timeouts + Graceful Fallback Chain

================================================================================
PURPOSE:
    Enforce hard timeouts on each generator/modality.
    When generation exceeds budget: Gracefully fallback instead of blocking.
    Learner never waits more than target latency (+ 2s buffer).

DEPENDENCIES:
    - asyncio : Timeout management
    - tenacity : Retry decorator with deadline
    - functools : Decorator implementation

LATENCY BUDGETS (from README):
    Modality | Target | Hard Timeout | Fallback
    ---|---|---|---
    Text simplification (Gemma 4 E2B local) | < 3s | 5s | Serve original text
    Analogy generation (Gemma 4 E2B) | < 2s | 3s | Skip analogy
    Audio TTS (Kokoro) | < 2s | 3s | Serve text only
    Image generation (Stable Diffusion) | < 8s | 12s | Serve text + audio
    Manim animation (local render) | < 30s | 45s | Serve static image + audio
    LivePortrait avatar (local) | < 15s | 20s | Serve illustrated narrative

DECORATOR USAGE:
    @latency_budget(action_id=2, timeout_seconds=5, fallback_strategy="original_text")
    def simplify_text(text: str) -> dict:
        # Implementation
        return {...}

ALGORITHM:
    1. Start timer (wall clock)
    2. Execute wrapped function in thread with timeout
    3. If timeout exceeded:
        a. Signal function to cancel
        b. Apply fallback strategy
        c. Return partial/cached result
    4. If timeout NOT exceeded:
        a. Return result
        b. Record latency metric
    5. Always return response (never crash/timeout to user)

FALLBACK STRATEGIES:
    "original_text" : Return original text (no change)
    "skip_modality" : Omit this modality from response
    "cached_result" : Return last cached result for this concept
    "placeholder" : Return empty/default value
    "hardcoded_template" : Return pre-built fallback (for quizzes)

TIMEOUT SIGNAL HANDLING:
    - Python threading: Send signal to thread (no true cancellation)
    - asyncio: Use asyncio.wait_for() + cancel()
    - Subprocess: Use subprocess.Popen() + timeout + kill
    - LLM calls: Add hard deadline to Ollama request

HYPERFOCUS PROTECTION:
    - If in hyperfocus pre-emption window:
        → Override all timeouts to 0 (don't call generator)
        → Return action_id = 0 immediately

PRE-EMPTION WINDOW TRACKING:
    - When hyperfocus gate triggers pre-emption
    - Start timer for pre-emption window
    - Keep pre-emption active for 30+ seconds minimum
    - Exit when hyperfocus_composite < 0.6 for sustained period
    - latency_budget respects pre-emption (skips all Tier 2/3)

ADAPTIVE TIMEOUT (Optional Future Enhancement):
    - Track learner's past generation times
    - If consistently fast: Reduce timeout
    - If frequently timeout: Increase fallback likelihood
    - Personalize by learner speed profile

CASCADING FALLBACKS:
    For complex multi-step requests (e.g., animation + narration):
    1. Manim animation (45s timeout)
        → Fail: Try static image (12s timeout)
        → Fail: Serve text only
    2. Kokoro TTS (3s timeout)
        → Fail: Serve text only
    3. LivePortrait (20s timeout)
        → Fail: Serve audio only

MONITORING:
    - Latency histogram by action_id
    - Timeout rate by modality
    - Fallback rate by strategy
    - Timeout frequency trends

KEY FUNCTIONS:
    - @latency_budget(action_id, timeout_seconds, fallback_strategy)
    - get_timeout_for_action(action_id) → float
    - get_fallback_strategy(action_id) → str
    - apply_fallback(action_id, fallback_strategy, original_input) → dict
    - measure_actual_latency(action_id, actual_ms) → None

ERROR HANDLING:
    - Timeout signal unresponsive: Force kill process
    - Fallback function errors: Return minimal default
    - Negative latency: Log warning, treat as 0
    - All fallbacks fail: Return error response to user

CONSTRAINTS:
    - Hard timeout: Never block > target + 2s buffer
    - Fallback generation: Must be instant (< 100ms)
    - No recursive timeouts (only one deadline per request)

INTEGRATION:
    - Decorates all generator functions
    - Called by action_router
    - Results logged to PostgreSQL
    - Metrics sent to Prometheus

CONFIGURATION (environment):
    - LATENCY_BUDGET_TEXT_SIMPLIFY : Default 5s
    - LATENCY_BUDGET_IMAGE_GEN : Default 12s
    - LATENCY_BUDGET_MANIM : Default 45s
    - LATENCY_BUDGET_AUDIO : Default 3s
    - LATENCY_BUDGET_AVATAR : Default 20s

RELATED:
    - action_router : Wraps all generator calls with decorator
    - hyperfocus_gate : Pre-emption affects timeout decisions
    - prefetch_manager : May complete before timeout
    - All generators : Decorated with @latency_budget

================================================================================
"""

from __future__ import annotations

import asyncio
import functools
import inspect
import os
import time
from typing import Any, Awaitable, Callable, Dict, Optional, Tuple


ACTION_TIMEOUTS: Dict[int, float] = {
    0: 0.5,
    1: 1.0,
    2: float(os.getenv("LATENCY_BUDGET_TEXT_SIMPLIFY", "5")),
    3: float(os.getenv("LATENCY_BUDGET_MANIM", "45")),
    4: 5.0,
    5: 1.0,
}

ACTION_FALLBACKS: Dict[int, str] = {
    0: "skip_modality",
    1: "original_text",
    2: "original_text",
    3: "skip_modality",
    4: "hardcoded_template",
    5: "placeholder",
}


def get_timeout_for_action(action_id: int) -> float:
    return max(0.1, ACTION_TIMEOUTS.get(action_id, 5.0))


def get_fallback_strategy(action_id: int) -> str:
    return ACTION_FALLBACKS.get(action_id, "placeholder")


def apply_fallback(
    action_id: int,
    fallback_strategy: str,
    original_input: Optional[Any] = None,
) -> Dict[str, Any]:
    """Return deterministic fallback payload for a failed/timed-out generation."""
    if fallback_strategy == "original_text":
        return {
            "simplified_text": original_input if isinstance(original_input, str) else "",
            "chunks": [],
            "cache_hit": False,
            "warning": "Returned original text due to timeout/failure.",
        }
    if fallback_strategy == "skip_modality":
        return {
            "skipped": True,
            "cache_hit": False,
            "warning": "Skipped modality due to timeout/failure.",
        }
    if fallback_strategy == "hardcoded_template":
        return {
            "quiz_json": [
                {
                    "id": 1,
                    "text": "Quick check: Which option best matches the current concept?",
                    "options": ["Option A", "Option B", "Option C", "Option D"],
                    "correct_index": 0,
                    "difficulty": "easy",
                }
            ],
            "mastery_level": "moderate",
            "estimated_time_seconds": 60,
            "cache_hit": False,
            "warning": "Returned template quiz due to timeout/failure.",
        }
    return {
        "cache_hit": False,
        "warning": "Returned placeholder due to timeout/failure.",
    }


async def _invoke_callable(func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    if inspect.iscoroutinefunction(func):
        return await func(*args, **kwargs)
    return await asyncio.to_thread(func, *args, **kwargs)


async def execute_with_timeout(
    func: Callable[..., Any],
    *args: Any,
    action_id: int,
    timeout_seconds: Optional[float] = None,
    fallback_strategy: Optional[str] = None,
    fallback_value: Optional[Any] = None,
    **kwargs: Any,
) -> Tuple[Any, Optional[str], Optional[str], int]:
    """
    Execute a callable with an action-specific timeout.

    Returns:
        (result, error, warning, latency_ms)
    """
    start = time.perf_counter()
    timeout = timeout_seconds or get_timeout_for_action(action_id)
    strategy = fallback_strategy or get_fallback_strategy(action_id)

    try:
        result = await asyncio.wait_for(_invoke_callable(func, *args, **kwargs), timeout=timeout)
        latency_ms = int((time.perf_counter() - start) * 1000)
        return result, None, None, latency_ms
    except asyncio.TimeoutError:
        latency_ms = int((time.perf_counter() - start) * 1000)
        warning = f"Generation timed out after {timeout:.2f}s; fallback '{strategy}' applied."
        fallback = fallback_value if fallback_value is not None else apply_fallback(action_id, strategy, args[0] if args else None)
        return fallback, "timeout", warning, latency_ms
    except Exception as exc:
        latency_ms = int((time.perf_counter() - start) * 1000)
        warning = f"Generation failed; fallback '{strategy}' applied."
        fallback = fallback_value if fallback_value is not None else apply_fallback(action_id, strategy, args[0] if args else None)
        return fallback, f"generator_error: {exc}", warning, latency_ms


def latency_budget(
    action_id: int,
    timeout_seconds: Optional[float] = None,
    fallback_strategy: Optional[str] = None,
):
    """Decorator wrapper that enforces latency budgets on generator functions."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Awaitable[Any]]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            result, error, warning, _latency_ms = await execute_with_timeout(
                func,
                *args,
                action_id=action_id,
                timeout_seconds=timeout_seconds,
                fallback_strategy=fallback_strategy,
                **kwargs,
            )
            if isinstance(result, dict):
                if warning and not result.get("warning"):
                    result["warning"] = warning
                if error and not result.get("error"):
                    result["error"] = error
            return result

        return wrapper

    return decorator
