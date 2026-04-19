"""Typography state morphing for neurodivergent-aware rendering (Tier 1)."""

from __future__ import annotations

from typing import Any, Dict

_BASE_BY_LOAD = {
    "low": {
        "--font-size-base": "18px",
        "--font-weight-body": "400",
        "--line-height": "1.8",
        "--letter-spacing": "0.04em",
        "--paragraph-margin": "1.2em",
        "--color-contrast": "normal",
        "--animation-duration": "0.35s",
    },
    "moderate": {
        "--font-size-base": "16px",
        "--font-weight-body": "400",
        "--line-height": "1.6",
        "--letter-spacing": "0.02em",
        "--paragraph-margin": "1em",
        "--color-contrast": "normal",
        "--animation-duration": "0.3s",
    },
    "high": {
        "--font-size-base": "18px",
        "--font-weight-body": "500",
        "--line-height": "1.9",
        "--letter-spacing": "0.08em",
        "--paragraph-margin": "1.4em",
        "--color-contrast": "high",
        "--animation-duration": "0.45s",
    },
    "critical": {
        "--font-size-base": "19px",
        "--font-weight-body": "600",
        "--line-height": "2.0",
        "--letter-spacing": "0.12em",
        "--paragraph-margin": "1.6em",
        "--color-contrast": "enhanced",
        "--animation-duration": "0.5s",
    },
}


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, float(value)))


def _bucket(load: float) -> str:
    if load < 0.3:
        return "low"
    if load < 0.6:
        return "moderate"
    if load < 0.9:
        return "high"
    return "critical"


def morph_typography(
    state_vector: Dict[str, Any],
    locked_css: Dict[str, str] | None = None,
) -> Dict[str, str]:
    """Create CSS variable set from state vector signals."""
    load = _clamp(state_vector.get("cognitive_load", 0.5))
    regressions = max(0, int(state_vector.get("regression_count", 0)))
    gaze_stability = _clamp(state_vector.get("eye_gaze_stability", 0.5))
    switching = _clamp(state_vector.get("attention_switching", 0.5))
    hyperfocus = _clamp(state_vector.get("hyperfocus_composite", 0.0))

    if hyperfocus >= 0.75 and locked_css:
        return dict(locked_css)

    css = dict(_BASE_BY_LOAD[_bucket(load)])

    if gaze_stability < 0.4:
        css["--line-height"] = "2.0"
        css["--letter-spacing"] = "0.1em"

    if regressions >= 6:
        css["--font-weight-body"] = "600"
        css["--paragraph-margin"] = "1.5em"
    elif regressions >= 3:
        css["--font-weight-body"] = "500"

    if switching < 0.3:
        css["--animation-duration"] = "0.5s"
    elif switching > 0.7:
        css["--animation-duration"] = "0.25s"

    return css
