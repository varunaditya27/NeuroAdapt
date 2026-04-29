from __future__ import annotations

import argparse
import json
import math
import random
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import torch
import torch.nn.functional as F
from torch import optim

if __package__ is None or __package__ == "":
    import sys

    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

try:
    from quantum.pennylane_vqc import ClassicalDDQN, QuantumDDQN
except ModuleNotFoundError:
    from pennylane_vqc import ClassicalDDQN, QuantumDDQN
from backend.shared_config import (
    BATCH_SIZE,
    EPSILON_DECAY_EP,
    EPSILON_END,
    EPSILON_START,
    GAMMA,
    N_ACTIONS,
    REPLAY_CAPACITY,
    STATE_VECTOR_DIM,
    TAU,
)

# Do not start training until this many experiences are in the buffer.
# Training on fewer produces nearly identical batches and useless gradients.
MIN_REPLAY_SIZE = 1_000
REPLAY_PREFILL_SIZE = 1_000
EVAL_SAMPLE_SIZE = 512
GRAD_CLIP_NORM = 10.0
DEFAULT_CLASSICAL_HIDDEN_DIM = 64

DEFAULT_STEPS_PER_EPISODE = 50
DEFAULT_DATA_DIR = "quantum/data"

Transition = tuple[list[float], int, float, list[float], bool]


@dataclass
class TrainingResult:
    episode_rewards: list[float]
    preference_delta_history: list[float]


class ReplayBuffer:
    def __init__(self, capacity: int = REPLAY_CAPACITY) -> None:
        self.buf = deque(maxlen=capacity)

    def push(self, state, action, reward, next_state, done) -> None:
        self.buf.append((state, action, reward, next_state, done))

    def sample(self, batch_size: int = BATCH_SIZE):
        return random.sample(self.buf, batch_size)

    def __len__(self) -> int:
        return len(self.buf)


def _parse_state_vector(raw_state: object, field_name: str) -> list[float]:
    if not isinstance(raw_state, list) or len(raw_state) != STATE_VECTOR_DIM:
        raise ValueError(f"Invalid {field_name}: expected list[{STATE_VECTOR_DIM}]")

    try:
        return [float(value) for value in raw_state]
    except Exception as exc:
        raise ValueError(f"Invalid {field_name}: values must be numeric") from exc


def load_dataset_transitions(data_dir: str | Path) -> list[Transition]:
    dataset_dir = Path(data_dir)
    dataset_files = sorted(dataset_dir.glob("*.json"))

    if not dataset_files:
        raise FileNotFoundError(
            f"No dataset files found in {dataset_dir}. "
            "Generate or add archetype data JSON files first."
        )

    transitions: list[Transition] = []

    for dataset_file in dataset_files:
        payload = json.loads(dataset_file.read_text(encoding="utf-8"))
        raw_transitions = payload.get("transitions")

        if not isinstance(raw_transitions, list):
            raise ValueError(f"Invalid dataset file {dataset_file}: missing 'transitions' list")

        for index, item in enumerate(raw_transitions):
            if not isinstance(item, dict):
                raise ValueError(f"Invalid transition at {dataset_file} index {index}: must be object")

            state = _parse_state_vector(item.get("state"), "state")
            next_state = _parse_state_vector(item.get("next_state"), "next_state")

            action = int(item.get("action"))
            if action < 0 or action >= N_ACTIONS:
                raise ValueError(f"Invalid action at {dataset_file} index {index}: {action}")

            reward = float(item.get("reward"))
            done = bool(item.get("done", False))

            transitions.append((state, action, reward, next_state, done))

    if not transitions:
        raise ValueError(f"No transitions loaded from {dataset_dir}")

    return transitions


def evaluate_policy_pref_delta(
    net,
    transitions: list[Transition],
    sample_count: int = 32,
) -> float:
    pref_deltas: list[float] = []

    if not transitions:
        return 0.0

    eval_batch = transitions[: min(sample_count, len(transitions))]

    with torch.no_grad():
        for state, expected_action, _, _, _ in eval_batch:

            state_tensor = torch.tensor(state, dtype=torch.float32).unsqueeze(0)
            predicted_action = int(net(state_tensor).argmax(dim=1).item())
            pref_delta = abs(predicted_action - expected_action) / (N_ACTIONS - 1)
            pref_deltas.append(pref_delta)

    return sum(pref_deltas) / float(len(pref_deltas))


