import { v4 as uuidv4 } from 'uuid';
import { STATE_VECTOR_DIM, TELEMETRY_INTERVAL } from '../shared_config.js';

/**
 * Vanilla JS Telemetry Module
 * Computes and POSTs a normalised 5-signal state vector to /api/state every 30 seconds.
 */

// Persistent state vectors (stored in sessionStorage for cross-page persistence)
const _getStoredVector = () => {
  if (typeof window === 'undefined') return [0, 0, 1, 0, 1.0];
  const stored = window.sessionStorage.getItem('neuroadapt_last_state_vector');
  return stored ? JSON.parse(stored) : [0, 0, 1, 0, 1.0];
};
const _saveVector = (v) => {
  if (typeof window !== 'undefined')
    window.sessionStorage.setItem('neuroadapt_last_state_vector', JSON.stringify(v));
};

// Module state
let sessionId = null;
let flushIntervalId = null;
let lastStateVector = _getStoredVector();

// 30-second window counters and state
let timeOnSlideMs = 0;
let slideVisibilityStartTime = null;
let lastInteractionTimestamp = Date.now();
let mouseSamples = []; // Array of {timestamp, x, y}
let visibilityHiddenCount = 0;
let preferenceDelta = 1.0; // Initialize to 1.0: users staying in default text mode are rewarded

// Lesson tracking state (for event-based completion flushing)
let lessonStartTime = null;
let lessonMetadata = null; // {subject, topic, total_slides, current_slide}

// Constants
const AVERAGE_READING_TIME_MS = 250; // ms per word
const MAX_VELOCITY_CAP = 3; // px/ms
const FOCUS_PERSISTENCE_THRESHOLD = 5; // visibility changes for normalization

/**
 * Clamp a value to the range [0, 1]
 */
function clamp(value, min = 0, max = 1) {
  return Math.max(min, Math.min(max, value));
}

/**
 * Generate or retrieve session ID
 */
function getSessionId() {
  if (!sessionId) {
    const storedSessionId =
      typeof window !== 'undefined'
        ? window.sessionStorage.getItem('neuroAdapt_sessionId')
        : null;
    sessionId = storedSessionId || `session_${uuidv4()}`;
    if (typeof window !== 'undefined' && !storedSessionId) {
      window.sessionStorage.setItem('neuroAdapt_sessionId', sessionId);
    }
  }
  return sessionId;
}

/**
 * Compute Semantic Dwell Ratio
 * Formula: timeOnSlide_ms / (wordCount × averageReadingTime_ms), clamped to [0, 1]
 */
function computeSemanticDwellRatio() {
  const wordCountElement = document.querySelector('[data-word-count]');
  const wordCount = wordCountElement ? parseInt(wordCountElement.dataset.wordCount, 10) : 200;

  if (wordCount === 0) return 0;

  const denominator = wordCount * AVERAGE_READING_TIME_MS;
  const dwellRatio = timeOnSlideMs / denominator;

  return clamp(dwellRatio);
}

/**
 * Compute Interaction Jitter
 * Rolling standard deviation of mouse velocity over the last 10 samples.
 * Normalise by dividing by max velocity cap, then clamp to [0, 1].
 */
function computeInteractionJitter() {
  if (mouseSamples.length < 2) return 0;

  const recentSamples = mouseSamples.slice(-10);
  const velocities = [];

  for (let i = 1; i < recentSamples.length; i++) {
    const prev = recentSamples[i - 1];
    const curr = recentSamples[i];

    const dx = curr.x - prev.x;
    const dy = curr.y - prev.y;
    const distance = Math.sqrt(dx * dx + dy * dy);
    const timeDelta = curr.timestamp - prev.timestamp;

    if (timeDelta > 0) {
      const velocity = distance / timeDelta;
      velocities.push(velocity);
    }
  }

  if (velocities.length === 0) return 0;

  // Compute standard deviation
  const mean = velocities.reduce((a, b) => a + b, 0) / velocities.length;
  const variance = velocities.reduce((sum, v) => sum + (v - mean) ** 2, 0) / velocities.length;
  const stdDev = Math.sqrt(variance);

  const normalizedJitter = stdDev / MAX_VELOCITY_CAP;
  return clamp(normalizedJitter);
}

/**
 * Compute Focus Persistence
 * 1 - min(visibilityHiddenCount / threshold, 1)
 * 0 tab switches = 1.0 (fully focused), ≥ 5 = 0.0
 */
