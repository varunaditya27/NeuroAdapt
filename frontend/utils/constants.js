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
 * Study mode metadata for adaptive mode selection
 * Maps study modes to their UI representation and descriptions
 */
export const STUDY_MODES = {
  text: {
    label: 'Text Mode',
    description: 'Read at your own pace with bite-sized text content',
    icon: '📖',
  },
  video: {
    label: 'Video Mode',
    description: 'Learn through visual explanations and demonstrations',
    icon: '📹',
  },
  audio: {
    label: 'Audio Mode',
    description: 'Listen to narrated explanations (with sensory breaks)',
    icon: '🎧',
  },
  quiz: {
    label: 'Quiz Mode',
    description: 'Test your knowledge with interactive questions',
    icon: '✓',
  },
  sensory_break: {
    label: 'Sensory Break',
    description: 'Take a moment to reset with a guided break',
    icon: '🌬️',
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
