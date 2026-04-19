"""Background prefetch manager for Tier-3/Tier-2 speculative generation."""

from __future__ import annotations

import hashlib
import os
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple


@dataclass
class _CacheEntry:
    value: dict
    created_at: float


class PrefetchManager:
    def __init__(self, max_workers: int = 4, ttl_seconds: int = 600, max_entries: int = 100):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.ttl_seconds = ttl_seconds
        self.max_entries = max_entries

        self._cache: Dict[str, _CacheEntry] = {}
        self._active: Dict[str, Future] = {}
        self._lock = threading.Lock()
        self._generator: Optional[Callable[[int, dict], dict]] = None

    def set_generator(self, callback: Callable[[int, dict], dict]) -> None:
        self._generator = callback

    def _make_key(
        self,
        session_id: str,
        action_id: int,
        slide_content: str,
        content_type: str | None = None,
    ) -> str:
        content_hash = hashlib.md5(slide_content.encode("utf-8")).hexdigest()
        return f"{session_id}:{action_id}:{content_type or 'auto'}:{content_hash}"

    def _candidate_keys(
        self,
        session_id: str,
        action_id: int,
        slide_content: str,
        content_type: str | None = None,
    ) -> List[str]:
        explicit = self._make_key(session_id, action_id, slide_content, content_type)
        keys = [explicit]
        if content_type not in {None, "", "auto"}:
            keys.append(self._make_key(session_id, action_id, slide_content, None))
        # Preserve order while removing duplicates.
        seen = set()
        deduped: List[str] = []
        for key in keys:
            if key in seen:
                continue
            seen.add(key)
            deduped.append(key)
        return deduped

    def _prune_locked(self) -> None:
        now = time.time()
        stale = [k for k, v in self._cache.items() if now - v.created_at > self.ttl_seconds]
        for key in stale:
            self._cache.pop(key, None)

        while len(self._cache) > self.max_entries:
            oldest_key = min(self._cache, key=lambda k: self._cache[k].created_at)
            self._cache.pop(oldest_key, None)

    def _normalize_actions(self, candidates: Iterable[Any]) -> List[int]:
        out: List[int] = []
        for item in candidates:
            if isinstance(item, int):
                out.append(item)
            elif isinstance(item, (tuple, list)) and item:
                try:
                    out.append(int(item[0]))
                except Exception:
                    continue
            elif isinstance(item, dict) and "action_id" in item:
                try:
                    out.append(int(item["action_id"]))
                except Exception:
                    continue
        return [a for a in out if 0 <= a <= 5]

    def _on_done(self, key: str, future: Future) -> None:
        with self._lock:
            self._active.pop(key, None)

        try:
            value = future.result()
        except Exception as exc:
            value = {"warning": f"prefetch_failed: {exc}"}

        with self._lock:
            self._cache[key] = _CacheEntry(value=value, created_at=time.time())
            self._prune_locked()

    def start_prefetch(self, action_candidates: Iterable[Any], request_data: dict) -> int:
        """Start speculative generation for top-2 candidates."""
        if self._generator is None:
            return 0

        queued = 0
        actions = self._normalize_actions(action_candidates)[:2]
        session_id = str(request_data.get("session_id", "unknown"))
        slide_content = str(request_data.get("slide_content", ""))

        for action_id in actions:
            content_type = request_data.get("content_type")
            key = self._make_key(session_id, action_id, slide_content, content_type)
            future: Future | None = None

            with self._lock:
                self._prune_locked()
                if key in self._cache or key in self._active:
                    continue

                future = self.executor.submit(self._generator, action_id, dict(request_data))
                self._active[key] = future
                queued += 1

            # Register callback outside lock.
            # If the future already finished, callback executes immediately in this thread;
            # outside-lock registration prevents deadlocks against _on_done locking.
            if future is not None:
                future.add_done_callback(lambda f, cache_key=key: self._on_done(cache_key, f))

        return queued

    def get_cached(self, action_id: int, request_data: dict) -> Optional[dict]:
        session_id = str(request_data.get("session_id", "unknown"))
        slide_content = str(request_data.get("slide_content", ""))
        content_type = request_data.get("content_type")
        keys = self._candidate_keys(session_id, action_id, slide_content, content_type)

        with self._lock:
            self._prune_locked()
            for key in keys:
                entry = self._cache.get(key)
                if entry:
                    return dict(entry.value)
            return None

    def get_cached_or_wait(self, action_id: int, request_data: dict, timeout: float = 30) -> Tuple[Optional[dict], bool]:
        cached = self.get_cached(action_id, request_data)
        if cached is not None:
            return cached, True

        session_id = str(request_data.get("session_id", "unknown"))
        slide_content = str(request_data.get("slide_content", ""))
        content_type = request_data.get("content_type")
        keys = self._candidate_keys(session_id, action_id, slide_content, content_type)

        selected_key: str | None = None
        with self._lock:
            future = None
            for key in keys:
                maybe = self._active.get(key)
                if maybe is not None:
                    future = maybe
                    selected_key = key
                    break

        if not future:
            return None, False

        try:
            value = future.result(timeout=timeout)
        except Exception:
            return None, False

        with self._lock:
            now = time.time()
            for key in keys:
                self._cache[key] = _CacheEntry(value=value, created_at=now)
            if selected_key is not None:
                self._active.pop(selected_key, None)
            self._prune_locked()

        return dict(value), True

    def get_status(self, action_id: int, request_data: dict) -> Dict[str, Any]:
        session_id = str(request_data.get("session_id", "unknown"))
        slide_content = str(request_data.get("slide_content", ""))
        content_type = request_data.get("content_type")
        keys = self._candidate_keys(session_id, action_id, slide_content, content_type)

        with self._lock:
            self._prune_locked()
            for key in keys:
                if key in self._cache:
                    return {"status": "ready", "cache_hit": True, "content": self._cache[key].value}

            for key in keys:
                if key in self._active:
                    return {"status": "pending", "cache_hit": False, "content": None}

        return {"status": "missing", "cache_hit": False, "content": None}

    def clear_session(self, session_id: str) -> None:
        with self._lock:
            keys = [k for k in self._cache if k.startswith(f"{session_id}:")]
            for key in keys:
                self._cache.pop(key, None)


prefetch_manager = PrefetchManager(
    max_workers=int(os.getenv("PREFETCH_MAX_WORKERS", "4")),
    ttl_seconds=int(os.getenv("CACHE_TTL_SECONDS", "600")),
    max_entries=int(os.getenv("CACHE_MAX_SIZE", os.getenv("GENERATION_CACHE_SIZE", "100"))),
)
