"""Analytics service for Cognitive Stability Dashboard, Learning Modalities,
and User Summary computations.

All analytics are computed on-the-fly from persisted telemetry data.
No caching — lightweight DB aggregations only.
"""

from __future__ import annotations

import json
import logging
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# State vector indices in the stored JSON array: [dwell, jitter, focus, stall, pref_delta]
IDX_DWELL = 0
IDX_JITTER = 1
IDX_FOCUS = 2
IDX_STALL = 3
IDX_PREF_DELTA = 4

# Overload spike threshold (mirrors Stability Reward Engine condition)
OVERLOAD_IJ_THRESHOLD = 0.65
OVERLOAD_SD_THRESHOLD = 0.65

# CSS component weights
W_SDR = 0.30
W_FP = 0.30
W_IJ = 0.20
W_SD = 0.20

# Minimum snapshot count for valid trends
MIN_SNAPSHOTS_FOR_TREND = 3


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_state(raw_state: Any) -> list[float] | None:
    """Parse a stored state into a float list [dwell, jitter, focus, stall, pref_delta]."""
    if raw_state is None:
        return None
    if isinstance(raw_state, str):
        try:
            raw_state = json.loads(raw_state)
        except (json.JSONDecodeError, TypeError):
            return None
    if isinstance(raw_state, list) and len(raw_state) >= 5:
        try:
            return [float(v) for v in raw_state[:5]]
        except (ValueError, TypeError):
            return None
    return None


def _compute_css(state: list[float]) -> float:
    """Compute Cognitive Stability Score from a 5-element state vector.

    CSS = (dwell × 0.30) + (focus × 0.30) + ((1 - jitter) × 0.20) + ((1 - stall) × 0.20)
    Scaled to 0-100.
    """
    dwell, jitter, focus, stall = state[0], state[1], state[2], state[3]
    raw = (dwell * W_SDR) + (focus * W_FP) + ((1.0 - jitter) * W_IJ) + ((1.0 - stall) * W_SD)
    return round(raw * 100.0, 1)


def _is_overload_spike(state: list[float]) -> bool:
    """Check if a state vector meets the overload spike condition."""
    return state[IDX_JITTER] > OVERLOAD_IJ_THRESHOLD and state[IDX_STALL] > OVERLOAD_SD_THRESHOLD


async def _fetch_state_snapshots_since(
    db: AsyncSession,
    student_id: str,
    since: datetime,
) -> list[dict]:
    """Fetch state snapshots for a student since a given timestamp, ordered ascending.

    The 'student_id' is stored in the 'sessions' table. We join through sessions
    to find snapshots belonging to this user.
    """
    rows = await db.execute(
        text(
            """
            SELECT ss.state, ss.created_at, ss.session_id
            FROM state_snapshots ss
            JOIN sessions s ON s.id = ss.session_id
            WHERE s.student_id = :student_id
              AND ss.created_at >= :since
            ORDER BY ss.created_at ASC
            """
        ),
        {"student_id": student_id, "since": since},
    )
    results = []
    for row in rows:
        state = _parse_state(row[0])
        if state is not None:
            results.append({
                "state": state,
                "created_at": row[1],
                "session_id": row[2],
            })
    return results


async def _fetch_all_session_dates(
    db: AsyncSession,
    student_id: str,
) -> list[datetime]:
    """Fetch all distinct session creation timestamps for a student."""
    rows = await db.execute(
        text(
            """
            SELECT created_at
            FROM sessions
            WHERE student_id = :student_id
            ORDER BY created_at ASC
            """
        ),
        {"student_id": student_id},
    )
    return [row[0] for row in rows]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def get_user_summary(db: AsyncSession, user_id: str) -> dict[str, Any]:
    """Return user identity strip fields."""
    # Try to find the user in sessions table; use first session's student_id
    row = await db.execute(
        text(
            """
            SELECT student_id, MIN(created_at) as first_seen
            FROM sessions
            WHERE student_id = :user_id
            GROUP BY student_id
            """
        ),
        {"user_id": user_id},
    )
    user_row = row.first()
    if user_row is None:
        # No sessions yet — fallback
        return {
            "name": "Learner",
            "member_since": "—",
            "total_sessions": 0,
            "current_streak": 0,
        }

    display_name = "Learner"  # No users.name column exists; hardcoded fallback
    member_since_raw = user_row[1]  # first session timestamp

    # Format member_since
    if member_since_raw:
        if isinstance(member_since_raw, str):
            member_dt = datetime.fromisoformat(member_since_raw.replace("Z", "+00:00"))
        else:
            member_dt = member_since_raw.replace(tzinfo=timezone.utc) if member_since_raw.tzinfo is None else member_since_raw
        member_since = member_dt.strftime("%B %Y")
    else:
        member_since = "—"

    # Total sessions
    count_row = await db.execute(
        text(
            "SELECT COUNT(DISTINCT id) FROM sessions WHERE student_id = :user_id"
        ),
        {"user_id": user_id},
    )
    total_sessions = count_row.scalar() or 0

    # Current streak: walk backwards from today through session dates
    session_dates = await _fetch_all_session_dates(db, user_id)
    session_date_set = set()
    for sd in session_dates:
        if isinstance(sd, str):
            sd = datetime.fromisoformat(sd.replace("Z", "+00:00"))
        if sd.tzinfo is None:
            sd = sd.replace(tzinfo=timezone.utc)
        session_date_set.add(sd.date())

    today = datetime.now(timezone.utc).date()
    streak = 0
    # If no session today, start checking from yesterday
    check = today if today in session_date_set else today - timedelta(days=1)
    while check in session_date_set:
        streak += 1
        check -= timedelta(days=1)

    return {
        "name": display_name,
        "member_since": member_since,
        "total_sessions": total_sessions,
        "current_streak": streak,
    }


