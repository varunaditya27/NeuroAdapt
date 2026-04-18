"""
Typography Morpher — CSS State Machine for Cognitive State (Tier 1, Instant <1 second)

================================================================================
PURPOSE:
    Generate CSS variables for typography based on cognitive state.
    Font size, weight, spacing morph to match learner's processing capacity.
    Rules compiled from design_system.md research.

TIER: 1 (Instant, <1 second)

DEPENDENCIES:
    - None (pure data/logic, no external calls)

EXTERNAL SERVICES:
    - None (frontend renders CSS)

INPUT:
    state_vector: dict
    {
        "cognitive_load": float (0.0-1.0),
        "eye_gaze_stability": float (0.0-1.0),
        "regression_count": int,
        "attention_switching": float (0.0-1.0),
        "hyperfocus_composite": float (0.0-1.0)
    }

OUTPUT (CSS Variables):
    {
        "--font-size-base": "16px" | "18px" | "20px" | "22px",
        "--font-weight-body": "400" | "500" | "600",
        "--line-height": "1.4" | "1.6" | "1.8" | "2.0",
        "--letter-spacing": "0px" | "0.5px" | "1px" | "1.5px",
        "--paragraph-margin": "8px" | "12px" | "16px" | "20px",
        "--color-contrast": "normal" | "high" | "enhanced",
        "--animation-duration": "0.3s" | "0.5s" | "0.8s" | "1.2s"
    }

MORPHING RULES:
    Cognitive Load (primary driver):
        - LOW (< 0.3) → Large fonts, wide spacing (easier scanning)
        - MODERATE (0.3-0.6) → Standard size, medium spacing (default)
        - HIGH (0.6-0.9) → Slightly reduced, tighter spacing (focus)
        - CRITICAL (> 0.9) → Minimal text, maximized spacing (extreme)

    Eye Gaze Stability (affects layout):
        - STABLE (> 0.7) → Normal sized text, compact layout
        - UNSTABLE (< 0.7) → Larger text, extra line spacing (easier tracking)

    Regression Count (reading difficulty):
        - LOW (< 3) → Standard spacing
        - MODERATE (3-6) → +25% line spacing
        - HIGH (> 6) → +50% line spacing + bolded text (anchor points)

    Attention Switching (affects animation):
        - SLOW (< 0.3) → Slower animations, easier tracking
        - NORMAL (0.3-0.7) → Standard animations
        - RAPID (> 0.7) → Faster animations, reduced motion

    Hyperfocus State (protective):
        - ACTIVE (> 0.75) → NO changes, lock current style

STATE MACHINE:
    ```
    Input: state_vector
    ↓
    Compute primary drivers: [cognitive_load, gaze_stability, regressions]
    ↓
    Apply base rules by cognitive_load
    ↓
    Adjust for gaze_stability (line spacing)
    ↓
    Adjust for regressions (font weight + spacing)
    ↓
    Adjust for attention_switching (animation speed)
    ↓
    Check hyperfocus: If > 0.75, lock all values (no change)
    ↓
    Generate CSS variables
    ↓
    Return to frontend
    ```

ALGORITHM:
    1. Read state_vector inputs
    2. Categorize cognitive_load into bucket
    3. Look up base CSS from lookup table
    4. Apply deltas for gaze_stability
    5. Apply deltas for regressions
    6. Apply deltas for attention_switching
    7. Check hyperfocus → if active, override to "no change"
    8. Generate CSS string

LOOKUP TABLES:
    ```python
    BASE_CSS_BY_LOAD = {
        "low": {
            "font-size": "20px",
            "font-weight": "400",
            "line-height": "1.8",
            ...
        },
        "moderate": {
            "font-size": "16px",
            "font-weight": "400",
            "line-height": "1.6",
            ...
        },
        ...
    }
    ```

KEY FUNCTIONS:
    - morph_typography(state_vector) → dict
    - categorize_cognitive_load(load: float) → str
    - apply_gaze_stability_delta(base_css, stability) → dict
    - apply_regression_delta(css, regression_count) → dict
    - apply_attention_delta(css, switching_rate) → dict
    - check_hyperfocus_lock(css, hyperfocus_score) → dict

ERROR HANDLING:
    - Missing state_vector field: Use default value
    - Invalid state ranges: Clamp to [0, 1]
    - Return valid CSS variables (no crashes)

CONSTRAINTS:
    - Execution: < 1ms (instant)
    - No external I/O
    - Deterministic (same input → same output)

OPTIMIZATION:
    - Pre-compute lookup tables on startup
    - Memoize common state vectors (optional)

INTEGRATION:
    - Called by action_router for every response
    - Frontend receives CSS variables in response JSON
    - ContentRenderer applies CSS via style.setProperty()
    - Changes animate smoothly (transition: all 0.5s ease)

RELATED:
    - Called alongside text_simplify
    - Used by chunk_renderer for chunk display
    - Coordinates with kokoro_tts animation speed

================================================================================
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Optional


BASE_CSS_BY_LOAD: Dict[str, Dict[str, str]] = {
    "low": {
        "--font-size-base": "20px",
        "--font-weight-body": "400",
        "--line-height": "1.8",
        "--letter-spacing": "0.8px",
        "--paragraph-margin": "16px",
        "--color-contrast": "normal",
        "--animation-duration": "0.6s",
    },
    "moderate": {
        "--font-size-base": "18px",
        "--font-weight-body": "400",
        "--line-height": "1.6",
        "--letter-spacing": "0.4px",
        "--paragraph-margin": "12px",
        "--color-contrast": "normal",
        "--animation-duration": "0.5s",
    },
    "high": {
        "--font-size-base": "16px",
        "--font-weight-body": "500",
        "--line-height": "1.5",
        "--letter-spacing": "0.2px",
        "--paragraph-margin": "10px",
        "--color-contrast": "high",
        "--animation-duration": "0.4s",
    },
    "critical": {
        "--font-size-base": "22px",
        "--font-weight-body": "600",
        "--line-height": "2.0",
        "--letter-spacing": "1.2px",
        "--paragraph-margin": "20px",
        "--color-contrast": "enhanced",
        "--animation-duration": "0.8s",
    },
}


def _clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, value))


def categorize_cognitive_load(load: float) -> str:
    """Bucket cognitive load for style lookup."""
    load = _clamp(load)
    if load < 0.3:
        return "low"
    if load < 0.6:
        return "moderate"
    if load < 0.9:
        return "high"
    return "critical"


def _parse_px(value: str) -> float:
    return float(value.replace("px", "").strip())


def _format_px(value: float) -> str:
    return f"{value:.1f}px" if value % 1 else f"{int(value)}px"


def _parse_float(value: str) -> float:
    return float(value.strip())


def _format_float(value: float) -> str:
    return f"{value:.2f}".rstrip("0").rstrip(".")


def apply_gaze_stability_delta(css: Dict[str, str], gaze_stability: float) -> Dict[str, str]:
    """Adjust line-height and spacing when gaze is unstable."""
    output = deepcopy(css)
    stability = _clamp(gaze_stability)
    if stability < 0.7:
        line_height = _parse_float(output["--line-height"])
        letter_spacing = _parse_px(output["--letter-spacing"])
        output["--line-height"] = _format_float(min(2.2, line_height + 0.15))
        output["--letter-spacing"] = _format_px(min(2.0, letter_spacing + 0.3))
    return output


def apply_regression_delta(css: Dict[str, str], regression_count: int) -> Dict[str, str]:
    """Increase readability support for heavy regression patterns."""
    output = deepcopy(css)
    if regression_count > 6:
        line_height = _parse_float(output["--line-height"])
        paragraph_margin = _parse_px(output["--paragraph-margin"])
        output["--font-weight-body"] = "600"
        output["--line-height"] = _format_float(min(2.3, line_height + 0.2))
        output["--paragraph-margin"] = _format_px(min(24.0, paragraph_margin + 4.0))
        output["--color-contrast"] = "enhanced"
    elif regression_count >= 3:
        line_height = _parse_float(output["--line-height"])
        output["--line-height"] = _format_float(min(2.1, line_height + 0.1))
        if output["--font-weight-body"] == "400":
            output["--font-weight-body"] = "500"
    return output


def apply_attention_delta(css: Dict[str, str], switching_rate: float) -> Dict[str, str]:
    """Tune transition speed based on switching cadence."""
    output = deepcopy(css)
    switching_rate = _clamp(switching_rate)
    if switching_rate > 0.7:
        output["--animation-duration"] = "0.3s"
    elif switching_rate < 0.3:
        output["--animation-duration"] = "0.8s"
    return output


def morph_typography(
    state_vector: Optional[Dict[str, Any]],
    previous_css: Optional[Dict[str, str]] = None,
) -> Dict[str, str]:
    """
    Generate typography CSS variables from learner cognitive state.

    Returns CSS custom properties keyed by variable name.
    """
    state = state_vector or {}
    load = float(state.get("cognitive_load", 0.5))
    gaze_stability = float(state.get("eye_gaze_stability", 0.5))
    regression_count = int(state.get("regression_count", 0))
    attention_switching = float(state.get("attention_switching", 0.5))
    hyperfocus_composite = float(state.get("hyperfocus_composite", 0.0))

    if _clamp(hyperfocus_composite) > 0.75 and previous_css:
        return deepcopy(previous_css)

    bucket = categorize_cognitive_load(load)
    css = deepcopy(BASE_CSS_BY_LOAD[bucket])
    css = apply_gaze_stability_delta(css, gaze_stability)
    css = apply_regression_delta(css, regression_count)
    css = apply_attention_delta(css, attention_switching)

    if _clamp(hyperfocus_composite) > 0.75:
        css["--animation-duration"] = "0s"

    return css
