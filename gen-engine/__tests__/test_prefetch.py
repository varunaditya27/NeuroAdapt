from __future__ import annotations

import threading
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
        "learner_level": "grade8",
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


def test_prefetch_content_type_alias_is_retrievable_with_auto_key():
    manager = PrefetchManager(max_workers=1, ttl_seconds=60, max_entries=10)
    manager.set_generator(lambda action_id, _request: {"action_id": action_id, "ready": True})

    prefetch_request = {
        "session_id": "s_alias",
        "slide_content": "Momentum conservation",
        "learner_level": "grade8",
        "content_type": "stem",
    }
    query_request = {
        "session_id": "s_alias",
        "slide_content": "Momentum conservation",
        "learner_level": "grade8",
        # no content_type on generate request
    }

    queued = manager.start_prefetch([3], prefetch_request)
    assert queued == 1

    value, cache_hit = manager.get_cached_or_wait(action_id=3, request_data=query_request, timeout=2)
    assert cache_hit is True
    assert value is not None
    assert value["action_id"] == 3


def test_clear_session_prevents_stale_result_from_repopulating_cache():
    manager = PrefetchManager(max_workers=1, ttl_seconds=60, max_entries=10)
    started = threading.Event()
    release = threading.Event()

    def slow_generator(action_id, _request):
        started.set()
        release.wait(timeout=1)
        return {"action_id": action_id, "ready": True}

    manager.set_generator(slow_generator)
    request = {
        "session_id": "s_clear",
        "slide_content": "Friction and force",
        "learner_level": "grade8",
        "content_type": "animation",
    }

    queued = manager.start_prefetch([3], request)
    assert queued == 1
    assert started.wait(timeout=0.5)

    manager.clear_session("s_clear")
    release.set()
    time.sleep(0.05)

    status = manager.get_status(action_id=3, request_data=request)
    assert status["status"] == "missing"
    assert status["cache_hit"] is False


def test_prefetch_isolated_by_learner_level():
    manager = PrefetchManager(max_workers=1, ttl_seconds=60, max_entries=10)
    manager.set_generator(lambda action_id, request: {"action_id": action_id, "level": request.get("learner_level")})

    grade5_request = {
        "session_id": "s_level",
        "slide_content": "Cell respiration overview",
        "learner_level": "grade5",
        "content_type": "animation",
    }
    queued = manager.start_prefetch([3], grade5_request)
    assert queued == 1

    value_grade5, hit_grade5 = manager.get_cached_or_wait(action_id=3, request_data=grade5_request, timeout=2)
    assert hit_grade5 is True
    assert value_grade5 is not None
    assert value_grade5.get("level") == "grade5"

    grade8_request = {
        "session_id": "s_level",
        "slide_content": "Cell respiration overview",
        "learner_level": "grade8",
        "content_type": "animation",
    }
    value_grade8, hit_grade8 = manager.get_cached_or_wait(action_id=3, request_data=grade8_request, timeout=0.1)
    assert hit_grade8 is False
    assert value_grade8 is None
