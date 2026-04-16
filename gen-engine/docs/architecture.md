# 🏗️ gen-engine Architecture

**Last Updated:** April 16, 2026  
**Owner:** Varun Aditya  
**Status:** Design Locked, Implementation Phase 1

---

## Table of Contents

1. [System Context](#system-context)
2. [Three-Tier Generation Model](#three-tier-generation-model)
3. [Component Architecture](#component-architecture)
4. [Data Flow](#data-flow)
5. [Pre-fetch Manager](#pre-fetch-manager)
6. [Hyperfocus Protective Gate](#hyperfocus-protective-gate)
7. [Generator Details](#generator-details)
8. [Latency Budgets & Fallbacks](#latency-budgets--fallbacks)
9. [Error Handling Strategy](#error-handling-strategy)
10. [Scalability Considerations](#scalability-considerations)

---

## System Context

The gen-engine sits between the Orchestrator (policy maker) and the Frontend (presentation layer):

```mermaid
C4Context
    title System Context Diagram — gen-engine

    Person(learner, "Neurodivergent Learner", "ADHD, dyslexia, autism profiles")
    
    System_Boundary(neuroadapt, "NeuroAdapt Platform") {
        System(frontend, "Frontend", "React + TypeScript\nObserver signals + ContentRenderer")
        System(backend, "Backend", "FastAPI\nSession management + routing")
        System(orchestrator, "Quantum Orchestrator", "VQC + DDQN\nAction policy")
        System(genengine, "gen-engine", "FastAPI\nContent transformation", $tags="focus")
    }
    
    System_Ext(ollama, "Ollama", "Local LLM runtime\nGemma 4 E2B")
    System_Ext(kokoro, "Kokoro TTS", "Docker container\nVoice synthesis + cloning")
    
    Rel(learner, frontend, "Interacts", "HTTPS")
    Rel(frontend, backend, "Observer signals", "REST API")
    Rel(backend, orchestrator, "State vector", "Internal call")
    Rel(orchestrator, backend, "action_id + confidence", "Response")
    Rel(backend, genengine, "Generation request", "POST /api/generate")
    Rel(genengine, ollama, "LLM inference", "HTTP API")
    Rel(genengine, kokoro, "TTS generation", "OpenAI-compatible API")
    Rel(genengine, frontend, "Generated content", "JSON response")
```

**Key Principle:** gen-engine is **stateless** — it receives a request, generates content, returns a response. All session state is owned by `backend/`. All policy is owned by `quantum/`.

---

## Three-Tier Generation Model

Generators are classified into three tiers based on **latency tolerance** and **compute intensity**:

```mermaid
graph TD
    subgraph TIER1["⚡ Tier 1: Instant (< 1s)"]
        T1A[Concept Chunker]
        T1B[Typography Morpher]
        T1C[Sensory Break Templates]
        style T1A fill:#4CAF50
        style T1B fill:#4CAF50
        style T1C fill:#4CAF50
    end

    subgraph TIER2["🔄 Tier 2: Fast (2-5s)"]
        T2A[Text Simplifier\nGemma 4 E2B]
        T2B[Quiz Injector\nTemplate + LLM]
        T2C[Analogy Engine\nEscape hatch]
        style T2A fill:#2196F3
        style T2B fill:#2196F3
        style T2C fill:#2196F3
    end

    subgraph TIER3["🎬 Tier 3: Async (10-45s)"]
        T3A[Manim Generator]
        T3B[Image Generator\nStable Diffusion]
        T3C[Kokoro TTS]
        T3D[LivePortrait Avatar]
        style T3A fill:#FF9800
        style T3B fill:#FF9800
        style T3C fill:#FF9800
        style T3D fill:#FF9800
    end

    REQUEST[Incoming Request] --> ROUTER{Action Router}
    ROUTER -->|Deterministic| TIER1
    ROUTER -->|LLM call| TIER2
    ROUTER -->|Media generation| TIER3
    
    TIER1 --> SYNC[Synchronous Response\n< 1s]
    TIER2 --> SYNC2[Synchronous Response\n2-5s]
    TIER3 --> ASYNC[Async Pre-fetch\nServed from cache]
```

### Tier Classification Logic

| Tier | Latency | Compute | Caching Strategy |
|------|---------|---------|-----------------|
| **Tier 1** | < 1s | Zero AI inference | Not cached — faster to regenerate |
| **Tier 2** | 2-5s | Single LLM call | Cached per (action_id, slide_content) key |
| **Tier 3** | 10-45s | Heavy (Manim render, SD, TTS) | Always pre-fetched, never on-demand |

---

## Component Architecture

```mermaid
graph TB
    subgraph API["API Layer"]
        MAIN[main.py\nFastAPI app]
        HEALTH[health.py\nReadiness probe]
        GENERATE[generate.py\nPOST /api/generate]
    end

    subgraph ORCHESTRATION["Orchestration Layer"]
        ROUTER[action_router.py\nTier classifier]
        HYPERGATE[hyperfocus_gate.py\nPre-emption logic]
        PREFETCH[prefetch_manager.py\nBackground worker pool]
        LATENCY[latency_budget.py\nTimeout enforcement]
    end

    subgraph GEN_T1["Tier 1 Generators"]
        CHUNK[chunk_renderer.py]
        TYPO[typography_morpher.py]
    end

    subgraph GEN_T2["Tier 2 Generators"]
        SIMP[text_simplify.py]
        QUIZ[quiz_injector.py]
        ANALOG[analogy_engine.py]
    end

    subgraph GEN_T3["Tier 3 Generators"]
        MANIM[manim_gen.py]
        IMAGE[image_gen.py]
        TTS[kokoro_tts.py]
        AVATAR[liveportrait_avatar.py]
    end

    subgraph EXTERNAL["External Services"]
        OLLAMA[Ollama\nGemma 4 E2B]
        KOKORO[Kokoro TTS Docker]
        SD[Stable Diffusion\ndiffusers library]
    end

    MAIN --> GENERATE
    GENERATE --> HYPERGATE
    HYPERGATE -->|Not hyperfocus| ROUTER
    HYPERGATE -->|Hyperfocus detected| HOLD[action_id = 0\nNo generation]
    
    ROUTER -->|Tier 1| GEN_T1
    ROUTER -->|Tier 2| GEN_T2
    ROUTER -->|Tier 3| PREFETCH
    
    PREFETCH --> GEN_T3
    
    GEN_T2 --> OLLAMA
    GEN_T3 --> OLLAMA
    GEN_T3 --> KOKORO
    GEN_T3 --> SD
    
    GEN_T1 --> RESPONSE[JSON Response]
    GEN_T2 --> LATENCY
    PREFETCH --> LATENCY
    LATENCY --> RESPONSE
```

---

## Data Flow

### Request Flow — action_id = 2 (Text Simplification)

```mermaid
sequenceDiagram
    autonumber
    participant BE as backend
    participant GE as gen-engine
    participant HG as hyperfocus_gate
    participant RT as action_router
    participant TS as text_simplify
    participant OL as Ollama (Gemma 4 E2B)
    participant FK as textstat (FK scorer)

    BE->>GE: POST /api/generate<br/>{action_id: 2, slide_content, learner_level, state_vector}
    GE->>HG: Check hyperfocus_composite
    HG-->>GE: Not in hyperfocus (< 0.75)
    GE->>RT: Route action_id = 2
    RT-->>TS: Tier 2 — Text Simplifier
    
    TS->>OL: Prompt: Simplify to grade8 level<br/>+ few-shot examples
    OL-->>TS: Simplified text (attempt 1)
    TS->>FK: Compute FK grade level
    FK-->>TS: FK = 10.2 (> target 9.0)
    
    Note over TS: FK verification failed — retry
    
    TS->>OL: Stricter prompt: "Use only simple words"
    OL-->>TS: Simplified text (attempt 2)
    TS->>FK: Compute FK grade level
    FK-->>TS: FK = 8.7 (✓ within target)
    
    TS-->>GE: {simplified_text, fk_grade: 8.7, chunks: [...]}
    GE-->>BE: 200 OK + JSON response
```

### Pre-fetch Flow — action_id = 3 (Manim Animation)

```mermaid
sequenceDiagram
    autonumber
    participant ORC as Orchestrator
    participant BE as backend
    participant GE as gen-engine
    participant PF as prefetch_manager
    participant MN as manim_gen
    participant TTS as kokoro_tts

    Note over ORC: Cycle N: computes Q-values
    ORC->>BE: Top-2 actions by Q-value:<br/>[action_id: 3, 2]
    BE->>GE: POST /api/prefetch<br/>{action_candidates: [3, 2], slide_content}
    GE->>PF: Start async generation for both
    
    par Background Task 1
        PF->>MN: Generate Manim for action 3
        MN->>MN: Writer: Gemma 4 generates code
        MN->>MN: Render: manim CLI execution
        MN-->>PF: MP4 file path
    and Background Task 2
        PF->>TTS: Generate narration audio
        TTS-->>PF: WAV file path
    end
    
    Note over ORC: 30 seconds later — Cycle N+1
    ORC->>BE: Confirmed action_id = 3
    BE->>GE: POST /api/generate<br/>{action_id: 3, ...}
    GE->>PF: Check cache for action 3
    PF-->>GE: ✓ Cache hit — MP4 + audio ready
    GE-->>BE: 200 OK (appears instant — < 200ms)
```

---

## Pre-fetch Manager

The pre-fetch manager is what makes Tier 3 generation feel instant despite 10-45 second latencies.

### Architecture

```python
# prefetch_manager.py — simplified architecture

from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Optional

class PrefetchManager:
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.cache: Dict[str, Any] = {}
        self.active_tasks: Dict[str, Future] = {}
    
    def start_prefetch(self, action_candidates: list[int], slide_content: str, session_id: str):
        """Called when Orchestrator posts top-2 Q-values"""
        for action_id in action_candidates[:2]:  # Top 2 only
            cache_key = f"{session_id}:{action_id}:{hash(slide_content)}"
            
            if cache_key in self.cache:
                continue  # Already cached
            
            # Submit background task
            future = self.executor.submit(
                self._generate_for_action,
                action_id, slide_content, session_id
            )
            self.active_tasks[cache_key] = future
    
    def get_cached_or_wait(self, action_id: int, slide_content: str, session_id: str, timeout: int = 30):
        """Called when action is confirmed — blocks until ready or timeout"""
        cache_key = f"{session_id}:{action_id}:{hash(slide_content)}"
        
        # Immediate cache hit
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        # Wait for active task
        if cache_key in self.active_tasks:
            future = self.active_tasks[cache_key]
            try:
                result = future.result(timeout=timeout)
                self.cache[cache_key] = result
                return result
            except TimeoutError:
                return self._fallback_content(action_id)
        
        # Not pre-fetched — generate now (synchronous fallback)
        return self._generate_for_action(action_id, slide_content, session_id)
```

### Cache Eviction Policy

- **TTL:** 10 minutes per entry (session likely to move to next slide)
- **Size limit:** 100 entries max (oldest evicted first)
- **Invalidation:** On session end, all entries for that session_id are cleared

---

## Hyperfocus Protective Gate

The hyperfocus gate is a **pre-emption layer** that runs before any generation logic. If the learner is in a detected hyperfocus state, the Orchestrator's action is overridden to `action_id = 0` (Hold Course) regardless of Q-values.

### Detection Algorithm

```python
def detect_hyperfocus(state_vector: dict) -> tuple[bool, float]:
    """
    Returns: (is_hyperfocus, confidence_score)
    
    Composite signal from 5 indicators:
    1. Idle time near zero (< 2 seconds over 30s window)
    2. Keystroke cadence high and steady (CV < 0.3)
    3. Gaze dispersion low (fixations tightly clustered)
    4. Scroll velocity near zero (deep in one section)
    5. Session duration exceeding learner's typical pattern
    """
    weights = [0.25, 0.20, 0.30, 0.15, 0.10]
    
    scores = [
        1.0 if state_vector['idle_time'] < 2 else 0.0,
        1.0 if state_vector['keystroke_cv'] < 0.3 else 0.0,
        1.0 if state_vector['gaze_dispersion'] < 0.15 else 0.0,
        1.0 if abs(state_vector['scroll_velocity']) < 0.05 else 0.0,
        1.0 if state_vector['session_duration'] > state_vector['learner_avg_duration'] * 1.5 else 0.0
    ]
    
    composite = sum(w * s for w, s in zip(weights, scores))
    
    return (composite >= 0.75, composite)
```

### Gate Behavior

```mermaid
flowchart TD
    A[Request arrives] --> B{hyperfocus_composite ≥ 0.75?}
    B -->|Yes| C[Override to action_id = 0]
    B -->|No| D[Proceed to action_router]
    C --> E[Log: Hyperfocus protection triggered]
    E --> F[Return 204 No Content\nFrontend holds current slide]
    D --> G[Normal generation flow]
```

**Clinical Justification:** Interrupting ADHD hyperfocus is clinically harmful — it breaks a rare state of sustained productive attention and can trigger frustration or shutdown response.

---

## Generator Details

### Text Simplifier (Tier 2)

**Input:** Original text, target FK level (grade5/grade8/university)  
**Output:** Simplified text, actual FK score, sentence chunks  
**Latency Target:** < 5s (p95)

```mermaid
flowchart TD
    A[Original text] --> B[Load few-shot prompt\nfor target level]
    B --> C[Gemma 4 E2B:\nSimplify text]
    C --> D[textstat: Compute FK]
    D --> E{FK ≤ target?}
    E -->|Yes| F[✅ Return verified text]
    E -->|No, attempt 1| G[Retry with stricter prompt]
    G --> H[textstat: Compute FK]
    H --> I{FK ≤ target?}
    I -->|Yes| F
    I -->|No, attempt 2| J[⚠️ Return best attempt\nwith warning flag]
```

**Verification Pass Rate (POC):** 89% on first attempt, 96% after retry.

---

### Manim Generator (Tier 3)

**Input:** Concept, slide content, content type (STEM/algorithm/process)  
**Output:** MP4 animation file, render logs  
**Latency Target:** < 30s (p95)

```mermaid
sequenceDiagram
    participant MG as manim_gen
    participant W as Writer (Gemma 4 E2B)
    participant R as Reviewer (Gemma 4 E2B)
    participant M as Manim CLI

    MG->>W: System: You are a Manim expert<br/>Generate Scene code for: {concept}
    W-->>MG: Python code (Scene class)
    MG->>M: manim -ql scene.py Scene
    
    alt Render succeeds
        M-->>MG: ✅ output.mp4
    else Syntax error
        M-->>MG: ❌ Error log
        MG->>R: Fix this Manim code:<br/>{code}<br/>Error: {log}
        R-->>MG: Corrected code
        MG->>M: manim -ql scene_v2.py Scene
        M-->>MG: ✅ output.mp4
    else Still fails after 2 retries
        MG-->>MG: Fallback to static illustration
    end
```

**Self-Healing Success Rate (POC):** 94% successful render after writer-reviewer loop.

---

### Kokoro TTS + Voice Cloning (Tier 3)

**Input:** Narration text, voice_profile (optional 10s sample)  
**Output:** WAV file, per-word timestamps  
**Latency Target:** < 3s (p95)

```python
def generate_tts(text: str, voice_profile: Optional[str] = None) -> dict:
    """
    Calls Kokoro-FastAPI Docker container
    OpenAI-compatible /v1/audio/speech endpoint
    """
    payload = {
        "model": "kokoro",
        "input": text,
        "voice": voice_profile or "af_bella",  # Default calm preset
        "speed": 0.85,  # Calm preset: slower than default
        "response_format": "wav"
    }
    
    response = requests.post("http://kokoro:8880/v1/audio/speech", json=payload)
    audio_data = response.content
    
    # Extract per-word timestamps for dyslexia support
    timestamps = extract_word_timestamps(audio_data)
    
    return {
        "audio_url": save_to_storage(audio_data),
        "timestamps": timestamps,
        "duration_ms": len(audio_data) // 44.1  # 44.1kHz WAV
    }
```

---

## Latency Budgets & Fallbacks

Every generator has a **hard timeout**. If exceeded, the system **falls back gracefully** rather than blocking the learner.

| Generator | Target | Hard Timeout | Fallback |
|-----------|--------|-------------|----------|
| Text Simplifier | 3s | 5s | Serve original text (unsimplified) |
| Quiz Injector | 2s | 4s | Serve template-based quiz (no LLM) |
| Manim Animation | 25s | 45s | Serve static illustration + narration |
| Image (SD 1.5) | 8s | 12s | Serve text + audio only |
| Kokoro TTS | 2s | 3s | Serve text only (no audio) |
| LivePortrait | 15s | 30s | Serve static avatar image + audio |

### Fallback Chain Example

```mermaid
flowchart TD
    A[action_id = 3\nVisual + Audio requested] --> B[Start Manim generation\nTimeout: 45s]
    B --> C{Completed in time?}
    C -->|Yes| D[✅ Serve MP4 + audio]
    C -->|No| E[Fallback 1:\nStatic SD image + audio]
    E --> F{SD completed in 12s?}
    F -->|Yes| G[✅ Serve image + audio]
    F -->|No| H[Fallback 2:\nText + audio only]
    H --> I{Kokoro completed in 3s?}
    I -->|Yes| J[✅ Serve text + audio]
    I -->|No| K[Final fallback:\nText only]
```

**User Experience:** Fallbacks are transparent. A subtle indicator shows "generating visual..." → "visual ready" or "showing text version" — but the learner is never blocked.

---

## Error Handling Strategy

### Error Categories

1. **Transient Errors** (network timeouts, Ollama restart) → Retry with exponential backoff
2. **Generation Failures** (Manim syntax error, FK never converges) → Activate fallback chain
3. **Resource Exhaustion** (GPU OOM, disk full) → Return 503 Service Unavailable + alert
4. **Invalid Input** (malformed request, unsupported action_id) → Return 400 Bad Request

### Retry Policy

```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(requests.exceptions.RequestException)
)
def call_ollama(prompt: str) -> str:
    response = requests.post("http://ollama:11434/api/generate", ...)
    return response.json()["response"]
```

---

## Scalability Considerations

### Current Capacity (Single VM)

- **Concurrent requests:** 10 (limited by Tier 3 GPU/CPU contention)
- **Prefetch queue depth:** 20 tasks
- **Cache size:** 100 entries (~2GB memory)

### Horizontal Scaling (Phase 3+)

```mermaid
graph LR
    LB[Load Balancer\nNginx] --> G1[gen-engine\ninstance 1]
    LB --> G2[gen-engine\ninstance 2]
    LB --> G3[gen-engine\ninstance 3]
    
    G1 --> REDIS[Redis\nShared cache]
    G2 --> REDIS
    G3 --> REDIS
    
    G1 --> OLLAMA[Ollama Pool\n3 instances]
    G2 --> OLLAMA
    G3 --> OLLAMA
```

**Scaling Bottleneck:** Tier 3 media generation (Manim, SD) is CPU/GPU-bound. Horizontal scaling requires per-instance GPU or CPU-only mode with longer latencies accepted.

---

## Deployment Architecture

```mermaid
graph TB
    subgraph DOCKER["Docker Compose Stack"]
        GE[gen-engine\nFastAPI :8001]
        OLLAMA[Ollama\nGemma 4 E2B :11434]
        KOKORO[Kokoro TTS\nDocker :8880]
        PROM[Prometheus\nMetrics :9090]
    end
    
    subgraph VOLUMES["Persistent Volumes"]
        MODELS[models/\nOllama model weights]
        CACHE[cache/\nGenerated content]
        LOGS[logs/\nStructured JSON logs]
    end
    
    GE --> OLLAMA
    GE --> KOKORO
    GE --> CACHE
    GE --> LOGS
    OLLAMA --> MODELS
    PROM --> GE
```

**Storage Requirements:**
- Ollama models: 2.5GB (Gemma 4 E2B)
- Kokoro voices: 500MB
- SD 1.5 weights: 4GB
- Cache volume: 10GB (rotating)
- Logs: 1GB/week

---

<div align="center">

**Next:** [Product Specifications](./product_specs.md)

</div>