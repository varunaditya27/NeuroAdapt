/**
 * Format to preference delta numeric mapping
 * Used by PreferenceDelta widget to convert format selection to a normalized value
 */
export const FORMAT_TO_DELTA = {
  text: 0.0,
  audio: 0.33,
  video: 0.67,
  quiz: 1.0,
};

/**
 * Delta to format reverse mapping
 */
export const DELTA_TO_FORMAT = {
  0.0: 'text',
  0.33: 'audio',
  0.67: 'video',
  1.0: 'quiz',
};

/**
 * Format metadata for UI
 */
export const FORMAT_METADATA = {
  text: {
    label: 'Read it',
    subtext: 'Bite-sized text, at your pace',
    icon: 'BookOpen',
  },
  audio: {
    label: 'Listen to it',
    subtext: 'Narrated explanation',
    icon: 'Headphones',
  },
  video: {
    label: 'Watch it',
    subtext: 'Visual walkthrough',
    icon: 'Play',
  },
  quiz: {
    label: 'Test yourself',
    subtext: 'Questions and answers',
    icon: 'CheckCircle',
  },
};

/**
 * Quiz result messages
 */
export const QUIZ_RESULT_MESSAGES = {
  encouragement: ['Nice one!', 'Correct!', 'Spot on!', 'You got it!', 'Well done!'],
  correction: 'Not quite - the right answer is highlighted.',
  goodScore: 'Great work - you\'ve got this.',
  needsReview: 'Good effort. Review the material and try again when you are ready.',
};
