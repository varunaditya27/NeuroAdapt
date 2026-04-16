"""
Hyperfocus Protective Gate — Pre-emption Logic to Preserve Flow States

================================================================================
PURPOSE:
    Detects rare ADHD hyperfocus states (high productivity).
    Blocks ALL interventions when hyperfocus is active (protect flow).
    Overrides orchestrator decision to action_id = 0 (hold course).

DEPENDENCIES:
    - None (pure logic/computation)

INPUT:
    state_vector: dict
    {
        "hyperfocus_composite": float (0.0-1.0),
        "attention_switching": float,
        "regression_count": int,
        "task_engagement": float,
        "time_on_task": int (seconds),
        ...
    }

HYPERFOCUS COMPOSITE CALCULATION:
    hyperfocus_composite = (
        0.4 * (1 - attention_switching) +    # Low task-switching
        0.3 * engagement_level +              # High engagement
        0.2 * (1 - micro_pause_ratio) +       # Few breaks
        0.1 * time_on_task_bonus              # Sustained duration
    )
    
    Range: 0.0 (no hyperfocus) to 1.0 (complete hyperfocus)

DETECTION THRESHOLD:
    hyperfocus_composite > 0.75 → Hyperfocus ACTIVE
    
    Interpretation:
    - < 0.3: No hyperfocus, normal intervention mode
    - 0.3-0.6: Partial attention (allow interventions)
    - 0.6-0.75: Deep focus (caution, allow light interventions)
    - > 0.75: HYPERFOCUS (protect at all costs, no interventions)

RESEARCH BASIS:
    - Russell Barkley: Hyperfocus is rare ADHD strength (not impairment)
    - Can last 2-4 hours if uninterrupted
    - Interruptions reset hyperfocus state (90+ minute recovery)
    - Protecting hyperfocus → major productivity gains
    - Nadeau: "Honor the hyperfocus"

BEHAVIOR:
    IF hyperfocus_composite > 0.75:
        → Pre-emption: Override action_id to 0
        → Block ALL UI changes (no content interventions)
        → No audio, no visual changes, no quizzes
        → Learner sees "In Flow" indicator only
        → Continue passive monitoring (don't lose state_vector)
        → EXIT pre-emption only when:
            - hyperfocus_composite < 0.60 (for 30+ seconds)
            - Explicit learner "break" button clicked
            - Session timeout (> 2 hours without break)

PROTECTION WINDOW:
    Once hyperfocus detected:
    1. Activate "do not disturb" mode (30+ second confirmation window)
    2. Only exit if hyperfocus_composite < 0.60 for sustained period
    3. Gradually re-enable interventions as composite drops

OPTIONAL UI FEEDBACK:
    - Display "In Flow" badge (subtle, non-intrusive)
    - Show estimated time until re-engagement possible
    - Offer "Break?" button (optional)
    - Log hyperfocus episodes for learner insight

EDGE CASES:
    - High engagement but multiple regressions → Not true hyperfocus
    - Hyperfocus detection but < 30 seconds → Ignore (too brief)
    - Rapid on/off cycles → Indicate distractibility, not true hyperfocus
    - Gaming vs. learning → Same logic applies

LOGGING:
    - Hyperfocus activation: timestamp, duration, composite score
    - Pre-empted actions: what would have been sent (for analytics)
    - Exit reason: dropped composite vs. explicit break

METRICS:
    - Count of hyperfocus episodes
    - Average duration per episode
    - Pre-emption count per session
    - Sessions with at least one hyperfocus episode

KEY FUNCTIONS:
    - check_hyperfocus(state_vector) → bool
    - get_hyperfocus_composite(state_vector) → float
    - should_pre_empt(hyperfocus_composite, current_pre_emption_state) → bool
    - get_pre_emption_exit_criteria(initial_composite, duration) → dict

ERROR HANDLING:
    - Missing state_vector fields: Use conservative defaults (0.0)
    - Invalid composite scores: Clamp to [0, 1]
    - Return valid pre-emption decision (default to no pre-emption)

CONSTRAINTS:
    - Execution: < 1ms (instant)
    - No external I/O
    - Deterministic

INTEGRATION:
    - Called by action_router BEFORE routing
    - If pre-empt: Override action_id to 0, skip generator calls
    - Called by latency_budget for pre-emption window tracking
    - Results logged to PostgreSQL session table

RELATED:
    - action_router : Uses pre-emption decision
    - latency_budget : Tracks pre-emption window duration
    - Frontend : Displays "In Flow" badge

================================================================================
"""

# TODO: Implement check_hyperfocus() main function
# TODO: Implement hyperfocus_composite calculation
# TODO: Define detection threshold (0.75)
# TODO: Implement should_pre_empt() decision logic
# TODO: Track pre-emption window (requires state management)
# TODO: Implement exit criteria checking
# TODO: Log hyperfocus episodes
# TODO: Add error handling for missing fields
# TODO: Add metrics recording
