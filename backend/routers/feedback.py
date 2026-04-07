import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db import get_db, redis_client
from backend.models.feedback import FeedbackPayload, FeedbackResponse
from backend.services.reward_router import compute_reward

router = APIRouter(prefix="/api", tags=["feedback"])


@router.post("/feedback", response_model=FeedbackResponse)
async def post_feedback(
    payload: FeedbackPayload,
    db: AsyncSession = Depends(get_db),
) -> FeedbackResponse:
    reward_value = compute_reward(event=payload.event, chosen_format=payload.chosen_format)

    try:
        next_state_raw = await redis_client.get(f"state:{payload.session_id}")
        next_state = json.loads(next_state_raw) if next_state_raw else payload.current_state
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Redis unavailable: {exc}") from exc

    done = payload.event == "complete"
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
        await db.commit()
        stored = True
    except Exception:
        await db.rollback()

    return FeedbackResponse(reward=reward_value, stored=stored)
