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

# TODO: Define state_vector input schema
# TODO: Create lookup tables by cognitive_load
# TODO: Implement categorization logic
# TODO: Implement delta application functions
# TODO: Implement hyperfocus lock check
# TODO: Generate CSS variables output
# TODO: Add validation of ranges
# TODO: Add error handling
# TODO: Add logging/metrics
