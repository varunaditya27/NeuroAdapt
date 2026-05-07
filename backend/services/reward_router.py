import random
from typing import Optional


def placeholder_reward(event: str, chosen_format: Optional[str] = None) -> float:
    event_to_reward = {
        "complete": 1.0,
        "answer_correct": 0.5,
        "format_choice": 0.2 if chosen_format else 0.0,
        "energy_bar": -2.0,
    }
    return float(event_to_reward.get(event, 0.0))


def compute_reward(
    event: str,
    chosen_format: Optional[str] = None,
    state: list[float] | None = None,
    action: int = 0,
    next_state: list[float] | None = None,
    done: bool = False,
) -> float:
    """Use quantum reward when state context is present, else event fallback."""

    if state is not None and next_state is not None:
        try:
            from quantum.reward import compute_reward as teammate_compute_reward  # type: ignore

            return float(
                teammate_compute_reward(
                    state,
                    action,
                    next_state,
                    done,
                    rng=random.Random(0),
                    quiz_correct_p=1.0 if event == "answer_correct" else 0.0,
                )
            )
        except Exception:
            pass

    return placeholder_reward(event=event, chosen_format=chosen_format)
