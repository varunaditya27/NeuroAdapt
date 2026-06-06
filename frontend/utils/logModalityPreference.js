/**
 * Modality Preference Event Logger
 *
 * Single, canonical emission path for recording modality preference events.
 * All user-initiated content format choices must go through this function.
 *
 * Do NOT inline POST calls in individual components — always use this helper.
 */

const API_ENDPOINT = '/api/analytics/modality-event';

/**
 * Log a modality preference event to the backend.
 *
 * @param {string} modality - The modality identifier:
 *   'video' | 'audio' | 'simplified_text' | 'quiz' | 'sensory_break' | 'standard'
 * @param {string} source - How the choice was made:
 *   'selection' | 'acceptance' | 'dismissal'
 * @returns {Promise<boolean>} True if the event was recorded successfully.
 */
export default async function logModalityPreference(modality, source = 'selection') {
  try {
    const response = await fetch(API_ENDPOINT, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ modality, source }),
    });

    if (!response.ok) {
      console.warn('[logModalityPreference] Failed to log event:', {
        status: response.status,
        modality,
        source,
      });
      return false;
    }

    console.log('[logModalityPreference] Event logged:', { modality, source });
    return true;
  } catch (error) {
    console.error('[logModalityPreference] Error logging event:', error);
    return false;
  }
}