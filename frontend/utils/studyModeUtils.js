/**
 * Study Mode Management Utilities
 * Handles study mode recommendations, tracking, and preference delta computation
 */

/**
 * Map action_id to recommended study mode
 * Based on intervention strategy:
 * - 0: hold_course → stay in current mode (no recommendation)
 * - 1: soft_nudge → text mode (simplified text)
 * - 2: simplify_text → text mode (text focus)
 * - 3: switch_video → video mode (visual/motion)
 * - 4: gamified_task → quiz mode (interactive learning)
 * - 5: sensory_break → audio mode (auditory/break)
 *
 * @param {number} actionId - The action ID from model recommendation
 * @returns {string|null} - Study mode key ('text', 'video', 'audio', 'quiz') or null if no recommendation
 */
export function actionIdToStudyMode(actionId) {
  const mapping = {
    0: null, // hold_course - no mode change recommended
    1: 'text', // soft_nudge - text mode
    2: 'text', // simplify_text - text mode
    3: 'video', // switch_video - video mode
    4: 'quiz', // gamified_task - quiz mode
    5: 'audio', // sensory_break - audio mode
  };
  return mapping[actionId] ?? null;
}

/**
 * Compute preference delta based on user choice vs model recommendation
 * Reflects alignment between user action and model suggestion
 *
 * @param {string|null} suggestedMode - Mode suggested by model (or null if no clear suggestion)
 * @param {string} userChosenMode - Mode selected/confirmed by user
 * @returns {number} - prefDelta value: 1 = aligned, 0.5 = neutral/no suggestion, 0 = misaligned
 */
export function computeStudyModePrefDelta(suggestedMode, userChosenMode) {
  // No clear suggestion from model - user's choice is neither reinforced nor punished
  if (!suggestedMode) {
    return 0.5;
  }

  // User accepted the model's recommendation
  if (suggestedMode === userChosenMode) {
    // Return 1 to indicate strong alignment
    return 1;
  }

  // User rejected or ignored the model's recommendation
  // Return 0 to indicate misalignment
  return 0;
}

/**
 * Fetch model's recommended study mode for current session
 * Returns null if fetch fails or no clear recommendation
 *
 * @param {string} sessionId - Current session ID
 * @returns {Promise<string|null>} - Recommended study mode or null
 */
export async function fetchModelStudyModeRecommendation(sessionId) {
  try {
    const response = await fetch(
      `/api/action?session_id=${encodeURIComponent(sessionId)}`,
      { cache: 'no-store' }
    );

    if (!response.ok) {
      console.warn('[StudyModeUtils] Failed to fetch action:', {
        status: response.status,
      });
      return null;
    }

    const data = await response.json();

    // Check if response is gated (low confidence) - ignore recommendation
    if (data.gated || data.action_id === 0) {
      console.log('[StudyModeUtils] Recommendation gated or hold_course');
      return null;
    }

    // Map action_id to study mode
    const recommendedMode = actionIdToStudyMode(data.action_id);

    console.log('[StudyModeUtils] Model recommendation:', {
      actionId: data.action_id,
      actionName: data.action_name,
      recommendedMode,
      confidence: data.confidence,
    });

    return recommendedMode;
  } catch (error) {
    console.error('[StudyModeUtils] Error fetching recommendation:', error);
    return null;
  }
}

/**
 * Handle study mode change with preference delta computation
 * Centralizes logic for:
 * - Accepting model recommendation
 * - Rejecting recommendation
 * - Choosing alternative mode
 *
 * @param {string} userChoice - 'accept' | 'reject' | 'alternative'
 * @param {string} currentMode - Current active study mode
 * @param {string|null} suggestedMode - Mode suggested by model
 * @param {string} [alternativeMode] - If userChoice is 'alternative', the chosen mode
 * @returns {object} - { newMode, prefDelta, reason }
 */
export function handleStudyModeUserChoice(
  userChoice,
  currentMode,
  suggestedMode,
  alternativeMode = null
) {
  let newMode;
  let prefDelta;
  let reason;

  if (userChoice === 'accept' && suggestedMode) {
    // User accepted model recommendation
    newMode = suggestedMode;
    prefDelta = 1; // Strong alignment
    reason = 'user_accepted_recommendation';
  } else if (userChoice === 'reject') {
    // User kept current mode
    newMode = currentMode;
    prefDelta = 0; // No alignment
    reason = 'user_rejected_recommendation';
  } else if (userChoice === 'alternative' && alternativeMode && alternativeMode !== currentMode) {
    // User chose a different mode (not current, not suggested)
    newMode = alternativeMode;
    prefDelta = 0; // No alignment with suggestion
    reason = 'user_chose_alternative_mode';
  } else {
    // Fallback: no change
    newMode = currentMode;
    prefDelta = 0.5; // Neutral
    reason = 'no_change';
  }

  console.log('[StudyModeUtils] ✓ PrefDelta computed:', {
    userChoice,
    currentMode,
    suggestedMode,
    alternativeMode,
    newMode,
    prefDelta,
    reason,
  });

  return { newMode, prefDelta, reason };
}

/**
 * Determine if a recommendation should be shown
 * Show modal only when suggestion differs from current mode AND there's a valid suggestion
 *
 * @param {string} currentMode - Currently active study mode
 * @param {string|null} suggestedMode - Mode suggested by model
 * @returns {boolean} - Whether to show recommendation modal
 */
export function shouldShowRecommendation(currentMode, suggestedMode) {
  return suggestedMode !== null && suggestedMode !== currentMode;
}
