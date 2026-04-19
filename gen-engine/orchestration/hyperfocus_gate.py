"""Hyperfocus protective gate logic."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Any, Dict, Tuple

ENTER_THRESHOLD = 0.75
EXIT_THRESHOLD = 0.60
MIN_EXIT_STABLE_SECONDS = 30.0


@dataclass
class _SessionState:
    active: bool = False
    activated_at: float = 0.0
    below_exit_since: float | None = None
    last_composite: float = 0.0


_SESSION_STATES: Dict[str, _SessionState] = {}
_SESSION_LOCK = threading.Lock()


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, float(value)))


def compute_hyperfocus_composite(state_vector: Dict[str, Any]) -> float:
    """
    Compute a composite score from available state fields.
    Priority order:
    1) If documented 5-signal inputs are present, compute weighted composite.
    2) Else use provided hyperfocus value if available.
    3) Else compute backward-compatible proxy blend.
    """
    required_signals = {
        "idle_time",
        "keystroke_cv",
        "gaze_dispersion",
        "scroll_velocity",
        "session_duration",
        "learner_avg_duration",
    }

    if required_signals.issubset(state_vector.keys()):
        idle_time = max(0.0, float(state_vector.get("idle_time", 0.0)))
        keystroke_cv = max(0.0, float(state_vector.get("keystroke_cv", 1.0)))
        gaze_dispersion = max(0.0, float(state_vector.get("gaze_dispersion", 1.0)))
        scroll_velocity = float(state_vector.get("scroll_velocity", 0.0))
        session_duration = max(0.0, float(state_vector.get("session_duration", 0.0)))
        learner_avg_duration = max(0.0, float(state_vector.get("learner_avg_duration", 0.0)))

        scores = [
            1.0 if idle_time < 2.0 else 0.0,
            1.0 if keystroke_cv < 0.3 else 0.0,
            1.0 if gaze_dispersion < 0.15 else 0.0,
            1.0 if abs(scroll_velocity) < 0.05 else 0.0,
            1.0
            if learner_avg_duration > 0 and session_duration > (learner_avg_duration * 1.5)
            else 0.0,
        ]
        weights = [0.25, 0.20, 0.30, 0.15, 0.10]
        composite = sum(weight * score for weight, score in zip(weights, scores))
        return _clamp(composite)

    direct = state_vector.get("hyperfocus_composite")
    if direct is not None:
        return _clamp(direct)

    attention_switching = _clamp(state_vector.get("attention_switching", 0.5))
    engagement = _clamp(state_vector.get("engagement_level", 0.5))
    micro_pause = _clamp(state_vector.get("micro_pause_ratio", 0.5))

    time_on_task = max(0.0, float(state_vector.get("time_on_task", 0.0)))
    time_bonus = min(1.0, time_on_task / 1800.0)  # full bonus at ~30 minutes

    composite = (
        0.4 * (1.0 - attention_switching)
        + 0.3 * engagement
        + 0.2 * (1.0 - micro_pause)
        + 0.1 * time_bonus
    )
    return _clamp(composite)


def check_hyperfocus(session_id: str, state_vector: Dict[str, Any]) -> Tuple[bool, float, str]:
    """
    Return `(should_preempt, composite, reason)`.

    Behavior:
    - Enter preemption at composite >= ENTER_THRESHOLD.
    - Stay in preemption until composite < EXIT_THRESHOLD for MIN_EXIT_STABLE_SECONDS.
    """
    now = time.time()
    composite = compute_hyperfocus_composite(state_vector)

    with _SESSION_LOCK:
        session = _SESSION_STATES.setdefault(session_id, _SessionState())
        session.last_composite = composite

        if not session.active:
            if composite >= ENTER_THRESHOLD:
                session.active = True
                session.activated_at = now
                session.below_exit_since = None
                return True, composite, "hyperfocus_entered"
            return False, composite, "normal_flow"

        # Already active preemption mode.
        if composite < EXIT_THRESHOLD:
            if session.below_exit_since is None:
                session.below_exit_since = now
                return True, composite, "hyperfocus_hold_exit_timer_started"

            stable_duration = now - session.below_exit_since
            if stable_duration >= MIN_EXIT_STABLE_SECONDS:
                session.active = False
                session.activated_at = 0.0
                session.below_exit_since = None
                return False, composite, "hyperfocus_exited"

            return True, composite, "hyperfocus_hold_exit_timer_running"

        # Composite rose again; remain in protected mode.
        session.below_exit_since = None
        return True, composite, "hyperfocus_active"


def clear_session(session_id: str) -> None:
    with _SESSION_LOCK:
        _SESSION_STATES.pop(session_id, None)
