from typing import Optional


def placeholder_reward(event: str, chosen_format: Optional[str] = None) -> float:
    event_to_reward = {
        "complete": 1.0,
        "answer_correct": 0.5,
        "format_choice": 0.2 if chosen_format else 0.0,
        "energy_bar": -2.0,
    }
    return float(event_to_reward.get(event, 0.0))


def compute_reward(event: str, chosen_format: Optional[str] = None) -> float:
    """Use teammate reward module when present, else fallback placeholder."""

    try:
        from quantum.reward import compute_reward as teammate_compute_reward  # type: ignore

        return float(teammate_compute_reward(event=event, chosen_format=chosen_format))
    except Exception:
        return placeholder_reward(event=event, chosen_format=chosen_format)