def evaluate_policy_action_entropy(
    net,
    transitions: list[Transition],
    sample_count: int = 64,
) -> float:
    if not transitions:
        return 0.0

    eval_batch = transitions[: min(sample_count, len(transitions))]
    action_counts = [0 for _ in range(N_ACTIONS)]

    with torch.no_grad():
        for state, _, _, _, _ in eval_batch:
            state_tensor = torch.tensor(state, dtype=torch.float32).unsqueeze(0)
            action = int(net(state_tensor).argmax(dim=1).item())
            action_counts[action] += 1

    total = float(sum(action_counts))
    if total == 0.0:
        return 0.0

    entropy = 0.0
    for count in action_counts:
        if count > 0:
            p = count / total
            entropy -= p * math.log(p + 1e-12)

    return entropy


def select_action(state_tensor: torch.Tensor, epsilon: float, net) -> int:
    if random.random() < epsilon:
        return random.randint(0, N_ACTIONS - 1)

    with torch.no_grad():
        return int(net(state_tensor.unsqueeze(0)).argmax().item())


def soft_update(online_net, target_net, tau: float = TAU) -> None:
    for p_online, p_target in zip(online_net.parameters(), target_net.parameters()):
        p_target.data.copy_(tau * p_online.data + (1.0 - tau) * p_target.data)


def heuristic_action(state: list[float]) -> int:
    dwell, jitter, focus, stall, pref_delta = state

    if max(stall, jitter) > 0.75:
        return 5
    if dwell > 0.70:
        return 2
    if pref_delta > 0.70:
        return 3
    if stall > 0.55:
        return 4
    if focus < 0.25:
        return 1
    return 0


def generate_next_state(state: list[float]) -> list[float]:
    next_state = []
    for signal in state:
        perturbed = signal + random.uniform(-0.12, 0.12)
        next_state.append(max(0.0, min(1.0, perturbed)))
    return next_state


def compute_reward(action: int, preferred_action: int) -> float:
    """Exponentially decayed reward to penalize large misses harder."""
    distance = abs(action - preferred_action)
    return float(math.exp(-(distance**2) / 2.0))


def _quantum_grad_norm(model) -> float:
    if not hasattr(model, "quantum_layer"):
        return 0.0

    sq_norm = 0.0
    for param in model.quantum_layer.parameters():
        if param.grad is not None:
            sq_norm += float(param.grad.detach().pow(2).sum().item())

    return sq_norm ** 0.5


def _validate_quantum_requires_grad(model) -> None:
    if not hasattr(model, "quantum_layer"):
        return

    frozen = [name for name, param in model.quantum_layer.named_parameters() if not param.requires_grad]
    if frozen:
        raise RuntimeError(f"Quantum parameters are frozen and cannot train: {frozen}")


def train_step(batch, online_net, target_net, optimiser, gamma: float = GAMMA) -> tuple[float, float]:
    states, actions, rewards, next_states, dones = zip(*batch)

    states_t = torch.tensor(states, dtype=torch.float32)
    actions_t = torch.tensor(actions, dtype=torch.long).unsqueeze(1)
    rewards_t = torch.tensor(rewards, dtype=torch.float32).unsqueeze(1)
    next_states_t = torch.tensor(next_states, dtype=torch.float32)
    dones_t = torch.tensor(dones, dtype=torch.float32).unsqueeze(1)

    q_online = online_net(states_t).gather(1, actions_t)

    with torch.no_grad():
        next_actions = online_net(next_states_t).argmax(dim=1, keepdim=True)
        q_target_val = target_net(next_states_t).gather(1, next_actions)
        td_target = rewards_t + gamma * q_target_val * (1.0 - dones_t)

    loss = F.smooth_l1_loss(q_online, td_target)
    optimiser.zero_grad()
    loss.backward()
    quantum_grad_norm = _quantum_grad_norm(online_net)
    torch.nn.utils.clip_grad_norm_(online_net.parameters(), GRAD_CLIP_NORM)
    optimiser.step()
    return float(loss.item()), float(quantum_grad_norm)


def _build_model(model_type: str, classical_hidden_dim: int = DEFAULT_CLASSICAL_HIDDEN_DIM):
    if model_type == "quantum":
        return QuantumDDQN()
    if model_type == "classical":
        return ClassicalDDQN(hidden_dim=classical_hidden_dim)
    raise ValueError(f"Unsupported model_type: {model_type}")


