"""
Hyperfocus Protective Gate — Pre-emption Logic to Preserve Flow States

================================================================================
PURPOSE:
    Detects rare ADHD hyperfocus states (high productivity).
    Blocks ALL interventions when hyperfocus is active (protect flow).
    Overrides orchestrator decision to action_id = 0 (hold course).

DEPENDENCIES:
    - None (pure logic/computation)

INPUT:
    state_vector: dict
    {
        "hyperfocus_composite": float (0.0-1.0),
        "attention_switching": float,
        "regression_count": int,
        "task_engagement": float,
        "time_on_task": int (seconds),
        ...
    }

HYPERFOCUS COMPOSITE CALCULATION:
    hyperfocus_composite = (
        0.4 * (1 - attention_switching) +    # Low task-switching
        0.3 * engagement_level +              # High engagement
        0.2 * (1 - micro_pause_ratio) +       # Few breaks
        0.1 * time_on_task_bonus              # Sustained duration
    )
    
    Range: 0.0 (no hyperfocus) to 1.0 (complete hyperfocus)

DETECTION THRESHOLD:
    hyperfocus_composite > 0.75 → Hyperfocus ACTIVE
    
    Interpretation:
    - < 0.3: No hyperfocus, normal intervention mode
    - 0.3-0.6: Partial attention (allow interventions)
    - 0.6-0.75: Deep focus (caution, allow light interventions)
    - > 0.75: HYPERFOCUS (protect at all costs, no interventions)

RESEARCH BASIS:
    - Russell Barkley: Hyperfocus is rare ADHD strength (not impairment)
    - Can last 2-4 hours if uninterrupted
    - Interruptions reset hyperfocus state (90+ minute recovery)
    - Protecting hyperfocus → major productivity gains
    - Nadeau: "Honor the hyperfocus"

BEHAVIOR:
    IF hyperfocus_composite > 0.75:
        → Pre-emption: Override action_id to 0
        → Block ALL UI changes (no content interventions)
        → No audio, no visual changes, no quizzes
        → Learner sees "In Flow" indicator only
        → Continue passive monitoring (don't lose state_vector)
        → EXIT pre-emption only when:
            - hyperfocus_composite < 0.60 (for 30+ seconds)
            - Explicit learner "break" button clicked
            - Session timeout (> 2 hours without break)

PROTECTION WINDOW:
    Once hyperfocus detected:
    1. Activate "do not disturb" mode (30+ second confirmation window)
    2. Only exit if hyperfocus_composite < 0.60 for sustained period
    3. Gradually re-enable interventions as composite drops

OPTIONAL UI FEEDBACK:
    - Display "In Flow" badge (subtle, non-intrusive)
    - Show estimated time until re-engagement possible
    - Offer "Break?" button (optional)
    - Log hyperfocus episodes for learner insight

EDGE CASES:
    - High engagement but multiple regressions → Not true hyperfocus
    - Hyperfocus detection but < 30 seconds → Ignore (too brief)
    - Rapid on/off cycles → Indicate distractibility, not true hyperfocus
    - Gaming vs. learning → Same logic applies

LOGGING:
    - Hyperfocus activation: timestamp, duration, composite score
    - Pre-empted actions: what would have been sent (for analytics)
    - Exit reason: dropped composite vs. explicit break

METRICS:
    - Count of hyperfocus episodes
    - Average duration per episode
    - Pre-emption count per session
    - Sessions with at least one hyperfocus episode

KEY FUNCTIONS:
    - check_hyperfocus(state_vector) → bool
    - get_hyperfocus_composite(state_vector) → float
    - should_pre_empt(hyperfocus_composite, current_pre_emption_state) → bool
    - get_pre_emption_exit_criteria(initial_composite, duration) → dict

ERROR HANDLING:
    - Missing state_vector fields: Use conservative defaults (0.0)
    - Invalid composite scores: Clamp to [0, 1]
    - Return valid pre-emption decision (default to no pre-emption)

CONSTRAINTS:
    - Execution: < 1ms (instant)
    - No external I/O
    - Deterministic

INTEGRATION:
    - Called by action_router BEFORE routing
    - If pre-empt: Override action_id to 0, skip generator calls
    - Called by latency_budget for pre-emption window tracking
    - Results logged to PostgreSQL session table

RELATED:
    - action_router : Uses pre-emption decision
    - latency_budget : Tracks pre-emption window duration
    - Frontend : Displays "In Flow" badge

================================================================================
"""

from __future__ import annotations

import time
from typing import Any, Dict


HYPERFOCUS_THRESHOLD = 0.75
HYPERFOCUS_EXIT_THRESHOLD = 0.60
MIN_PREEMPTION_SECONDS = 30
MAX_PREEMPTION_SECONDS = 2 * 60 * 60

# session_id -> timestamp of pre-emption start
_PREEMPTION_STATE: Dict[str, float] = {}


def _clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, value))


def get_hyperfocus_composite(state_vector: Dict[str, Any]) -> float:
    """Compute a stable hyperfocus composite from the available state fields."""
    state = state_vector or {}

    if "hyperfocus_composite" in state:
        try:
            return _clamp(float(state["hyperfocus_composite"]))
        except Exception:
            pass

    attention_switching = _clamp(float(state.get("attention_switching", 0.5)))
    engagement_level = _clamp(float(state.get("task_engagement", 0.5)))
    micro_pause_ratio = _clamp(float(state.get("micro_pause_ratio", 0.4)))
    time_on_task = max(0.0, float(state.get("time_on_task", 0.0)))
    time_on_task_bonus = _clamp(time_on_task / 1800.0)  # bonus saturates at ~30 min

    composite = (
        0.4 * (1.0 - attention_switching)
        + 0.3 * engagement_level
        + 0.2 * (1.0 - micro_pause_ratio)
        + 0.1 * time_on_task_bonus
    )
    return _clamp(composite)


def check_hyperfocus(state_vector: Dict[str, Any]) -> bool:
    """One-shot threshold check for hyperfocus."""
    return get_hyperfocus_composite(state_vector) >= HYPERFOCUS_THRESHOLD


def should_pre_empt(
    session_id: str,
    state_vector: Dict[str, Any],
    explicit_break: bool = False,
    now: float | None = None,
) -> bool:
    """
    Decide whether to route to action_id=0 to protect hyperfocus.

    Hysteresis:
    - Enter at >= 0.75
    - Stay pre-empted for at least 30 seconds
    - Exit at < 0.60 (after minimum window) or max window expiration
    """
    if not session_id:
        return False

    current_time = now if now is not None else time.time()

    if explicit_break:
        _PREEMPTION_STATE.pop(session_id, None)
        return False

    score = get_hyperfocus_composite(state_vector)
    start_time = _PREEMPTION_STATE.get(session_id)

    if start_time is None:
        if score >= HYPERFOCUS_THRESHOLD:
            _PREEMPTION_STATE[session_id] = current_time
            return True
        return False

    elapsed = current_time - start_time
    if elapsed < MIN_PREEMPTION_SECONDS:
        return True

    if elapsed > MAX_PREEMPTION_SECONDS or score < HYPERFOCUS_EXIT_THRESHOLD:
        _PREEMPTION_STATE.pop(session_id, None)
        return False

    return True


def reset_pre_emption(session_id: str) -> None:
    """Clear any pre-emption state for a session."""
    if session_id:
        _PREEMPTION_STATE.pop(session_id, None)