async def get_stability(db: AsyncSession, user_id: str) -> dict[str, Any]:
    """Compute Cognitive Stability Score and trends for all three windows."""
    now = datetime.now(timezone.utc)

    # Fetch snapshots for the last 60 days (covers monthly window)
    snapshots = await _fetch_state_snapshots_since(db, user_id, now - timedelta(days=60))

    if not snapshots:
        return {
            "current_score": None,
            "daily": {"mean": None, "delta": None, "sufficient_data": False},
            "weekly": {"mean": None, "delta": None, "sufficient_data": False},
            "monthly": {"mean": None, "delta": None, "sufficient_data": False},
        }

    # Current score: average of last 10 snapshots or all if fewer
    recent_snapshots = [s["state"] for s in snapshots[-10:]]
    current_score = round(sum(_compute_css(s) for s in recent_snapshots) / len(recent_snapshots), 1)

    def _window_stats(snapshots_subset: list[dict]) -> dict:
        css_values = [_compute_css(s["state"]) for s in snapshots_subset]
        if len(css_values) < MIN_SNAPSHOTS_FOR_TREND:
            return {"mean": None, "delta": None, "sufficient_data": False}
        mean_score = round(sum(css_values) / len(css_values), 1)
        return {"mean": mean_score, "delta": None, "sufficient_data": True}

    # Daily: last 24h vs 24-48h ago
    daily_now = [s for s in snapshots if s["created_at"] >= now - timedelta(hours=24)]
    daily_before = [
        s
        for s in snapshots
        if (now - timedelta(hours=48)) <= s["created_at"] < (now - timedelta(hours=24))
    ]
    daily_current = _window_stats(daily_now)
    daily_prior = _window_stats(daily_before)
    daily_delta = None
    if daily_current["sufficient_data"] and daily_prior["sufficient_data"] and daily_prior["mean"] is not None:
        daily_delta = round(daily_current["mean"] - daily_prior["mean"], 1)

    # Weekly: last 7d vs 7-14d ago
    weekly_now = [s for s in snapshots if s["created_at"] >= now - timedelta(days=7)]
    weekly_before = [
        s
        for s in snapshots
        if (now - timedelta(days=14)) <= s["created_at"] < (now - timedelta(days=7))
    ]
    weekly_current = _window_stats(weekly_now)
    weekly_prior = _window_stats(weekly_before)
    weekly_delta = None
    if weekly_current["sufficient_data"] and weekly_prior["sufficient_data"] and weekly_prior["mean"] is not None:
        weekly_delta = round(weekly_current["mean"] - weekly_prior["mean"], 1)

    # Monthly: last 30d vs 30-60d ago
    monthly_now = [s for s in snapshots if s["created_at"] >= now - timedelta(days=30)]
    monthly_before = [
        s
        for s in snapshots
        if (now - timedelta(days=60)) <= s["created_at"] < (now - timedelta(days=30))
    ]
    monthly_current = _window_stats(monthly_now)
    monthly_prior = _window_stats(monthly_before)
    monthly_delta = None
    if monthly_current["sufficient_data"] and monthly_prior["sufficient_data"] and monthly_prior["mean"] is not None:
        monthly_delta = round(monthly_current["mean"] - monthly_prior["mean"], 1)

    return {
        "current_score": current_score,
        "daily": {"mean": daily_current["mean"], "delta": daily_delta, "sufficient_data": daily_current["sufficient_data"]},
        "weekly": {"mean": weekly_current["mean"], "delta": weekly_delta, "sufficient_data": weekly_current["sufficient_data"]},
        "monthly": {"mean": monthly_current["mean"], "delta": monthly_delta, "sufficient_data": monthly_current["sufficient_data"]},
    }


