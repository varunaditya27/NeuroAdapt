from __future__ import annotations

import argparse
import json
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
from shared_config import (
    BATCH_SIZE,
    EPSILON_END,
    EPSILON_START,
    GAMMA,
    N_ACTIONS,
    REPLAY_CAPACITY,
    STATE_VECTOR_DIM,
    TAU,
    TARGET_UPDATE_FREQ,
)

# Do not start training until this many experiences are in the buffer.
# Training on fewer produces nearly identical batches and useless gradients.
MIN_REPLAY_SIZE = 500

DEFAULT_STEPS_PER_EPISODE = 50


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


def evaluate_policy_pref_delta(net, sample_count: int = 32, seed: int = 0) -> float:
    rng = random.Random(seed)
    pref_deltas: list[float] = []

    with torch.no_grad():
        for _ in range(sample_count):
            state = [rng.random() for _ in range(STATE_VECTOR_DIM)]
            preferred_action = heuristic_action(state)

            state_tensor = torch.tensor(state, dtype=torch.float32).unsqueeze(0)
            action = int(net(state_tensor).argmax(dim=1).item())
            pref_delta = abs(action - preferred_action) / (N_ACTIONS - 1)
            pref_deltas.append(pref_delta)

    return sum(pref_deltas) / float(sample_count)


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
    """Standard shaped reward for stable convergence."""
    distance = abs(action - preferred_action)
    # This provides a consistent +0.4 improvement for every step closer
    return 1.0 - (2.0 * distance / (N_ACTIONS - 1))


def train_step(batch, online_net, target_net, optimiser, gamma: float = GAMMA) -> float:
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
    optimiser.step()
    return float(loss.item())


def _build_model(model_type: str):
    if model_type == "quantum":
        return QuantumDDQN()
    if model_type == "classical":
        return ClassicalDDQN()
    raise ValueError(f"Unsupported model_type: {model_type}")


def _build_optimiser(model_type: str, model, learning_rate: float):
    if model_type == "quantum":
        return optim.Adam([
            {"params": model.quantum_layer.parameters(), "lr": learning_rate / 10}, # 1/10 is safer than 1/20 here
            {"params": model.bn.parameters(),            "lr": learning_rate}, 
            {"params": model.advantage.parameters(),     "lr": learning_rate},
            {"params": model.value.parameters(),         "lr": learning_rate},
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
) -> TrainingResult:
    if seed is not None:
        random.seed(seed)
        torch.manual_seed(seed)

    online_net = _build_model(model_type)
    target_net = _build_model(model_type)
    target_net.load_state_dict(online_net.state_dict())

    optimiser = _build_optimiser(model_type, online_net, learning_rate)
    # Decay the LR by half every 50 episodes
    scheduler = optim.lr_scheduler.StepLR(optimiser, step_size=50, gamma=0.5)
    replay = ReplayBuffer(capacity=REPLAY_CAPACITY)

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

    global_step = 0

    # Epsilon decays across the full training run so the agent moves from
    # fully exploratory → mostly greedy by the final episode.
    epsilon_decay_episodes = episodes

    for episode in range(1, episodes + 1):
        state = [random.random() for _ in range(STATE_VECTOR_DIM)]
        episode_reward = 0.0
        episode_pref_delta = 0.0
        losses: list[float] = []

        epsilon = max(EPSILON_END, EPSILON_START - (episode / epsilon_decay_episodes))

        for _ in range(steps_per_episode):
            action = select_action(torch.tensor(state, dtype=torch.float32), epsilon, online_net)
            next_state = generate_next_state(state)

            preferred_action = heuristic_action(next_state)
            reward = compute_reward(action, preferred_action)
            pref_delta = abs(action - preferred_action) / (N_ACTIONS - 1)

            replay.push(state, action, reward, next_state, False)

            # Only train once the buffer has enough diverse experiences
            if len(replay) >= MIN_REPLAY_SIZE:
                batch = replay.sample(BATCH_SIZE)
                loss = train_step(batch, online_net, target_net, optimiser)
                losses.append(loss)

            global_step += 1
            if global_step % TARGET_UPDATE_FREQ == 0:
                soft_update(online_net, target_net, tau=TAU)

            state = next_state
            episode_reward += reward
            episode_pref_delta += pref_delta

        mean_pref_delta_train = episode_pref_delta / float(steps_per_episode)
        mean_pref_delta_eval = evaluate_policy_pref_delta(
            online_net,
            sample_count=32,
            seed=(seed or 0) + episode,
        )

        episode_rewards.append(episode_reward)
        train_preference_delta_history.append(mean_pref_delta_train)
        preference_delta_history.append(mean_pref_delta_eval)

        if wandb is not None:
            wandb.log(
                {
                    "lr": optimiser.param_groups[0]['lr'],
                    "episode": episode,
                    "episode_reward": episode_reward,
                    "epsilon": epsilon,
                    "loss": (sum(losses) / len(losses)) if losses else 0.0,
                    "train_pref_delta": mean_pref_delta_train,
                    "pref_delta": mean_pref_delta_eval,
                }
            )

        # Step LR scheduler only after at least one optimiser step.
        if losses:
            scheduler.step()  # Decay the learning rate for the next episode

        if episode % checkpoint_every == 0:
            checkpoint_path = checkpoints_dir / f"{checkpoint_prefix}_ep_{episode}.pt"
            torch.save(online_net.state_dict(), checkpoint_path)

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
    parser.add_argument("--episodes", type=int, default=200)
    parser.add_argument("--steps-per-episode", type=int, default=DEFAULT_STEPS_PER_EPISODE)
    parser.add_argument("--learning-rate", type=float, default=5e-4)
    parser.add_argument("--checkpoint-every", type=int, default=50)
    parser.add_argument("--model", choices=["quantum", "classical"], default="quantum")
    parser.add_argument("--checkpoint-prefix", type=str, default="policy")
    parser.add_argument("--seed", type=int, default=7)
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
    )


if __name__ == "__main__":
    main()
