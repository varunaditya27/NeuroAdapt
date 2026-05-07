from __future__ import annotations

import json
import time
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

STATE_TTL_SECONDS = 300

_STATE_CACHE: dict[str, tuple[float, list[float]]] = {}


def _prune_expired(now: float | None = None) -> None:
    current_time = now if now is not None else time.time()
    expired = [
        session_id
        for session_id, (expires_at, _vector) in _STATE_CACHE.items()
        if expires_at <= current_time
    ]
    for session_id in expired:
        _STATE_CACHE.pop(session_id, None)


def set_cached_state(session_id: str, vector: list[float]) -> None:
    _prune_expired()
    _STATE_CACHE[session_id] = (time.time() + STATE_TTL_SECONDS, list(vector))


def get_cached_state(session_id: str) -> list[float] | None:
    _prune_expired()
    cached = _STATE_CACHE.get(session_id)
    if cached is None:
        return None
    return list(cached[1])


def cache_status() -> dict[str, Any]:
    _prune_expired()
    return {"entries": len(_STATE_CACHE), "ttl_seconds": STATE_TTL_SECONDS}


def clear_state_cache() -> None:
    _STATE_CACHE.clear()


async def persist_state(db: AsyncSession, session_id: str, vector: list[float]) -> None:
    await db.execute(
        text(
            """
            INSERT INTO state_snapshots (session_id, state)
            VALUES (:session_id, :state)
            """
        ),
        {"session_id": session_id, "state": json.dumps(vector)},
    )


async def fetch_latest_state(db: AsyncSession, session_id: str) -> list[float] | None:
    result = await db.execute(
        text(
            """
            SELECT state
            FROM state_snapshots
            WHERE session_id = :session_id
            ORDER BY created_at DESC
            LIMIT 1
            """
        ),
        {"session_id": session_id},
    )
    row = result.first()
    if row is None:
        return None

    raw_state = row[0]
    if isinstance(raw_state, str):
        raw_state = json.loads(raw_state)
    if isinstance(raw_state, list):
        return [float(value) for value in raw_state]
    return None


async def persist_lesson_event(
    db: AsyncSession,
    session_id: str,
    metadata: dict,
    duration_ms: int | None,
    state: list[float],
) -> None:
    await db.execute(
        text(
            """
            INSERT INTO lesson_events
                (session_id, subject, topic, duration_ms, final_slide, total_slides, state)
            VALUES
                (:session_id, :subject, :topic, :duration_ms, :final_slide, :total_slides, :state)
            """
        ),
        {
            "session_id": session_id,
            "subject": metadata.get("subject"),
            "topic": metadata.get("topic"),
            "duration_ms": duration_ms,
            "final_slide": metadata.get("current_slide"),
            "total_slides": metadata.get("total_slides"),
            "state": json.dumps(state),
        },
    )
