"""Canonical configuration for NeuroAdapt.

This file is the single source of truth for shared constants.
"""

STATE_VECTOR_DIM = 5
ACTION_SPACE = 6
N_QUBITS = 5
N_ACTIONS = ACTION_SPACE

GAMMA = 0.99
EPSILON_START = 1.0
EPSILON_END = 0.05
EPSILON_DECAY_EP = 500

REPLAY_CAPACITY = 10_000
BATCH_SIZE = 32
TARGET_UPDATE_FREQ = 100
TAU = 0.001

CONFIDENCE_GATE = 0.60
TELEMETRY_INTERVAL = 30_000

ACTION_NAMES = {
    0: "hold_course",
    1: "soft_nudge",
    2: "simplify_text",
    3: "switch_video",
    4: "gamified_task",
    5: "sensory_break",
}
