/**
 * Preference Delta Calculator
 * Calculates dynamic preference delta based on model prediction vs user selection
 * - Positive score (0.7-1.0) if user selects model's recommended mode
 * - Heavy negative score (0.0-0.2) if user selects different mode
 */

/**
 * Map action_id to predicted content format
 * Based on action semantics:
 * - 0: hold_course → maintain current format (neutral, returns null)
 * - 1: soft_nudge → text format (simplified)
 * - 2: simplify_text → text format
 * - 3: switch_video → video format
 * - 4: gamified_task → quiz format
 * - 5: sensory_break → audio format
 * 
 * @param {number} actionId - The action ID from model
 * @returns {string|null} - Format name ('text', 'video', 'audio', 'quiz') or null if no clear prediction
 */
export function actionIdToFormat(actionId) {
  const mapping = {
    0: null, // hold_course - no strong format recommendation
    1: 'text', // soft_nudge - likely text
    2: 'text', // simplify_text
    3: 'video', // switch_video
    4: 'quiz', // gamified_task
    5: 'audio', // sensory_break
  };
  return mapping[actionId] ?? null;
}

/**
 * Calculate preference delta based on model prediction vs user selection
 * 
 * @param {string|null} predictedFormat - Format predicted by model (from action)
 * @param {string} userSelectedFormat - Format selected by user ('text', 'video', 'audio', 'quiz')
 * @returns {number} - Preference delta value between 0 and 1
 */
export function calculatePreferenceDelta(predictedFormat, userSelectedFormat) {
  // If model didn't have a clear prediction, use a neutral value
  if (!predictedFormat) {
    // No prediction = user's choice is neither reinforced nor punished
    // Return mid-range value based on their selection
    return 0.5;
  }

  // If user selected the format the model predicted
  if (predictedFormat === userSelectedFormat) {
    // Positive reward: user is following model's recommendation
    // Range: 0.75-1.0 (strong positive)
    return 0.85 + Math.random() * 0.15; // 0.85-1.0
  }

  // User selected a different format than model predicted
  // Heavy negative reward: user is deviating from model's recommendation
  // Range: 0.0-0.2 (strong negative)
  return Math.random() * 0.2; // 0.0-0.2
}

/**
 * Fetch the model's recommended action for current session
 * Returns null if fetch fails or action can't be determined
 * 
 * @param {string} sessionId - Current session ID
 * @returns {Promise<number|null>} - Action ID from model or null
 */
export async function fetchModelPredictedAction(sessionId) {
  try {
    console.log('[PreferenceDelta] Fetching model action for session:', sessionId);
    
    const response = await fetch(`/api/action?session_id=${encodeURIComponent(sessionId)}`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
    });

    if (!response.ok) {
      console.warn('[PreferenceDelta] Failed to fetch action:', {
        status: response.status,
        statusText: response.statusText,
      });
      return null;
    }

    const data = await response.json();
    console.log('[PreferenceDelta] Action response:', data);
    
    // Response should have action_id field
    if (typeof data.action_id === 'number') {
      console.log('[PreferenceDelta] Model predicted action:', {
        action_id: data.action_id,
        action_name: data.action_name,
        confidence: data.confidence,
      });
      return data.action_id;
    }

    return null;
  } catch (error) {
    console.error('[PreferenceDelta] Error fetching model prediction:', error);
    return null;
  }
}

/**
 * Complete flow: fetch model prediction and calculate preference delta
 * Falls back to comparing with current format if API call fails
 * 
 * @param {string} sessionId - Current session ID
 * @param {string} userSelectedFormat - Format user just selected
 * @param {string} currentFormat - Currently active format (for fallback comparison)
 * @returns {Promise<number>} - Calculated preference delta
 */
export async function computePreferenceDelta(sessionId, userSelectedFormat, currentFormat) {
  try {
    console.log('[PreferenceDelta] Starting computation:', {
      sessionId,
      userSelectedFormat,
      currentFormat,
      timestamp: new Date().toLocaleTimeString(),
    });

    // Try to fetch model prediction
    const actionId = await fetchModelPredictedAction(sessionId);
    console.log('[PreferenceDelta] Got action ID:', actionId);
    
    let preferenceDelta;
    let predictedFormat;
    let source;

    if (actionId !== null) {
      // Got model prediction - use it
      predictedFormat = actionIdToFormat(actionId);
      source = 'model';
      console.log('[PreferenceDelta] Mapped to predicted format:', predictedFormat);
    } else {
      // No model prediction available - use current format as fallback
      // This rewards consistency and penalizes changes
      predictedFormat = currentFormat;
      source = 'current_format_fallback';
      console.log('[PreferenceDelta] Using current format as fallback:', currentFormat);
    }
    
    preferenceDelta = calculatePreferenceDelta(predictedFormat, userSelectedFormat);
    console.log('[PreferenceDelta] Calculated preference delta:', {
      predictedFormat,
      userSelectedFormat,
      preferenceDelta,
      match: predictedFormat === userSelectedFormat,
      source,
    });

    console.log('[PreferenceDelta] Computation complete:', {
      sessionId,
      actionId,
      predictedFormat,
      userSelectedFormat,
      preferenceDelta,
      source,
    });

    return preferenceDelta;
  } catch (error) {
    console.error('[PreferenceDelta] Error computing preference delta:', error);
    // Fallback to neutral value on error
    return 0.5;
  }
}
