<div align="center">

# 🔬 research
### Literature Survey · Ablation Results · POC Data

*The evidence base that justifies every design decision in NeuroAdapt.*

> This folder is the academic backbone of the project.
> Every claim in the system description is traceable to a study in this folder.

</div>

---

## 🗂️ Directory Layout

```
research/
├── lit_survey.md           # Full literature review across 5 research domains
├── ablation_results/       # W&B exported plots, CSV summaries (gitignored)
│   └── .gitkeep
└── poc_data/               # Anonymised POC session logs (gitignored, sensitive)
    └── .gitignore
```

---

## 📖 Literature Survey

`lit_survey.md` is a comprehensive survey across five research domains that directly inform NeuroAdapt's design:

### Domain 1 — Neurodivergent Academic Outcomes
Evidence that neurodivergent students face systematically worse outcomes under current educational systems — not due to ability, but due to structural design flaws.

| Study | Key Finding |
|---|---|
| Langberg et al., 2021 | ADHD students maintain −0.5 to −0.6 GPA gap across all 4 college years |
| Breaux et al., 2021 | Only 49% of unmedicated ADHD students complete 8 semesters vs 59% of peers |
| NCES Data, 2020 | 20.5% of undergraduates report a disability; ADHD and LD most prevalent |
| Doyle et al., 2024 | Existing accommodations show limited measurable impact on GPA |

### Domain 2 — Adaptive Learning Technologies
Evidence that adaptive systems outperform static instruction, particularly for struggling learners.

| Study | Key Finding |
|---|---|
| Maran et al., 2024 | Real-time adaptive difficulty reduces overload, improves retention |
| Al-Turki et al., 2025 | AI-driven ITS consistently outperforms static instruction; largest gains for weakest students |

### Domain 3 — Reinforcement Learning in Education
Evidence that RL and bandit algorithms can effectively personalise learning sequences.

| Study | Key Finding |
|---|---|
| Clément et al., 2015 | Bandits outperform expert curricula; live deployment with 400+ students |
| Multiple RL-ITS studies | 30% reduction in hint requests; higher post-test scores vs rule-based tutoring |

### Domain 4 — Gamification & Multimodal Interventions for ADHD
Clinical evidence that adaptive digital experiences can meaningfully improve attention.

| Study | Key Finding |
|---|---|
| EndeavorRx RCT (Leitner et al., 2024) | FDA-authorised; 1/3 of children reach normative range on attention after 4 weeks |
| Teruel et al., 2024 | Biometric signals during games accurately measure ADHD attentional performance |
| Frontiers in Education, 2025 | Gamified apps improve sustained attention and academic performance in ADHD |

### Domain 5 — Hybrid Quantum-Classical Models
Evidence for the VQC's early-convergence advantage over classical baselines.

| Study | Key Finding |
|---|---|
| Bhatia et al., 2025 | VQCs show significantly lower loss in early training epochs vs classical Dense |
| Cao et al., 2025 (Nature Sci. Rep.) | Confirmed early-convergence advantage in hybrid CNN architectures |

---

## 📊 Ablation Results

The `ablation_results/` folder stores exported outputs from the three planned ablation experiments. These are **gitignored** because W&B tracks them natively — see the [W&B project dashboard](https://wandb.ai) for live results.

Local exports (PNG plots, CSV summaries) are placed here for inclusion in the submission report.

| Ablation | File | Status |
|---|---|---|
| A — Remove Focus Persistence | `ablation_a_convergence.png` | Phase 4 |
| B — Reduced action space (6→3) | `ablation_b_cost_engagement.png` | Phase 4 |
| C — VQC vs Classical Dense | `ablation_c_quantum_advantage.png` | Phase 4 ⭐ |

> ⭐ Ablation C is the most important result for the Unisys submission. It directly answers: "Does the quantum component provide measurable benefit?"

---

## 🔒 POC Data

`poc_data/` is **gitignored** and contains:
- Anonymised session logs from the RVCE POC cohort (20–30 students)
- Preference Delta trajectories per learner (no PII)
- Engagement metrics (slides_completed / slides_total per session)

**Access:** Only Sudarshan (data custodian) has direct access to this folder on the deployment VM. Data is aggregated before sharing with the rest of the team.

> 📋 All participants in the POC cohort have signed written consent forms. See [`docs/ethics/consent_form.md`](../docs/ethics/consent_form.md).

---

## 🔗 Connected Modules

| Module | Connection |
|---|---|
| [`quantum/`](../quantum/README.md) | Ablation experiments generate results stored here |
| [`docs/`](../docs/README.md) | Literature survey informs architecture and reward design documents |
| [`infra/`](../infra/README.md) | POC data flows from deployment VM via `retrain.yml` |

---

<div align="center">

*Part of the [NeuroAdapt](../README.md) monorepo*
**🔬 Every design decision in NeuroAdapt is backed by evidence. This is where the evidence lives.**

</div>
