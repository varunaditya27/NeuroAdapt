"""Background prefetch manager for Tier-3/Tier-2 speculative generation."""

from __future__ import annotations

import hashlib
import os
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor, TimeoutError as FutureTimeout
from dataclasses import dataclass
from typing import Any, Callable, Iterable, List, Optional, Tuple

JSONDict = dict[str, Any]
GeneratorCallback = Callable[[int, JSONDict], JSONDict]


@dataclass
class _CacheEntry:
    value: JSONDict
    created_at: float


class PrefetchManager:
    def __init__(self, max_workers: int = 4, ttl_seconds: int = 600, max_entries: int = 100):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.ttl_seconds = ttl_seconds
        self.max_entries = max_entries

        self._cache: dict[str, _CacheEntry] = {}
        self._active: dict[str, Future[JSONDict]] = {}
        self._lock = threading.Lock()
        self._generator: Optional[GeneratorCallback] = None
        self._cleared_sessions: set[str] = set()

    _PREFETCHABLE_ACTIONS = {2, 3, 4}
    _CONTENT_TYPE_NORMALIZATION = {
        "animation": "animation",
        "video": "animation",
        "manim": "animation",
        "stem": "animation",
        "math": "animation",
        "physics": "animation",
        "algorithm": "animation",
        "process": "animation",
        "image": "image",
        "visual": "image",
        "illustration": "image",
        "graphic": "image",
        "general": "image",
        "audio": "audio",
        "tts": "audio",
        "speech": "audio",
        "avatar": "avatar",
        "liveportrait": "avatar",
        "video_avatar": "avatar",
        "auto": "auto",
    }

    def set_generator(self, callback: GeneratorCallback) -> None:
        self._generator = callback

    def _normalize_content_type(self, content_type: Any) -> str:
        if content_type is None:
            return "auto"
        normalized = self._CONTENT_TYPE_NORMALIZATION.get(str(content_type).strip().lower())
        return normalized or "auto"

    def _normalize_learner_level(self, learner_level: Any) -> str:
        if learner_level is None:
            return "grade8"
        value = str(learner_level).strip().lower()
        if not value:
            return "grade8"
        return value

    def _make_key(
        self,
        session_id: str,
        action_id: int,
        slide_content: str,
        learner_level: str | None = None,
        content_type: str | None = None,
    ) -> str:
        content_hash = hashlib.md5(slide_content.encode("utf-8")).hexdigest()
        normalized_learner_level = self._normalize_learner_level(learner_level)
        normalized_content_type = self._normalize_content_type(content_type)
        return f"{session_id}:{action_id}:{normalized_learner_level}:{normalized_content_type}:{content_hash}"

    def _candidate_keys(
        self,
        session_id: str,
        action_id: int,
        slide_content: str,
        learner_level: str | None = None,
        content_type: str | None = None,
    ) -> List[str]:
        normalized_learner_level = self._normalize_learner_level(learner_level)
        normalized_content_type = self._normalize_content_type(content_type)
        explicit = self._make_key(
            session_id,
            action_id,
            slide_content,
            normalized_learner_level,
            normalized_content_type,
        )
        keys = [explicit]
        if normalized_content_type != "auto":
            keys.append(
                self._make_key(
                    session_id,
                    action_id,
                    slide_content,
                    normalized_learner_level,
                    None,
                )
            )
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
        # Preserve order while filtering to useful speculative actions only.
        deduped: List[int] = []
        seen = set()
        for action_id in out:
            if action_id in seen:
                continue
            seen.add(action_id)
            if action_id in self._PREFETCHABLE_ACTIONS:
                deduped.append(action_id)
        return deduped

    def _on_done(self, cache_keys: List[str], future: Future[JSONDict]) -> None:
        with self._lock:
            for key in cache_keys:
                self._active.pop(key, None)

        try:
            value = future.result()
        except Exception as exc:
            value = {"warning": f"prefetch_failed: {exc}"}

        if not isinstance(value, dict):
            value = {"result": value}

        session_id = cache_keys[0].split(":", 1)[0] if cache_keys else ""

        with self._lock:
            if session_id in self._cleared_sessions:
                return
            now = time.time()
            for key in cache_keys:
                self._cache[key] = _CacheEntry(value=value, created_at=now)
            self._prune_locked()

    def start_prefetch(self, action_candidates: Iterable[Any], request_data: JSONDict) -> int:
        """Start speculative generation for top-2 candidates."""
        if self._generator is None:
            return 0

        queued = 0
        actions = self._normalize_actions(action_candidates)[:2]
        session_id = str(request_data.get("session_id", "unknown"))
        slide_content = str(request_data.get("slide_content", ""))
        learner_level = request_data.get("learner_level")
        self._cleared_sessions.discard(session_id)

        for action_id in actions:
            content_type = request_data.get("content_type")
            cache_keys = self._candidate_keys(
                session_id,
                action_id,
                slide_content,
                learner_level,
                content_type,
            )
            if not cache_keys:
                continue
            future: Future[JSONDict] | None = None

            with self._lock:
                self._prune_locked()
                if any(key in self._cache for key in cache_keys):
                    continue
                if any(key in self._active for key in cache_keys):
                    continue

                future = self.executor.submit(self._generator, action_id, dict(request_data))
                for key in cache_keys:
                    self._active[key] = future
                queued += 1

            # Register callback outside lock.
            # If the future already finished, callback executes immediately in this thread;
            # outside-lock registration prevents deadlocks against _on_done locking.
            if future is not None:

                def _finalize_prefetch(
                    fut: Future[JSONDict], keys: list[str] = list(cache_keys)
                ) -> None:
                    self._on_done(keys, fut)

                future.add_done_callback(_finalize_prefetch)

        return queued

    def get_cached(self, action_id: int, request_data: JSONDict) -> Optional[JSONDict]:
        session_id = str(request_data.get("session_id", "unknown"))
        slide_content = str(request_data.get("slide_content", ""))
        learner_level = request_data.get("learner_level")
        content_type = request_data.get("content_type")
        keys = self._candidate_keys(
            session_id, action_id, slide_content, learner_level, content_type
        )

        with self._lock:
            self._prune_locked()
            for key in keys:
                entry = self._cache.get(key)
                if entry:
                    return dict(entry.value)
            return None

    def get_cached_or_wait(
        self, action_id: int, request_data: JSONDict, timeout: float = 30
    ) -> Tuple[Optional[JSONDict], bool]:
        cached = self.get_cached(action_id, request_data)
        if cached is not None:
            return cached, True

        session_id = str(request_data.get("session_id", "unknown"))
        slide_content = str(request_data.get("slide_content", ""))
        learner_level = request_data.get("learner_level")
        content_type = request_data.get("content_type")
        keys = self._candidate_keys(
            session_id, action_id, slide_content, learner_level, content_type
        )

        selected_key: str | None = None
        future: Future[JSONDict] | None = None
        with self._lock:
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
        except FutureTimeout:
            return None, False
        except Exception:
            return None, False

        if not isinstance(value, dict):
            value = {"result": value}

        session_id = keys[0].split(":", 1)[0] if keys else ""

        with self._lock:
            if session_id in self._cleared_sessions:
                return None, False
            now = time.time()
            for key in keys:
                self._cache[key] = _CacheEntry(value=value, created_at=now)
                self._active.pop(key, None)
            if selected_key is not None:
                self._active.pop(selected_key, None)
            self._prune_locked()

        return dict(value), True

    def get_status(self, action_id: int, request_data: JSONDict) -> dict[str, Any]:
        session_id = str(request_data.get("session_id", "unknown"))
        slide_content = str(request_data.get("slide_content", ""))
        learner_level = request_data.get("learner_level")
        content_type = request_data.get("content_type")
        keys = self._candidate_keys(
            session_id, action_id, slide_content, learner_level, content_type
        )

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
            self._cleared_sessions.add(session_id)
            keys = [k for k in self._cache if k.startswith(f"{session_id}:")]
            for key in keys:
                self._cache.pop(key, None)

            active_keys = [k for k in self._active if k.startswith(f"{session_id}:")]
            futures = {self._active.get(k) for k in active_keys}
            for key in active_keys:
                self._active.pop(key, None)

        for future in futures:
            if future is not None:
                future.cancel()


prefetch_manager = PrefetchManager(
    max_workers=int(os.getenv("PREFETCH_MAX_WORKERS", "4")),
    ttl_seconds=int(os.getenv("CACHE_TTL_SECONDS", "600")),
    max_entries=int(os.getenv("CACHE_MAX_SIZE", os.getenv("GENERATION_CACHE_SIZE", "100"))),
)
