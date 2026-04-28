from __future__ import annotations

from orchestration import hyperfocus_gate as hg


def test_direct_composite_threshold_entry():
    session_id = "test-session-enter"
    hg.clear_session(session_id)

    should_preempt, composite, reason = hg.check_hyperfocus(
        session_id,
        {"hyperfocus_composite": 0.75},
    )

    assert should_preempt is True
    assert composite == 0.75
    assert reason == "hyperfocus_entered"


def test_below_threshold_no_preemption():
    session_id = "test-session-below"
    hg.clear_session(session_id)

    should_preempt, composite, reason = hg.check_hyperfocus(
        session_id,
        {"hyperfocus_composite": 0.74},
    )

    assert should_preempt is False
    assert composite == 0.74
    assert reason == "normal_flow"


def test_composite_fallback_calculation():
    score = hg.compute_hyperfocus_composite(
        {
            "attention_switching": 0.2,
            "engagement_level": 0.9,
            "micro_pause_ratio": 0.05,
            "time_on_task": 1800,
        }
    )
    assert score >= 0.75


def test_documented_five_signal_composite_path():
    score = hg.compute_hyperfocus_composite(
        {
            "idle_time": 1.0,
            "keystroke_cv": 0.2,
            "gaze_dispersion": 0.1,
            "scroll_velocity": 0.02,
            "session_duration": 1800,
            "learner_avg_duration": 900,
        }
    )
    assert score == 1.0

    should_preempt, composite, _ = hg.check_hyperfocus(
        "test-session-five-signal",
        {
            "idle_time": 1.0,
            "keystroke_cv": 0.2,
            "gaze_dispersion": 0.1,
            "scroll_velocity": 0.02,
            "session_duration": 1800,
            "learner_avg_duration": 900,
        },
    )
    assert should_preempt is True
    assert composite == 1.0


def test_preemption_exit_requires_stable_window(monkeypatch):
    session_id = "test-session-window"
    hg.clear_session(session_id)

    now = {"t": 1000.0}
    monkeypatch.setattr(hg.time, "time", lambda: now["t"])

    # Enter preemption
    assert hg.check_hyperfocus(session_id, {"hyperfocus_composite": 0.9})[0] is True

    # Drops below exit threshold, timer starts but should still preempt.
    now["t"] = 1005.0
    assert hg.check_hyperfocus(session_id, {"hyperfocus_composite": 0.55})[0] is True

    # Still within hold window.
    now["t"] = 1029.0
    assert hg.check_hyperfocus(session_id, {"hyperfocus_composite": 0.58})[0] is True

    # After 30s under threshold, preemption exits.
    now["t"] = 1036.0
    assert hg.check_hyperfocus(session_id, {"hyperfocus_composite": 0.55})[0] is False
