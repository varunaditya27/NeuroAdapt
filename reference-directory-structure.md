neuro-adapt/
│
├── .github/
│   ├── workflows/
│   │   ├── ci.yml                  # lint + unit tests on every PR
│   │   ├── deploy.yml              # build & push Docker image on merge to main
│   │   └── retrain.yml             # scheduled offline DDQN re-training (cron)
│   └── PULL_REQUEST_TEMPLATE.md
│
├── shared/
│   ├── config.py                   # single source of truth for all constants (Python)
│   ├── config.ts                   # AUTO-GENERATED from config.py via scripts/sync_config.py
│   └── types/
│       ├── state_vector.py         # Pydantic model: StateVector, FeedbackPayload
│       └── state_vector.ts         # Matching TypeScript interfaces (auto-generated)
│
├── frontend/                       # P1 — Next.js 14, Tailwind, WCAG 2.1 AA
│   ├── public/
│   │   └── assets/
│   │       ├── calm-break-bg.svg   # sensory break screen background
│   │       └── icons/
│   ├── src/
│   │   ├── app/                    # Next.js App Router
│   │   │   ├── (student)/
│   │   │   │   ├── lesson/
│   │   │   │   │   └── [moduleId]/
│   │   │   │   │       └── page.tsx
│   │   │   │   └── dashboard/
│   │   │   │       └── page.tsx    # student-facing progress view
│   │   │   ├── (educator)/
│   │   │   │   └── insights/
│   │   │   │       └── page.tsx    # aggregated cohort heatmaps (≥5 students)
│   │   │   ├── api/                # Next.js route handlers (thin proxies to backend)
│   │   │   │   ├── state/route.ts
│   │   │   │   ├── action/route.ts
│   │   │   │   └── feedback/route.ts
│   │   │   ├── layout.tsx
│   │   │   └── page.tsx            # landing / login
│   │   │
│   │   ├── components/
│   │   │   ├── observer/
│   │   │   │   ├── Observer.ts             # core telemetry module (vanilla JS class)
│   │   │   │   ├── signals/
│   │   │   │   │   ├── dwell.ts            # Semantic Dwell Ratio (+ FK normalisation)
│   │   │   │   │   ├── jitter.ts           # Interaction Jitter (mouse + touch fallback)
│   │   │   │   │   ├── focus.ts            # Focus Persistence (visibilityState events)
│   │   │   │   │   ├── stall.ts            # Stall Duration
│   │   │   │   │   └── scroll_direction.ts # Backwards scroll re-read detector (new)
│   │   │   │   └── TrajectoryBuffer.ts     # Holds last 3 state vectors for window input
│   │   │   │
│   │   │   ├── content/
│   │   │   │   ├── ContentRenderer.tsx     # switches text/image/audio/quiz/break
│   │   │   │   ├── TextSlide.tsx
│   │   │   │   ├── VideoSlide.tsx
│   │   │   │   ├── AudioSlide.tsx
│   │   │   │   ├── QuizSlide.tsx
│   │   │   │   ├── SensoryBreak.tsx        # action_id=5 screen (blank + TTS prompt)
│   │   │   │   └── SkeletonLoader.tsx      # shown when confidence < 0.60
│   │   │   │
│   │   │   ├── feedback/
│   │   │   │   ├── EnergyBar.tsx           # manual override widget
│   │   │   │   ├── PreferenceDeltaModal.tsx # end-of-lesson format preference
│   │   │   │   └── MicroFeedback.tsx       # 3-second emoji check post-format-switch (new)
│   │   │   │
│   │   │   ├── educator/
│   │   │   │   ├── EngagementHeatmap.tsx   # slide-level stall frequency heatmap
│   │   │   │   ├── InterventionChart.tsx   # format switch frequency by module section
│   │   │   │   └── FormatPrefDistribution.tsx
│   │   │   │
│   │   │   └── ui/                         # reusable atomic components
│   │   │       ├── Button.tsx
│   │   │       ├── Badge.tsx
│   │   │       └── Tooltip.tsx
│   │   │
│   │   ├── hooks/
│   │   │   ├── useObserver.ts      # mounts Observer, manages polling interval
│   │   │   ├── useAction.ts        # fetches action from backend, handles offline fallback
│   │   │   └── useOfflineQueue.ts  # queues state vectors when API unreachable (new)
│   │   │
│   │   ├── lib/
│   │   │   ├── constants.ts        # AUTO-GENERATED — do not edit manually
│   │   │   ├── api.ts              # typed fetch wrappers for all backend endpoints
│   │   │   └── flesch_kincaid.ts   # lightweight FK readability scorer (browser-side)
│   │   │
│   │   └── styles/
│   │       └── globals.css
│   │
│   ├── __tests__/
│   │   ├── observer/
│   │   │   ├── dwell.test.ts
│   │   │   ├── jitter.test.ts
│   │   │   └── focus.test.ts
│   │   └── components/
│   │       ├── ContentRenderer.test.tsx
│   │       └── EnergyBar.test.tsx
│   │
│   ├── next.config.js
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   └── package.json
│
├── backend/                        # P2 — Python 3.11, FastAPI
│   ├── main.py                     # FastAPI app entry, registers all routers
│   ├── routers/
│   │   ├── state.py                # POST /api/state — validate, plausibility gate, cache
│   │   ├── action.py               # GET  /api/action — call policy, return action_id + confidence
│   │   ├── feedback.py             # POST /api/feedback — compute reward, write to Postgres
│   │   └── health.py               # GET  /health — liveness probe for Docker
│   │
│   ├── middleware/
│   │   ├── auth.py                 # JWT validation
│   │   ├── rate_limit.py           # per-session rate limiting on /api/generate
│   │   └── plausibility.py         # adversarial input gate (new) — checks state delta vs history
│   │
│   ├── services/
│   │   ├── orchestrator_client.py  # calls quantum module inference endpoint
│   │   ├── redis_client.py         # state vector cache (sub-5ms reads, TTL 5min)
│   │   ├── session_manager.py      # per-learner session state, cold-start handling (new)
│   │   └── reward_router.py        # routes reward signals to quantum/reward.py
│   │
│   ├── models/
│   │   ├── state_vector.py         # Pydantic: StateVector, TrajectoryWindow (new — 3×5)
│   │   ├── feedback.py             # Pydantic: FeedbackPayload, MicroFeedbackPayload (new)
│   │   └── action.py               # Pydantic: ActionResponse
│   │
│   ├── db/
│   │   ├── postgres.py             # SQLAlchemy async engine setup
│   │   ├── migrations/             # Alembic migration scripts
│   │   │   └── versions/
│   │   └── schemas.sql             # raw schema reference (tables: sessions, replay, preferences)
│   │
│   ├── __tests__/
│   │   ├── test_state.py
│   │   ├── test_feedback.py
│   │   ├── test_plausibility.py    # adversarial input edge cases
│   │   └── test_session_manager.py # cold-start + Session 1 PD_prev handling
│   │
│   └── requirements.txt
│
├── quantum/                        # P2 (core) + P3 (reward, retrain)
│   ├── pennylane_vqc.py            # VQC circuit + QuantumDDQN class (Dueling streams)
│   ├── train.py                    # DDQN training loop, W&B logging, checkpoint saving
│   ├── retrain.py                  # offline re-training from Postgres replay table (P3)
│   ├── reward.py                   # full reward fn with Stability Bonus (YAML-configurable)
│   ├── mock_data.py                # 3 synthetic archetypes: ADHD, dyslexia, neurotypical
│   ├── visualise_circuit.py        # qml.draw → PNG for submission report (P1)
│   ├── ablations/
│   │   ├── ablation_a.py           # remove Focus Persistence signal
│   │   ├── ablation_b.py           # reduce action space to 3
│   │   └── ablation_c.py           # VQC vs classical dense layer convergence
│   │
│   ├── configs/
│   │   ├── reward_weights.yaml     # configurable reward term weights
│   │   └── training_config.yaml    # hyperparameters: gamma, epsilon, batch_size etc.
│   │
│   ├── checkpoints/                # saved model weights (gitignored, mounted as Docker volume)
│   │   └── .gitkeep
│   │
│   ├── __tests__/
│   │   ├── test_vqc.py             # unit tests with synthetic state vectors
│   │   ├── test_reward.py          # reward function edge cases
│   │   └── test_boltzmann.py       # Boltzmann exploration vs epsilon-greedy comparison (new)
│   │
│   └── QISKIT_MIGRATION.md         # future NISQ hardware migration guide
│
├── gen-engine/                     # P3 — FastAPI microservice
│   ├── main.py                     # FastAPI entry for generation service
│   ├── routers/
│   │   └── generate.py             # POST /api/generate — dispatch by action_id
│   │
│   ├── generators/
│   │   ├── text_simplify.py        # LLaMA-3 rewriter + FK verification loop (new)
│   │   ├── image_gen.py            # Stable Diffusion with autism-safe negative prompts (new)
│   │   ├── tts.py                  # Coqui TTS calm preset wrapper
│   │   ├── quiz_injector.py        # gamified task builder (mastery-scaled difficulty) (new)
│   │   └── avatar_video.py         # HeyGen API wrapper (optional / premium)
│   │
│   ├── prefetch/
│   │   ├── prefetch_manager.py     # async background generation of top-N format variants
│   │   └── latency_budget.py       # per-modality timeout config + graceful fallback (new)
│   │
│   ├── prompts/
│   │   ├── simplify_grade5.txt     # few-shot prompt templates
│   │   ├── simplify_grade8.txt
│   │   ├── simplify_university.txt
│   │   └── image_gen_base.txt      # base SD prompt + negative prompt block
│   │
│   ├── __tests__/
│   │   ├── test_text_simplify.py   # FK score verification of outputs
│   │   ├── test_quiz_injector.py
│   │   └── test_prefetch.py        # latency budget enforcement
│   │
│   └── requirements.txt
│
├── infra/
│   ├── docker-compose.yml          # full stack: Postgres + Redis + Backend + Gen-Engine + Frontend
│   ├── docker-compose.dev.yml      # dev overrides: hot reload, local Ollama mount
│   ├── docker-compose.test.yml     # CI test environment (in-memory SQLite, mock Redis)
│   ├── nginx/
│   │   └── nginx.conf              # reverse proxy: routes /api/* to backend, /* to frontend
│   ├── postgres/
│   │   └── init.sql                # seed data: 3 pre-baked demo learner profiles
│   ├── monitoring/
│   │   ├── prometheus.yml          # scrape config: API latency, Redis hit rate, queue depth
│   │   └── grafana/
│   │       └── dashboard.json      # pre-built Grafana dashboard export
│   └── scripts/
│       ├── sync_config.py          # generates config.ts + state_vector.ts from config.py (new)
│       ├── seed_demo.sh            # loads demo profiles into Postgres
│       └── health_check.sh         # pings all services, reports status
│
├── docs/
│   ├── architecture.md             # system architecture diagram + narrative
│   ├── api_reference.md            # all endpoints, request/response schemas
│   ├── quantum_guide.md            # VQC implementation guide (from workflow §4)
│   ├── observer_signals.md         # all 5 signals + computation formulas
│   ├── reward_design.md            # reward function rationale + YAML config reference
│   ├── educator_dashboard.md       # educator UI guide + privacy constraints
│   ├── ethics/
│   │   ├── participant_info_sheet.md  # POC participant information (new)
│   │   └── consent_form.md            # written consent form template (new)
│   └── deployment/
│       ├── local_setup.md
│       ├── vm_deployment.md
│       └── lti_integration.md      # future LTI 1.3 integration guide
│
├── research/
│   ├── lit_survey.md               # full literature review (from previous sessions)
│   ├── ablation_results/           # W&B exported plots, CSV summaries
│   │   └── .gitkeep
│   └── poc_data/                   # anonymised POC session logs (gitignored)
│       └── .gitignore
│
├── shared_config.py                # repo-root constants — canonical Python source
├── .env.example                    # all required env vars with placeholder values
├── .gitignore
├── .dockerignore
└── README.md                       # setup, architecture overview, team credits