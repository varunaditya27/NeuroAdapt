import json
import math
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

from backend.db import redis_client
from backend.models.action import ActionResponse
from backend.shared_config import ACTION_NAMES, ACTION_SPACE, CONFIDENCE_GATE, STATE_VECTOR_DIM

router = APIRouter(prefix="/api", tags=["action"])

_model = None
_model_load_attempted = False
_model_load_error = None


def _softmax_confidence(logits: list[float]) -> float:
    max_logit = max(logits)
    exps = [math.exp(value - max_logit) for value in logits]
    total = sum(exps)
    return max(exps) / total if total else 0.0


def _placeholder_q_values(vector: list[float]) -> list[float]:
    dwell, jitter, focus, stall, pref_delta = vector
    return [
        0.4 + (focus * 0.2),
        jitter * 0.9,
        dwell * 1.1,
        pref_delta * 0.8,
        stall * 1.0,
        max(stall, jitter) * 1.2,
    ]


def _load_model_if_available() -> None:
    global _model, _model_load_attempted, _model_load_error

    if _model_load_attempted:
        return

    _model_load_attempted = True

    checkpoint_path = Path(os.getenv("MODEL_CHECKPOINT", "quantum/checkpoints/latest.pt"))

    try:
        import torch

        from quantum.pennylane_vqc import QuantumDDQN

        model = QuantumDDQN()
        if checkpoint_path.exists():
            state_dict = torch.load(checkpoint_path, map_location="cpu")
            model.load_state_dict(state_dict)
        model.eval()
        _model = model
    except Exception as exc:
        _model = None
        _model_load_error = str(exc)


def _infer_q_values(vector: list[float]) -> list[float]:
    _load_model_if_available()

    if _model is None:
        return _placeholder_q_values(vector)

    import torch

    with torch.no_grad():
        tensor_state = torch.tensor(vector, dtype=torch.float32).unsqueeze(0)
        logits = _model(tensor_state).squeeze(0).tolist()

    return [float(value) for value in logits]


@router.get("/action", response_model=ActionResponse)
async def get_action(session_id: str = Query(..., min_length=1)) -> ActionResponse:
    key = f"state:{session_id}"

    try:
        cached_value = await redis_client.get(key)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Redis unavailable: {exc}") from exc

    if cached_value is None:
        raise HTTPException(status_code=404, detail="No state found for session_id")

    try:
        vector = json.loads(cached_value)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail="Corrupt cached state payload") from exc

    if not isinstance(vector, list) or len(vector) != STATE_VECTOR_DIM:
        raise HTTPException(status_code=422, detail="State vector shape is invalid")

    q_values = _infer_q_values([float(value) for value in vector])

    if len(q_values) != ACTION_SPACE:
        raise HTTPException(status_code=500, detail="Policy output shape is invalid")

    argmax_index = max(range(len(q_values)), key=lambda idx: q_values[idx])
    confidence = _softmax_confidence(q_values)
    gated = confidence < CONFIDENCE_GATE
    action_id = 0 if gated else argmax_index

    return ActionResponse(
        action_id=action_id,
        confidence=confidence,
        gated=gated,
        action_name=ACTION_NAMES.get(action_id, "unknown"),
    )
