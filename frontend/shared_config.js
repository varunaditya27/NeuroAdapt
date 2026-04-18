// Frontend shared configuration
export const STATE_VECTOR_DIM = 5;
export const TELEMETRY_INTERVAL = 30000; // 30 seconds in milliseconds
export const ACTION_SPACE = 6;
export const N_QUBITS = 5;
export const N_ACTIONS = ACTION_SPACE;

export const GAMMA = 0.99;
export const EPSILON_START = 1.0;
export const EPSILON_END = 0.05;
export const EPSILON_DECAY_EP = 500;

export const REPLAY_CAPACITY = 10_000;
export const BATCH_SIZE = 32;
export const TARGET_UPDATE_FREQ = 100;
export const TAU = 0.005;

export const CONFIDENCE_GATE = 0.60;

export const ACTION_NAMES = {
  0: "hold_course",
  1: "soft_nudge",
  2: "simplify_text",
  3: "switch_video",
  4: "gamified_task",
  5: "sensory_break",
};