def _build_optimiser(
    model_type: str,
    model,
    learning_rate: float,
    quantum_layer_lr: Optional[float] = None,
    quantum_head_lr: Optional[float] = None,
):
    if model_type == "quantum":
        q_lr = quantum_layer_lr if quantum_layer_lr is not None else learning_rate * 5.0
        h_lr = quantum_head_lr if quantum_head_lr is not None else learning_rate
        return optim.Adam([
            {"params": model.quantum_layer.parameters(), "lr": q_lr},
            {"params": model.bn.parameters(),            "lr": h_lr},
            {"params": model.advantage.parameters(),     "lr": h_lr},
            {"params": model.value.parameters(),         "lr": h_lr},
        ])
    return optim.Adam(model.parameters(), lr=learning_rate)

def run_training(
    episodes: int,
    model_type: str,
    steps_per_episode: int,
    checkpoint_every: int,
    checkpoint_prefix: str,
    learning_rate: float,
    enable_wandb: bool,
    wandb_project: str,
    write_latest: bool = True,
    seed: Optional[int] = None,
    data_dir: str = DEFAULT_DATA_DIR,
    epsilon_decay_episodes: Optional[int] = None,
    classical_hidden_dim: int = DEFAULT_CLASSICAL_HIDDEN_DIM,
    quantum_layer_lr: Optional[float] = None,
    quantum_head_lr: Optional[float] = None,
    reward_mode: str = "exp-distance",
) -> TrainingResult:
    if seed is not None:
        random.seed(seed)
        torch.manual_seed(seed)

    rng = random.Random(seed)
    dataset_transitions = load_dataset_transitions(data_dir)
    rng.shuffle(dataset_transitions)

    online_net = _build_model(model_type, classical_hidden_dim=classical_hidden_dim)
    target_net = _build_model(model_type, classical_hidden_dim=classical_hidden_dim)
    target_net.load_state_dict(online_net.state_dict())

    if model_type == "quantum":
        _validate_quantum_requires_grad(online_net)

    optimiser = _build_optimiser(
        model_type,
        online_net,
        learning_rate,
        quantum_layer_lr=quantum_layer_lr,
        quantum_head_lr=quantum_head_lr,
    )
    scheduler = optim.lr_scheduler.StepLR(optimiser, step_size=300, gamma=0.5)
    replay = ReplayBuffer(capacity=REPLAY_CAPACITY)

    prefill_size = min(len(dataset_transitions), max(MIN_REPLAY_SIZE, REPLAY_PREFILL_SIZE))
    for state, action, reward, next_state, done in dataset_transitions[:prefill_size]:
        replay.push(state, action, reward, next_state, done)

    eval_rng = random.Random((seed or 0) + 999)
    eval_size = min(EVAL_SAMPLE_SIZE, len(dataset_transitions))
    eval_transitions = eval_rng.sample(dataset_transitions, k=eval_size)

    wandb = None
    if enable_wandb:
        try:
            import wandb as wb

            wb.init(project=wandb_project, config={"model_type": model_type, "episodes": episodes})
            wandb = wb
        except Exception:
            wandb = None

    checkpoints_dir = Path("quantum/checkpoints")
    checkpoints_dir.mkdir(parents=True, exist_ok=True)

    episode_rewards: list[float] = []
    preference_delta_history: list[float] = []
    train_preference_delta_history: list[float] = []
    loss_history: list[float] = []
    quantum_grad_norm_history: list[float] = []
    action_entropy_history: list[float] = []

    # Epsilon decays across the full training run so the agent moves from
    # fully exploratory → mostly greedy by the final episode.
    decay_episodes = epsilon_decay_episodes if epsilon_decay_episodes is not None else EPSILON_DECAY_EP
    decay_episodes = max(1, decay_episodes)

    for episode in range(1, episodes + 1):
        episode_reward = 0.0
        episode_pref_delta = 0.0
        losses: list[float] = []

        epsilon = max(EPSILON_END, EPSILON_START - ((episode - 1) / decay_episodes))
        episode_quantum_grads: list[float] = []

        for _ in range(steps_per_episode):
            state, action, reward, next_state, done = rng.choice(dataset_transitions)

            if reward_mode == "exp-distance":
                preferred_action = heuristic_action(next_state)
                reward = compute_reward(action, preferred_action)

            replay.push(state, action, reward, next_state, done)

            with torch.no_grad():
                state_tensor = torch.tensor(state, dtype=torch.float32).unsqueeze(0)
                predicted_action = int(online_net(state_tensor).argmax(dim=1).item())

            pref_delta = abs(predicted_action - action) / (N_ACTIONS - 1)

            # Only train once the buffer has enough diverse experiences
            if len(replay) >= MIN_REPLAY_SIZE:
                batch = replay.sample(BATCH_SIZE)
                loss, quantum_grad_norm = train_step(batch, online_net, target_net, optimiser)
                losses.append(loss)
                if model_type == "quantum":
                    episode_quantum_grads.append(quantum_grad_norm)
                # Soft-update the target at every optimisation step.
                soft_update(online_net, target_net, tau=TAU)

            episode_reward += reward
            episode_pref_delta += pref_delta

        mean_pref_delta_train = episode_pref_delta / float(steps_per_episode)
        mean_pref_delta_eval = evaluate_policy_pref_delta(
            online_net,
            eval_transitions,
            sample_count=32,
        )
        policy_action_entropy = evaluate_policy_action_entropy(
            online_net,
            eval_transitions,
            sample_count=64,
        )
        mean_loss = (sum(losses) / len(losses)) if losses else 0.0
        mean_quantum_grad = (sum(episode_quantum_grads) / len(episode_quantum_grads)) if episode_quantum_grads else 0.0

        episode_rewards.append(episode_reward)
        train_preference_delta_history.append(mean_pref_delta_train)
        preference_delta_history.append(mean_pref_delta_eval)
        loss_history.append(mean_loss)
        quantum_grad_norm_history.append(mean_quantum_grad)
        action_entropy_history.append(policy_action_entropy)

        if wandb is not None:
            wandb.log(
                {
                    "lr": optimiser.param_groups[0]['lr'],
                    "episode": episode,
                    "episode_reward": episode_reward,
                    "epsilon": epsilon,
                    "loss": mean_loss,
                    "train_pref_delta": mean_pref_delta_train,
                    "pref_delta": mean_pref_delta_eval,
                    "policy_action_entropy": policy_action_entropy,
                    "quantum_grad_norm": mean_quantum_grad,
                }
            )

        if episode % checkpoint_every == 0:
            checkpoint_path = checkpoints_dir / f"{checkpoint_prefix}_ep_{episode}.pt"
            torch.save(online_net.state_dict(), checkpoint_path)

        scheduler.step()

    if write_latest:
        latest_path = checkpoints_dir / "latest.pt"
        torch.save(online_net.state_dict(), latest_path)

    history_path = checkpoints_dir / f"{checkpoint_prefix}_history.json"
    history_path.write_text(
        json.dumps(
            {
                "episode_rewards": episode_rewards,
                "preference_delta_history": preference_delta_history,
                "train_preference_delta_history": train_preference_delta_history,
                "loss_history": loss_history,
                "quantum_grad_norm_history": quantum_grad_norm_history,
                "policy_action_entropy_history": action_entropy_history,
                "reward_mode": reward_mode,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    if wandb is not None:
        wandb.finish()

    return TrainingResult(
        episode_rewards=episode_rewards,
        preference_delta_history=preference_delta_history,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train NeuroAdapt DDQN policy")
    parser.add_argument("--episodes", type=int, default=500)
    parser.add_argument("--steps-per-episode", type=int, default=DEFAULT_STEPS_PER_EPISODE)
    parser.add_argument("--learning-rate", type=float, default=5e-4)
    parser.add_argument("--checkpoint-every", type=int, default=50)
    parser.add_argument("--model", choices=["quantum", "classical"], default="quantum")
    parser.add_argument("--checkpoint-prefix", type=str, default="policy")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--data-dir", type=str, default=DEFAULT_DATA_DIR)
    parser.add_argument("--epsilon-decay-episodes", type=int, default=EPSILON_DECAY_EP)
    parser.add_argument("--classical-hidden-dim", type=int, default=DEFAULT_CLASSICAL_HIDDEN_DIM)
    parser.add_argument("--quantum-layer-lr", type=float, default=None)
    parser.add_argument("--quantum-head-lr", type=float, default=None)
    parser.add_argument("--reward-mode", choices=["dataset", "exp-distance"], default="exp-distance")
    parser.add_argument("--wandb", action="store_true", help="Enable Weights & Biases logging")
    parser.add_argument("--wandb-project", type=str, default="neuroadapt-ddqn")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    run_training(
        episodes=args.episodes,
        model_type=args.model,
        steps_per_episode=args.steps_per_episode,
        checkpoint_every=args.checkpoint_every,
        checkpoint_prefix=args.checkpoint_prefix,
        learning_rate=args.learning_rate,
        enable_wandb=args.wandb,
        wandb_project=args.wandb_project,
        write_latest=True,
        seed=args.seed,
        data_dir=args.data_dir,
        epsilon_decay_episodes=args.epsilon_decay_episodes,
        classical_hidden_dim=args.classical_hidden_dim,
        quantum_layer_lr=args.quantum_layer_lr,
        quantum_head_lr=args.quantum_head_lr,
        reward_mode=args.reward_mode,
    )


if __name__ == "__main__":
    main()
