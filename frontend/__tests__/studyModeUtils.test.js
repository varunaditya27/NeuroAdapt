/**
 * Test Suite for Study Mode Implementation
 * Verifies core logic of studyModeUtils and integration
 */

import {
  actionIdToStudyMode,
  computeStudyModePrefDelta,
  handleStudyModeUserChoice,
  shouldShowRecommendation,
} from '@/utils/studyModeUtils';

console.log('=== Study Mode Implementation Tests ===\n');

// Test 1: actionIdToStudyMode mapping
console.log('Test 1: actionIdToStudyMode');
const testCases = [
  { actionId: 0, expected: null, desc: 'hold_course' },
  { actionId: 1, expected: 'text', desc: 'soft_nudge' },
  { actionId: 2, expected: 'text', desc: 'simplify_text' },
  { actionId: 3, expected: 'video', desc: 'switch_video' },
  { actionId: 4, expected: 'quiz', desc: 'gamified_task' },
  { actionId: 5, expected: 'audio', desc: 'sensory_break' },
];

testCases.forEach(({ actionId, expected, desc }) => {
  const result = actionIdToStudyMode(actionId);
  const pass = result === expected;
  console.log(`  ${pass ? '✓' : '✗'} Action ${actionId} (${desc}): ${result} ${pass ? '' : `(expected ${expected})`}`);
});

// Test 2: computeStudyModePrefDelta
console.log('\nTest 2: computeStudyModePrefDelta');
const prefDeltaTests = [
  { suggested: 'video', chosen: 'video', expected: 1, desc: 'Match - user aligned' },
  { suggested: 'video', chosen: 'text', expected: 0, desc: 'Mismatch - user misaligned' },
  { suggested: null, chosen: 'text', expected: 0.5, desc: 'No suggestion - neutral' },
];

prefDeltaTests.forEach(({ suggested, chosen, expected, desc }) => {
  const result = computeStudyModePrefDelta(suggested, chosen);
  const pass = result === expected;
  console.log(`  ${pass ? '✓' : '✗'} ${desc}: ${result} ${pass ? '' : `(expected ${expected})`}`);
});

// Test 3: handleStudyModeUserChoice
console.log('\nTest 3: handleStudyModeUserChoice');
const choiceTests = [
  { 
    choice: 'accept', 
    current: 'text', 
    suggested: 'video', 
    alt: null,
    expected: { newMode: 'video', prefDelta: 1 },
    desc: 'Accept recommendation' 
  },
  { 
    choice: 'reject', 
    current: 'text', 
    suggested: 'video', 
    alt: null,
    expected: { newMode: 'text', prefDelta: 0 },
    desc: 'Reject recommendation' 
  },
  { 
    choice: 'alternative', 
    current: 'text', 
    suggested: 'video', 
    alt: 'audio',
    expected: { newMode: 'audio', prefDelta: 0 },
    desc: 'Choose alternative' 
  },
];

choiceTests.forEach(({ choice, current, suggested, alt, expected, desc }) => {
  const result = handleStudyModeUserChoice(choice, current, suggested, alt);
  const modeMatch = result.newMode === expected.newMode;
  const deltaMath = result.prefDelta === expected.prefDelta;
  const pass = modeMatch && deltaMath;
  console.log(`  ${pass ? '✓' : '✗'} ${desc}`);
  if (!pass) {
    console.log(`     Got: mode=${result.newMode}, delta=${result.prefDelta}`);
    console.log(`     Expected: mode=${expected.newMode}, delta=${expected.prefDelta}`);
  }
});

// Test 4: shouldShowRecommendation
console.log('\nTest 4: shouldShowRecommendation');
const showTests = [
  { current: 'text', suggested: 'video', expected: true, desc: 'Different modes' },
  { current: 'text', suggested: 'text', expected: false, desc: 'Same mode' },
  { current: 'text', suggested: null, expected: false, desc: 'No suggestion' },
];

showTests.forEach(({ current, suggested, expected, desc }) => {
  const result = shouldShowRecommendation(current, suggested);
  const pass = result === expected;
  console.log(`  ${pass ? '✓' : '✗'} ${desc}: ${result} ${pass ? '' : `(expected ${expected})`}`);
});

console.log('\n=== All Core Logic Tests Complete ===');