function computeFocusPersistence() {
  const normalizedCount = Math.min(visibilityHiddenCount / FOCUS_PERSISTENCE_THRESHOLD, 1);
  return clamp(1 - normalizedCount);
}

/**
 * Compute Stall Duration
 * (Date.now() - lastInteractionTimestamp) / 30000, clamped to [0, 1]
 */
function computeStallDuration() {
  const timeSinceLastInteraction = Date.now() - lastInteractionTimestamp;
  const stallRatio = timeSinceLastInteraction / TELEMETRY_INTERVAL;
  return clamp(stallRatio);
}

/**
 * Reset window counters for the next 30-second interval
 */
function resetWindowCounters() {
  timeOnSlideMs = 0;
  slideVisibilityStartTime = Date.now();
  mouseSamples = [];
  visibilityHiddenCount = 0;
}

/**
 * Attach all event listeners
 */
function attachEventListeners() {
  // Track slide visibility (element with data-slide attribute or data-visible)
  document.addEventListener('visibilitychange', handleVisibilityChange);

  // Track mouse movement for interaction jitter
  document.addEventListener('mousemove', handleMouseMove);

  // Track interactions (mouse, keyboard, scroll)
  document.addEventListener('mousedown', handleInteraction);
  document.addEventListener('keydown', handleInteraction);
  document.addEventListener('scroll', handleInteraction);

  // Track slide visibility - when a slide comes into view (optional: listen for custom events)
  // This could also be triggered by framework-specific lifecycle events
  if (slideVisibilityStartTime === null) {
    slideVisibilityStartTime = Date.now();
  }
}

/**
 * Handle visibility change (tab switch)
 */
function handleVisibilityChange() {
  if (document.visibilityState === 'hidden') {
    visibilityHiddenCount++;
  }
}

/**
 * Handle mouse movement - track velocity samples
 */
function handleMouseMove(event) {
  const now = Date.now();
  mouseSamples.push({
    timestamp: now,
    x: event.clientX,
    y: event.clientY,
  });

  // Keep only the last 20 samples to manage memory
  if (mouseSamples.length > 20) {
    mouseSamples.shift();
  }

  // Update last interaction timestamp
  lastInteractionTimestamp = now;
}

/**
 * Handle user interaction (mouse click, keyboard, scroll)
 */
function handleInteraction() {
  lastInteractionTimestamp = Date.now();
}

/**
 * Compute all 5 normalised signal values
 */
function computeStateVector() {
  // Update timeOnSlideMs based on elapsed time since slideVisibilityStartTime
  if (slideVisibilityStartTime !== null && document.visibilityState === 'visible') {
    timeOnSlideMs = Date.now() - slideVisibilityStartTime;
  }

  const dwellRatio = computeSemanticDwellRatio();
  const jitter = computeInteractionJitter();
  const focus = computeFocusPersistence();
  const stall = computeStallDuration();

  return [dwellRatio, jitter, focus, stall, preferenceDelta];
}

/**
 * Get the last computed state vector (used by Dashboard on mount)
 */
function getLastStateVector() {
  return lastStateVector;
}

/**
 * Flush telemetry: compute state vector and POST to /api/state
 */
async function flush() {
  try {
    const stateVector = computeStateVector();
    const [dwell, jitter, focus, stall, pref_delta] = stateVector;

    console.log('[Observer] Flush triggered:', {
      timeOnSlideMs,
      mouseSamplesCount: mouseSamples.length,
      visibilityHiddenCount,
      lastInteractionTimestamp,
      now: Date.now(),
      dwell, jitter, focus, stall, pref_delta,
      timestamp: new Date().toLocaleTimeString(),
    });

    const payload = {
      session_id: getSessionId(),
      timestamp: new Date().toISOString(),
      state_vector: stateVector,
    };

    const response = await fetch('/api/state', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      console.warn(`[Observer] POST /api/state returned status ${response.status}`);
    }

    // Call debug callback if it exists
    if (typeof window.__onObserverFlush === 'function') {
      const callbackData = {
        dwell, jitter, focus, stall, pref_delta,
        timestamp: new Date().toLocaleTimeString()
      };
      console.log('[Observer] Calling flush callback with data:', callbackData);
      window.__onObserverFlush(callbackData);
    } else {
      console.log('[Observer] No flush callback registered');
    }

    // Store last state vector for Dashboard to read on mount
    lastStateVector = stateVector;
    _saveVector(stateVector);

    // Reset counters for the next 30-second window
    resetWindowCounters();
  } catch (error) {
    console.error('[Observer] Failed to flush telemetry:', error);
  }
}

