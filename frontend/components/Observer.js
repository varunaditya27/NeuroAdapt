import { STATE_VECTOR_DIM, TELEMETRY_INTERVAL } from '../shared_config.js';

/**
 * Vanilla JS Telemetry Module
 * Computes and POSTs a normalised 5-signal state vector to /api/state every 30 seconds.
 */

// Module state
let sessionId = null;
let flushIntervalId = null;

// 30-second window counters and state
let timeOnSlideMs = 0;
let slideVisibilityStartTime = null;
let lastInteractionTimestamp = Date.now();
let mouseSamples = []; // Array of {timestamp, x, y}
let visibilityHiddenCount = 0;
let preferenceDelta = 0.5;

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
    sessionId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
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
  const dwellRatio = computeSemanticDwellRatio();
  const jitter = computeInteractionJitter();
  const focus = computeFocusPersistence();
  const stall = computeStallDuration();

  return [dwellRatio, jitter, focus, stall, preferenceDelta];
}

/**
 * Flush telemetry: compute state vector and POST to /api/state
 */
async function flush() {
  try {
    const stateVector = computeStateVector();
    const [dwell, jitter, focus, stall, pref_delta] = stateVector;

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
      window.__onObserverFlush({
        dwell, jitter, focus, stall, pref_delta,
        timestamp: new Date().toLocaleTimeString()
      });
    }

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
  preferenceDelta = clamp(value, 0, 1);
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
export { init, flush, setPreferenceDelta, destroy };

// Default export for convenience
export default { init, flush, setPreferenceDelta, destroy };
