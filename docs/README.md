<div align="center">

# 📚 docs
### Architecture · API Reference · Ethics · Deployment Guides

*Everything a developer, educator, or evaluator needs to understand NeuroAdapt completely.*

> This folder is the **definitive written record** of the system.
> Code is how NeuroAdapt works. Docs are *why*.

</div>

---

## 🗂️ Document Index

```
docs/
├── architecture.md             # System architecture + data flow narrative
├── api_reference.md            # All endpoints, request/response schemas, error codes
├── quantum_guide.md            # VQC implementation guide (theory + code walkthrough)
├── observer_signals.md         # All 5 signals: formulas, computation, privacy guarantees
├── reward_design.md            # Reward function rationale + YAML config reference
├── educator_dashboard.md       # Educator UI guide + privacy constraints (≥5 student rule)
│
├── ethics/
│   ├── participant_info_sheet.md  # POC participant information sheet
│   └── consent_form.md            # Written consent form template
│
└── deployment/
    ├── local_setup.md             # Full local development setup guide
    ├── vm_deployment.md           # DigitalOcean / AWS EC2 deployment walkthrough
    └── lti_integration.md         # Future LTI 1.3 integration guide (Moodle, Canvas)
```

---

## 📖 Document Descriptions

### `architecture.md`
The primary technical reference. Covers all four layers, the data flow diagram, the 30-second cycle, the trajectory buffer, and how the four agents interact. Start here if you are new to the codebase.

### `api_reference.md`
Every endpoint in `backend/` and `gen-engine/`, with:
- Full request/response JSON schemas
- HTTP status codes and error messages
- Rate limiting behaviour
- Authentication requirements

### `quantum_guide.md`
A standalone guide to the VQC + DDQN implementation. Covers the Hilbert space encoding, CNOT entanglement topology, Boltzmann exploration, the Dueling DDQN architecture, and the parameter-shift rule for gradient computation. Suitable for someone unfamiliar with quantum ML who needs to understand and extend the code.

### `observer_signals.md`
Detailed specification for all five signals including:
- Exact computation formulas
- Normalisation boundaries
- Edge case handling (mobile touch fallback for Jitter, cold-start for Preference Delta)
- Privacy guarantees (what is computed locally, what is transmitted)

### `reward_design.md`
The philosophical and technical justification for the Stability Reward function. Explains why optimising for correctness alone is harmful for neurodivergent learners, and documents every term in the reward function with its configurable weight in `quantum/configs/reward_weights.yaml`.

### `educator_dashboard.md`
Guide for educators using the aggregated insights dashboard. Explains the privacy model (minimum group size of 5, no individual data), the four available visualisations, and how to interpret intervention frequency data for curriculum redesign.

---

## ⚖️ Ethics Documentation

> These are not administrative afterthoughts. They are version-controlled, PR-reviewed documents that form part of the research record.

### `ethics/participant_info_sheet.md`
A plain-language document provided to every POC participant explaining:
- What data is collected (normalised signals only — no raw events)
- Where data is stored (anonymised, on-device computation)
- How data is used (training the Orchestrator policy)
- The right to withdraw at any time without consequence
- Contact information for concerns

### `ethics/consent_form.md`
A formal written consent form template covering:
- Voluntary participation statement
- Data collection and storage description
- Right to withdraw
- Signature block (participant + researcher)

> ⚠️ **Every POC participant must sign a consent form before their session data is used in training.** Informal consent is not sufficient for research data involving cognitive and behavioural signals from a neurodivergent population.

---

## 🚀 Deployment Guides

### `deployment/local_setup.md`
Step-by-step guide for getting the full stack running on a developer machine. Covers prerequisites, Docker setup, Ollama model download, environment variables, and the seed demo script.

### `deployment/vm_deployment.md`
Production deployment guide for a single VM (DigitalOcean Droplet or AWS EC2). Covers:
- Recommended VM specs (4 vCPU, 8GB RAM minimum for Ollama)
- Docker installation and Compose setup
- Nginx SSL certificate configuration
- Prometheus/Grafana setup
- Backup and recovery for PostgreSQL volume

### `deployment/lti_integration.md`
Forward-looking guide for Phase 3+ institutional deployment via LTI 1.3. Explains how NeuroAdapt integrates as a tool provider inside Moodle or Canvas, with the LMS acting as the platform that launches NeuroAdapt sessions in context.

---

## 🔗 Connected Modules

All documentation describes behaviour owned by:
- [`frontend/`](../frontend/README.md) — Observer signals, UI components
- [`backend/`](../backend/README.md) — API endpoints, middleware
- [`quantum/`](../quantum/README.md) — VQC architecture, reward design
- [`gen-engine/`](../gen-engine/README.md) — Generation modalities, latency budgets
- [`infra/`](../infra/README.md) — Deployment infrastructure

---

<div align="center">

*Part of the [NeuroAdapt](../README.md) monorepo*
**📚 If it is not documented, it does not exist.**

</div>
