import json

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db import get_db
from backend.models.feedback import FeedbackPayload, FeedbackResponse
from backend.services.reward_router import compute_reward
from backend.services.state_store import fetch_latest_state, get_cached_state

router = APIRouter(prefix="/api", tags=["feedback"])


@router.post("/feedback", response_model=FeedbackResponse)
async def post_feedback(
    payload: FeedbackPayload,
    db: AsyncSession = Depends(get_db),
) -> FeedbackResponse:
    next_state = get_cached_state(payload.session_id)
    if next_state is None:
        try:
            next_state = await fetch_latest_state(db, payload.session_id)
        except Exception:
            next_state = None
    if next_state is None:
        next_state = payload.current_state

    done = payload.event == "complete"
    reward_value = compute_reward(
        event=payload.event,
        chosen_format=payload.chosen_format,
        state=payload.current_state,
        action=payload.action_taken,
        next_state=next_state,
        done=done,
    )
    stored = False

    try:
        await db.execute(
            text(
                """
                INSERT INTO replay_buffer (session_id, state, action, reward, next_state, done)
                VALUES (:session_id, :state, :action, :reward, :next_state, :done)
                """
            ),
            {
                "session_id": payload.session_id,
                "state": json.dumps(payload.current_state),
                "action": payload.action_taken,
                "reward": reward_value,
                "next_state": json.dumps(next_state),
                "done": done,
            },
        )
        if payload.chosen_format:
            await db.execute(
                text(
                    """
                    INSERT INTO preference_log (session_id, chosen_format, pref_delta)
                    VALUES (:session_id, :chosen_format, :pref_delta)
                    """
                ),
                {
                    "session_id": payload.session_id,
                    "chosen_format": payload.chosen_format,
                    "pref_delta": payload.current_state[-1],
                },
            )
        await db.commit()
        stored = True
    except Exception:
        await db.rollback()

    return FeedbackResponse(reward=reward_value, stored=stored)