/**
 * Initialize the Observer module
 * - Attach event listeners
 * - Start the 30-second flush interval
 */
function init() {
  if (flushIntervalId !== null) {
    console.warn('[Observer] Already initialised; skipping duplicate init');
    return;
  }

  attachEventListeners();
  resetWindowCounters();

  // Start interval to flush every 30 seconds
  flushIntervalId = setInterval(flush, TELEMETRY_INTERVAL);

  console.log('[Observer] Initialised with 30-second telemetry interval');
}

/**
 * Set the preference delta externally
 * Updated by other components in later phases.
 */
function setPreferenceDelta(value) {
  const newValue = clamp(value, 0, 1);
  const oldValue = preferenceDelta;
  preferenceDelta = newValue;

  console.log('[Observer] Preference Delta Updated:', {
    old: oldValue,
    new: newValue,
    changed: oldValue !== newValue,
    timestamp: new Date().toLocaleTimeString(),
  });
}

/**
 * Start tracking a lesson
 * Called when user enters lesson view
 */
function startLesson(metadata) {
  lessonStartTime = Date.now();
  lessonMetadata = {
    subject: metadata?.subject || 'unknown',
    topic: metadata?.topic || 'unknown',
    total_slides: metadata?.total_slides || 0,
    current_slide: metadata?.current_slide || 0,
  };

  console.log('[Observer] Lesson started:', {
    metadata: lessonMetadata,
    startTime: new Date(lessonStartTime).toLocaleTimeString(),
  });
}

/**
 * End lesson and flush completion telemetry immediately
 * Called when user clicks "End Lesson" or navigates away from lesson view
 * Returns the duration in milliseconds
 */
async function endLesson(metadata = null) {
  if (!lessonStartTime) {
    console.warn('[Observer] endLesson called but no lesson was started');
    return 0;
  }

  const duration = Date.now() - lessonStartTime;
  const stateVector = computeStateVector();
  const [dwell, jitter, focus, stall, pref_delta] = stateVector;

  // Update metadata if provided (e.g., final slide count)
  if (metadata) {
    lessonMetadata = { ...lessonMetadata, ...metadata };
  }

  console.log('[Observer] Lesson ending with immediate flush:', {
    durationMs: duration,
    lessonMetadata,
    stateVector: { dwell, jitter, focus, stall, pref_delta },
    timestamp: new Date().toLocaleTimeString(),
  });

  try {
    const payload = {
      session_id: getSessionId(),
      timestamp: new Date().toISOString(),
      state_vector: stateVector,
      event_type: 'lesson_completion',
      lesson_metadata: lessonMetadata,
      duration_ms: duration,
    };

    const response = await fetch('/api/state', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      console.warn(`[Observer] POST /api/state (lesson completion) returned status ${response.status}`);
    } else {
      console.log('[Observer] Lesson completion telemetry sent successfully');
    }

    // Store for dashboard
    lastStateVector = stateVector;
    _saveVector(stateVector);
    resetWindowCounters();
  } catch (error) {
    console.error('[Observer] Failed to send lesson completion telemetry:', error);
  } finally {
    lessonStartTime = null;
    lessonMetadata = null;
  }

  return duration;
}

/**
 * Update current lesson metadata (e.g., when slide changes)
 */
function updateLessonMetadata(updates) {
  if (lessonMetadata) {
    lessonMetadata = { ...lessonMetadata, ...updates };
  }
}

/**
 * Cleanup: stop the flush interval and remove event listeners
 */
function destroy() {
  if (flushIntervalId !== null) {
    clearInterval(flushIntervalId);
    flushIntervalId = null;
  }

  document.removeEventListener('visibilitychange', handleVisibilityChange);
  document.removeEventListener('mousemove', handleMouseMove);
  document.removeEventListener('mousedown', handleInteraction);
  document.removeEventListener('keydown', handleInteraction);
  document.removeEventListener('scroll', handleInteraction);

  console.log('[Observer] Destroyed');
}

// Named exports
export { init, flush, setPreferenceDelta, destroy, getLastStateVector, startLesson, endLesson, updateLessonMetadata };
