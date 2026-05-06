import math
import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db import get_db
from backend.models.action import ActionResponse
from backend.shared_config import ACTION_NAMES, ACTION_SPACE, CONFIDENCE_GATE, STATE_VECTOR_DIM
from backend.services.state_store import fetch_latest_state, get_cached_state

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
    scores = [0.0 for _ in range(ACTION_SPACE)]

    if max(stall, jitter) >= 0.78:
        action_id = 5
        signal_strength = max(stall, jitter)
    elif dwell >= 0.68:
        action_id = 2
        signal_strength = dwell
    elif pref_delta >= 0.68:
        action_id = 3
        signal_strength = pref_delta
    elif stall >= 0.55:
        action_id = 4
        signal_strength = stall
    elif focus <= 0.30 or jitter >= 0.55:
        action_id = 1
        signal_strength = max(1.0 - focus, jitter)
    else:
        action_id = 0
        signal_strength = focus

    scores[action_id] = 3.2 + signal_strength
    return scores


def _policy_source() -> str:
    if _model is not None:
        return "quantum_checkpoint"
    if _model_load_error:
        return "heuristic_fallback"
    return "heuristic"


def _load_model_if_available() -> None:
    global _model, _model_load_attempted, _model_load_error

    if _model_load_attempted:
        return

    _model_load_attempted = True

    checkpoint_path = Path(os.getenv("MODEL_CHECKPOINT", "/app/quantum/checkpoints/latest.pt"))

    try:
        import torch

        from quantum.pennylane_vqc import QuantumDDQN

        model = QuantumDDQN()
        if checkpoint_path.exists():
            state_dict = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
            model.load_state_dict(state_dict)
        else:
            raise FileNotFoundError(f"Checkpoint not found: {checkpoint_path}")
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
async def get_action(
    session_id: str = Query(..., min_length=1),
    db: AsyncSession = Depends(get_db),
) -> ActionResponse:
    vector = get_cached_state(session_id)
    if vector is None:
        try:
            vector = await fetch_latest_state(db, session_id)
        except Exception:
            vector = None

    if not isinstance(vector, list) or len(vector) != STATE_VECTOR_DIM:
        raise HTTPException(status_code=404, detail="No state found for session_id")

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
        q_values=q_values,
        policy_source=_policy_source(),
    )
