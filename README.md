<div align="center">

# 🧠 NeuroAdapt
### The Autonomous Neuro-Diverse Learning Ecosystem

*Turning education into a responsive, empathetic dialogue — one learner at a time.*

<br/>

[![License: MIT](https://img.shields.io/badge/License-MIT-violet.svg)](LICENSE)
[![Python 3.11](https://img.shields.io/badge/Python-3.11-blue.svg)](https://python.org)
[![Next.js 14](https://img.shields.io/badge/Next.js-14-black.svg)](https://nextjs.org)
[![PennyLane](https://img.shields.io/badge/Quantum-PennyLane_0.38-brightgreen.svg)](https://pennylane.ai)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-teal.svg)](https://fastapi.tiangolo.com)
[![Docker](https://img.shields.io/badge/Docker-Compose-blue.svg)](https://docker.com)
[![W&B](https://img.shields.io/badge/Tracking-W%26B-orange.svg)](https://wandb.ai)

<br/>

> **RVCE × Unisys Innovation Programme 2025**
> Prarthana Upadhyaya · Sudarshan S. Niranjan · Varun Aditya

</div>

---

## 📌 The Problem

> *"One size fits all" is a design flaw, not a pedagogy.*

**20% of undergraduates are neurodivergent** — diagnosed with ADHD, dyslexia, dyscalculia, or autism spectrum conditions. Yet every digital learning platform they use was designed for a hypothetical average student that does not exist.

The consequences are measurable and severe:

| Metric | Neurodivergent Students | Neurotypical Peers |
|---|---|---|
| Course completion rate | **26% lower** | Baseline |
| Average GPA gap | **−0.6 grade points** | Baseline |
| High school graduation rate | **35%** lack adequate support | — |
| Formal diagnosis (India) | Costs ₹15,000+ | Not required |

NeuroAdapt eliminates the design flaw at the infrastructure level — no diagnosis required, no accommodation forms, no opt-in. **The platform adapts to the learner. The learner does not adapt to the platform.**

---

## ✨ What NeuroAdapt Does

NeuroAdapt watches five **passive behavioural signals** every 30 seconds, builds a real-time model of the learner's cognitive state, and autonomously selects from six interventions to maintain optimal engagement — before the student even realises they are struggling.

```mermaid
flowchart LR
    A[🖥️ Student Browser] -->|5 signals every 30s| B[👁️ Observer Layer]
    B -->|State Vector| C[⚛️ Orchestrator
DDQN + VQC]
    C -->|Action 0–5| D[🎨 Generative
Synthesis Engine]
    D -->|Re-rendered content| E[📱 Content Renderer]
    E -->|Preference Delta
Energy Bar| F[🔄 Feedback Loop]
    F -->|Reward Signal| C
```

---

## 🏗️ System Architecture

NeuroAdapt is a four-layer system where each layer has a single, well-defined responsibility:

```mermaid
graph TD
    subgraph L1["Layer 1 — Observer (Browser)"]
        S1[Semantic Dwell Ratio]
        S2[Interaction Jitter]
        S3[Focus Persistence]
        S4[Stall Duration]
        S5[Preference Delta]
    end

    subgraph L2["Layer 2 — Orchestrator (Python + Quantum)"]
        VQC[Variational Quantum Circuit
5 qubits · RX · CNOT · RY]
        DDQN[Double DQN
Dueling Streams]
        VQC --> DDQN
    end

    subgraph L3["Layer 3 — Generative Synthesis Engine"]
        T[Text Simplify
LLaMA-3]
        V[Visual Synthesis
Stable Diffusion]
        AU[Audio TTS
Coqui / ElevenLabs]
        G[Gamified Task
Quiz Injector]
        BR[Sensory Break]
    end

    subgraph L4["Layer 4 — Feedback Loop"]
        PD[Preference Delta Modal]
        EB[Energy Bar Override]
        MF[Micro-Feedback Check]
    end

    L1 -->|State Vector| L2
    L2 -->|Action ID + Confidence| L3
    L3 -->|Rendered Content| L4
    L4 -->|Reward Signal| L2
```

---

## 🗂️ Repository Structure

```
NeuroAdapt/
├── 📁 frontend/        Next.js 14 · Observer telemetry · Student & Educator UI
├── 📁 backend/         FastAPI · Session management · Plausibility middleware
├── 📁 quantum/         PennyLane VQC · DDQN training · Reward engineering
├── 📁 gen-engine/      LLaMA-3 · Stable Diffusion · Coqui TTS · Quiz injector
├── 📁 infra/           Docker Compose · Nginx · Prometheus · Grafana
├── 📁 shared/          Auto-generated constants · Pydantic + TypeScript types
├── 📁 docs/            Architecture · API reference · Ethics · Deployment guides
├── 📁 research/        Literature survey · Ablation results · POC data
└── 📄 shared_config.py Canonical constants — single source of truth
```

> 📖 Each folder has its own detailed README. Click any folder name above or see the links below.

**Folder READMEs:**
- [`frontend/README.md`](frontend/README.md)
- [`backend/README.md`](backend/README.md)
- [`quantum/README.md`](quantum/README.md)
- [`gen-engine/README.md`](gen-engine/README.md)
- [`infra/README.md`](infra/README.md)
- [`shared/README.md`](shared/README.md)
- [`docs/README.md`](docs/README.md)
- [`research/README.md`](research/README.md)

---

## ⚙️ Quick Start

### Prerequisites

| Tool | Version | Purpose |
|---|---|---|
| Docker + Compose | v2.x | Full stack containerisation |
| Node.js | 20+ | Frontend development |
| Python | 3.11 | Backend + quantum modules |
| Ollama | Latest | Local LLaMA-3 inference |

### 1. Clone & Configure

```bash
git clone https://github.com/varunaditya27/NeuroAdapt.git
cd NeuroAdapt
cp .env.example .env
# Fill in your API keys in .env
```

### 2. Sync Shared Constants

```bash
python infra/scripts/sync_config.py
# Generates shared/config.ts and shared/types/state_vector.ts
```

### 3. Launch Full Stack

```bash
docker compose -f infra/docker-compose.yml up --build
```

### 4. Seed Demo Data

```bash
bash infra/scripts/seed_demo.sh
# Loads 3 pre-baked learner profiles: ADHD · Dyslexia · Neurotypical
```

### 5. Access

| Service | URL |
|---|---|
| Student UI | http://localhost:3000 |
| Educator Dashboard | http://localhost:3000/educator/insights |
| FastAPI Docs | http://localhost:8000/docs |
| Grafana Monitoring | http://localhost:3001 |

---

## 🧪 The Six Interventions

| Action ID | Name | Trigger Condition |
|---|---|---|
| `0` | **Hold Course** | Learner is in stable engagement |
| `1` | **Soft Nudge** | Mild inattention, not yet critical |
| `2` | **Simplify Text** | High dwell + low progress (reading wall) |
| `3` | **Switch to Video** | Persistent text-format mismatch |
| `4` | **Inject Gamified Task** | High tab-switching + escalating stall |
| `5` | **Sensory Break** | Multi-signal overload state detected |

> ⚛️ All six actions are selected by the Hybrid Quantum-Classical Policy Network. See [`quantum/README.md`](quantum/README.md) for the full VQC architecture.

---

## 📊 Expected Outcomes

```mermaid
xychart-beta
    title "NeuroAdapt Projected Impact vs Baseline"
    x-axis ["Completion Rate", "Assessment Score", "Engagement", "Pref Delta Conv."]
    y-axis "% Improvement" 0 --> 50
    bar [25, 12, 40, 85]
```

---

## 👥 Team

| Member | Role | Primary Modules |
|---|---|---|
| **Prarthana Upadhyaya** | Frontend · Observer · QML Integration | `frontend/` · `shared/` |
| **Sudarshan S. Niranjan** | Backend · Orchestrator · Quantum Core | `backend/` · `quantum/` |
| **Varun Aditya** | Gen Engine · Feedback Loop · DevOps | `gen-engine/` · `infra/` |

---

## 🔬 Research Foundation

NeuroAdapt is grounded in peer-reviewed evidence across four research domains:

- **EndeavorRx RCT (Leitner et al., 2024)** — FDA-authorised adaptive game produces clinically significant attention improvements in ADHD
- **Clément et al., 2015** — Multi-Armed Bandits outperform expert-designed curricula in live classroom deployments
- **Bhatia et al. / Cao et al., 2025** — VQCs converge faster than classical baselines in early training epochs
- **Langberg et al., 2021** — ADHD students maintain 0.5–0.6 GPA gap under standard instruction across all four college years

> 📖 Full literature survey: [`research/lit_survey.md`](research/lit_survey.md)

---

## 📜 Branching Strategy

```
main          ← stable, demo-ready
dev           ← integration branch
feature/*     ← individual features (e.g. feature/trajectory-buffer)
quantum/*     ← quantum experiments (e.g. quantum/ablation-c)
```

---

<div align="center">

---

*Built at R. V. College of Engineering, Bengaluru*
*Unisys Innovation Programme 2025*

**🧠 NeuroAdapt — Because every brain deserves a platform built for it.**

</div>
