import json
from pathlib import Path
import matplotlib.pyplot as plt

def main():
    q_file = Path("quantum/checkpoints/ablation_quantum_seed7_history.json")
    c_file = Path("quantum/checkpoints/ablation_classical_seed7_history.json")

    if not q_file.exists() or not c_file.exists():
        print("History files not found!")
        return

    q_data = json.loads(q_file.read_text(encoding="utf-8"))
    c_data = json.loads(c_file.read_text(encoding="utf-8"))

    q_loss = q_data.get("loss_history", [])
    c_loss = c_data.get("loss_history", [])

    if not q_loss or not c_loss:
        print("Loss history empty!")
        return

    plt.figure(figsize=(10, 5))
    plt.plot(q_loss, label="VQC DDQN Loss", color='#1f63ff', alpha=0.8)
    plt.plot(c_loss, label="Classical DDQN Loss", color='#d9531e', alpha=0.8)

    # Calculate moving average for smoother curves
    def ma(x, w=10):
        out = []
        s = 0.0
        for i, v in enumerate(x):
            s += v
            if i >= w: s -= x[i - w]
            out.append(s / min(i + 1, w))
        return out

    plt.plot(ma(q_loss), color='#1f63ff', linewidth=2.5, label="VQC Loss (MA10)")
    plt.plot(ma(c_loss), color='#d9531e', linewidth=2.5, label="Classical Loss (MA10)")

    plt.title("Training Loss: VQC vs Classical DDQN")
    plt.xlabel("Episode")
    plt.ylabel("Loss (MSE)")
    plt.yscale("log")
    plt.legend()
    plt.grid(alpha=0.3)
    plt.tight_layout()

    out_path = Path("quantum/ablation_c_loss.png")
    plt.savefig(out_path)
    print(f"Saved loss plot to {out_path}")

if __name__ == "__main__":
    main()
