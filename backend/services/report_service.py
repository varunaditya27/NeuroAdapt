"""PDF report generation service for analytics.

Uses WeasyPrint to render a Jinja2 HTML template to PDF bytes.
Server-side only — no client-side rendering or LLM calls.
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.services.analytics_service import (
    get_modalities,
    get_overload,
    get_stability,
    get_user_summary,
)

logger = logging.getLogger(__name__)


async def generate_pdf_report(db: AsyncSession, user_id: str) -> bytes:
    summary = await get_user_summary(db, user_id)
    stability = await get_stability(db, user_id)
    overload = await get_overload(db, user_id)
    modalities = await get_modalities(db, user_id)
    reward_data = await _get_reward_summary(db, user_id)

    snapshot_count = await _count_snapshots(db, user_id)

    report_data = _build_report_data(
        summary, stability, overload, modalities, reward_data, snapshot_count,
    )

    return _render_pdf(report_data)


async def _get_reward_summary(db: AsyncSession, user_id: str) -> list[dict[str, Any]]:
    """Aggregate reward data from replay_buffer per reward_type.

    Since there's no reward_log table, we analyze stored reward values
    from replay_buffer grouped by action type.
    """
    rows = await db.execute(
        text(
            """
            SELECT rb.action, rb.reward, rb.created_at
            FROM replay_buffer rb
            JOIN sessions s ON s.id = rb.session_id
            WHERE s.student_id = :user_id
            ORDER BY rb.created_at ASC
            """
        ),
        {"user_id": user_id},
    )
    records = rows.all()

    if not records:
        return []

    # Group by action (which maps to intervention type)
    from backend.shared_config import ACTION_NAMES

    by_action: dict[int, list[float]] = defaultdict(list)
    for row in records:
        action = row[0]
        reward = row[1]
        by_action[action].append(reward)

    summary = []
    for action_id, rewards in sorted(by_action.items()):
        action_name = ACTION_NAMES.get(action_id, f"action_{action_id}")
        summary.append({
            "action_name": action_name,
            "action_id": action_id,
            "count": len(rewards),
            "avg_reward": round(sum(rewards) / len(rewards), 3),
            "min_reward": round(min(rewards), 3),
            "max_reward": round(max(rewards), 3),
        })

    return summary


async def _count_snapshots(db: AsyncSession, user_id: str) -> int:
    """Count total state snapshots for a user."""
    row = await db.execute(
        text(
            """
            SELECT COUNT(*)
            FROM state_snapshots ss
            JOIN sessions s ON s.id = ss.session_id
            WHERE s.student_id = :user_id
            """
        ),
        {"user_id": user_id},
    )
    return row.scalar() or 0


def _build_report_data(
    summary: dict,
    stability: dict,
    overload: dict,
    modalities: dict,
    reward_data: list[dict],
    snapshot_count: int,
) -> dict[str, Any]:
    """Assemble all analytics data into a structured dict for the template."""
    now = datetime.now(timezone.utc)

    # Determine date range from available data
    date_range = f"Last 30 days"

    return {
        "report_date": now.strftime("%B %d, %Y %H:%M UTC"),
        "report_date_short": now.strftime("%Y-%m-%d"),
        "learner_name": summary.get("name", "Learner"),
        "member_since": summary.get("member_since", "—"),
        "total_sessions": summary.get("total_sessions", 0),
        "current_streak": summary.get("current_streak", 0),
        "total_snapshots": snapshot_count,
        "date_range": date_range,
        # Stability
        "current_score": stability.get("current_score"),
        "daily_trend": stability.get("daily", {}),
        "weekly_trend": stability.get("weekly", {}),
        "monthly_trend": stability.get("monthly", {}),
        # Overload
        "spikes_this_week": overload.get("spikes_this_week", 0),
        "spikes_last_week": overload.get("spikes_last_week", 0),
        "weekly_delta": overload.get("weekly_delta", 0),
        "avg_spikes_per_session": overload.get("avg_spikes_per_session", 0.0),
        "sessions_with_zero_spikes": overload.get("sessions_with_zero_spikes", 0),
        # Modalities
        "modalities": modalities.get("modalities", {}),
        "total_modality_events": modalities.get("total_events", 0),
        "modality_no_data": modalities.get("no_data", True),
        # Intervention effectiveness
        "reward_summary": reward_data,
    }


def _render_pdf(data: dict[str, Any]) -> bytes:
    from pathlib import Path
    from jinja2 import Environment, FileSystemLoader
    from xhtml2pdf import pisa
    import io
    import re

    templates_dir = Path(__file__).parent.parent / "templates"
    env = Environment(loader=FileSystemLoader(str(templates_dir)))
    template = env.get_template("report_template.html")
    html = template.render(**data)

    # Strip all <style> blocks and replace with xhtml2pdf-safe CSS
    html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL)
    safe_css = """
    <style>
        body { font-family: Helvetica, Arial, sans-serif; font-size: 12px; color: #1a1a2e; }
        h1 { font-size: 22px; margin-bottom: 8px; }
        h2 { font-size: 16px; margin-top: 20px; margin-bottom: 6px; }
        h3 { font-size: 13px; margin-top: 12px; margin-bottom: 4px; }
        table { width: 100%; border-collapse: collapse; margin-bottom: 16px; }
        th { background-color: #2a9d8f; color: #ffffff; padding: 6px 8px; text-align: left; }
        td { padding: 5px 8px; border-bottom: 1px solid #e0e0e0; }
        .label { color: #666666; font-size: 11px; }
        .value { font-weight: bold; font-size: 14px; }
        .section { margin-bottom: 20px; }
    </style>
    """
    html = html.replace('</head>', safe_css + '</head>')

    buffer = io.BytesIO()
    result = pisa.CreatePDF(html, dest=buffer)
    if result.err:
        raise RuntimeError(f"PDF generation failed with {result.err} errors")
    return buffer.getvalue()