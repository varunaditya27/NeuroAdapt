import json

from fastapi import APIRouter, HTTPException

from backend.db import redis_client
from backend.models.state_vector import StateVector

router = APIRouter(prefix="/api", tags=["state"])


@router.post("/state")
async def post_state(payload: StateVector) -> dict[str, str]:
    key = f"state:{payload.session_id}"
    vector = payload.as_list()

    try:
        await redis_client.set(key, json.dumps(vector), ex=300)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Redis unavailable: {exc}") from exc

    return {"status": "ok", "session_id": payload.session_id}
