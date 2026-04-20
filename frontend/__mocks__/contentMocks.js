export const mockTextContent = {
  title: 'How the brain forms memories',
  chunks: [
    'Memory formation begins in the hippocampus — a small, curved structure deep in the brain.',
    'When you experience something new, neurons fire in a specific pattern.',
    'If that pattern repeats, the connection between those neurons strengthens.',
    'This strengthening process is called long-term potentiation, or LTP.',
    'Sleep is when the brain consolidates these patterns — moving them from short-term to long-term storage.',
  ],
};

export const mockVideoContent = {
  title: 'How memory works — 3-minute explainer',
  src: 'https://www.w3schools.com/html/mov_bbb.mp4',
  poster: '',
  transcript:
    'Memory is the process by which information is encoded, stored, and retrieved. The hippocampus plays a central role in this process. When you learn something new, your neurons form new connections. These connections strengthen with repetition and sleep.',
};

export const mockAudioContent = {
  title: 'Memory consolidation — narrated',
  src: 'https://www.w3schools.com/html/horse.mp3',
  transcript:
    'Memory formation begins in the hippocampus. When you experience something new, neurons fire in a specific pattern. If that pattern repeats, the connection between those neurons strengthens. This strengthening process is called long-term potentiation. Sleep is when the brain moves these patterns into long-term storage.',
};

export const mockQuizContent = {
  title: 'Check your understanding',
  questions: [
    {
      id: 'q1',
      prompt: 'Where in the brain does memory formation primarily begin?',
      options: ['Cerebellum', 'Hippocampus', 'Amygdala', 'Prefrontal cortex'],
      correct: 1,
      explanation:
        'The hippocampus plays a central role in converting short-term experiences into long-term memories.',
    },
    {
      id: 'q2',
      prompt: 'What is the term for the strengthening of neuron connections?',
      options: ['Synaptic pruning', 'Neurogenesis', 'Long-term potentiation', 'Action potential'],
      correct: 2,
      explanation:
        'Long-term potentiation (LTP) is the persistent strengthening of synapses based on recent patterns of activity.',
    },
    {
      id: 'q3',
      prompt: 'When does the brain primarily consolidate memories into long-term storage?',
      options: ['During exercise', 'During sleep', 'During eating', 'During stress'],
      correct: 1,
      explanation: 'Sleep is the primary window during which the brain replays and consolidates the day\'s experiences.',
    },
  ],
};
