from __future__ import annotations

import time

from orchestration.latency_budget import fallback_for, run_with_timeout
from orchestration.prefetch_manager import PrefetchManager


def test_run_with_timeout_triggers_timeout():
    def slow_fn():
        time.sleep(0.2)
        return {"ok": True}

    result, timed_out, elapsed_ms, error = run_with_timeout(slow_fn, 0.05)
    assert timed_out is True
    assert error == "timeout"
    assert isinstance(result, dict)
    assert elapsed_ms >= 0


def test_run_with_timeout_success():
    def fast_fn():
        return {"value": 42}

    result, timed_out, _, error = run_with_timeout(fast_fn, 0.5)
    assert timed_out is False
    assert error is None
    assert result["value"] == 42


def test_text_fallback_payload_contains_original_text():
    payload = fallback_for("text_simplify", original_text="Original content")
    assert payload["simplified_text"] == "Original content"


def test_prefetch_manager_round_trip():
    manager = PrefetchManager(max_workers=1, ttl_seconds=60, max_entries=10)
    manager.set_generator(lambda action_id, _request: {"action_id": action_id, "ready": True})

    request = {
        "session_id": "s1",
        "slide_content": "Newton's first law",
        "content_type": "animation",
    }

    queued = manager.start_prefetch([3, 2], request)
    assert queued >= 1

    value, cache_hit = manager.get_cached_or_wait(action_id=3, request_data=request, timeout=2)
    assert cache_hit is True
    assert value is not None
    assert value["action_id"] == 3

    status = manager.get_status(action_id=3, request_data=request)
    assert status["status"] == "ready"
    assert status["cache_hit"] is True