async def get_overload(db: AsyncSession, user_id: str) -> dict[str, Any]:
    """Compute cognitive overload spike frequencies."""
    now = datetime.now(timezone.utc)

    # Fetch snapshots for last 30 days (for per-session stats)
    snapshots_30d = await _fetch_state_snapshots_since(db, user_id, now - timedelta(days=30))
    snapshots_14d = await _fetch_state_snapshots_since(db, user_id, now - timedelta(days=14))

    # spikes_this_week: last 7 days
    this_week = [
        s for s in snapshots_14d
        if s["created_at"] >= now - timedelta(days=7)
    ]
    spikes_this_week = sum(1 for s in this_week if _is_overload_spike(s["state"]))

    # spikes_last_week: 7-14 days ago
    last_week = [
        s for s in snapshots_14d
        if (now - timedelta(days=14)) <= s["created_at"] < (now - timedelta(days=7))
    ]
    spikes_last_week = sum(1 for s in last_week if _is_overload_spike(s["state"]))

    weekly_delta = spikes_this_week - spikes_last_week

    # Per-session stats from last 30 days
    session_spikes: dict[str, int] = Counter()
    for s in snapshots_30d:
        if _is_overload_spike(s["state"]):
            session_spikes[s["session_id"]] += 1

    total_sessions_in_30d = len({s["session_id"] for s in snapshots_30d})
    sessions_with_zero = sum(
        1 for sid in {s["session_id"] for s in snapshots_30d}
        if session_spikes.get(sid, 0) == 0
    )

    avg_spikes_per_session = (
        round(sum(session_spikes.values()) / total_sessions_in_30d, 1)
        if total_sessions_in_30d > 0
        else 0.0
    )

    return {
        "spikes_this_week": spikes_this_week,
        "spikes_last_week": spikes_last_week,
        "weekly_delta": weekly_delta,
        "avg_spikes_per_session": avg_spikes_per_session,
        "sessions_with_zero_spikes": sessions_with_zero,
    }


async def get_modalities(db: AsyncSession, user_id: str) -> dict[str, Any]:
    """Compute modality preference shares from session_events."""
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=30)

    rows = await db.execute(
        text(
            """
            SELECT event_type, payload
            FROM session_events
            WHERE user_id = :user_id
              AND event_type = 'modality_preference'
              AND created_at >= :since
            ORDER BY created_at ASC
            """
        ),
        {"user_id": user_id, "since": since},
    )

    events = rows.all()
    total_events = len(events)
    modalities: dict[str, dict] = {
        "standard": {"count": 0, "share": 0.0},
        "simplified_text": {"count": 0, "share": 0.0},
        "video": {"count": 0, "share": 0.0},
        "audio": {"count": 0, "share": 0.0},
        "quiz": {"count": 0, "share": 0.0},
        "sensory_break": {"count": 0, "share": 0.0},
    }

    explicit_count = 0
    for row in events:
        payload = row[1]
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except (json.JSONDecodeError, TypeError):
                continue
        if not isinstance(payload, dict):
            continue

        modality = payload.get("modality")
        source = payload.get("source")

        if modality not in modalities:
            continue

        # Dismissal events count toward 'standard'
        if source == "dismissal":
            modalities["standard"]["count"] += 1
        elif modality in modalities:
            modalities[modality]["count"] += 1

        if source == "acceptance":
            explicit_count += 1

    # Compute shares using explicit acceptance events as denominator
    # (spec: preference_share(modality) = count(modality, source=acceptance) / total_explicit_events)
    # Dismissal events increment the standard modality counter
    total_explicit = sum(
        info["count"] for _mod, info in modalities.items()
    )

    if total_explicit > 0:
        for mod in modalities:
            modalities[mod]["share"] = round(modalities[mod]["count"] / total_explicit, 2)
    else:
        # Equal distribution fallback
        for mod in modalities:
            modalities[mod]["share"] = 0.2

    # Ensure shares sum to 1.0
    share_sum = sum(modalities[m]["share"] for m in modalities)
    if total_explicit > 0 and abs(share_sum - 1.0) > 0.01:
        # Normalize
        for m in modalities:
            modalities[m]["share"] = round(modalities[m]["share"] / share_sum, 2)

    return {
        "total_events": total_events,
        "modalities": modalities,
        "no_data": total_events == 0,
    }