# 📚 gen-engine Knowledge Bank

**Purpose:** Technical reference for all components, libraries, and integration patterns  
**Audience:** Developers implementing and extending gen-engine  
**Last Updated:** April 16, 2026

---

## Table of Contents

1. [Core Dependencies](#core-dependencies)
2. [Ollama + Gemma 4 E2B](#ollama--gemma-4-e2b)
3. [Kokoro TTS Integration](#kokoro-tts-integration)
4. [Manim Animation Pipeline](#manim-animation-pipeline)
5. [Stable Diffusion 1.5](#stable-diffusion-15)
6. [LivePortrait Avatar Generation](#liveportrait-avatar-generation)
7. [textstat FK Scoring](#textstat-fk-scoring)
8. [WebGazer.js Gaze Tracking](#webgazerjs-gaze-tracking)
9. [Pre-fetch Manager Implementation](#pre-fetch-manager-implementation)
10. [Error Handling Patterns](#error-handling-patterns)
11. [Testing Strategy](#testing-strategy)
12. [Deployment Configuration](#deployment-configuration)

---

## Core Dependencies

### `requirements.txt`

```txt
# Core Framework
fastapi==0.115.0
uvicorn[standard]==0.32.0
pydantic==2.9.0

# LLM Integration
ollama==0.4.1                    # Python client for Ollama API
requests==2.32.3

# Text Processing
textstat==0.7.3                  # Flesch-Kincaid scoring
spacy==3.8.2                     # Sentence tokenization for chunking
en-core-web-sm @ https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl

# Image Generation
diffusers==0.31.0                # Stable Diffusion pipeline
transformers==4.46.0
torch==2.5.0                     # PyTorch (CPU-only for now)
Pillow==11.0.0

# Audio Processing
pydub==0.25.1                    # WAV manipulation
numpy==2.1.0

# Utilities
python-dotenv==1.0.1
tenacity==9.0.0                  # Retry logic
prometheus-client==0.21.0        # Metrics export

# Testing
pytest==8.3.3
pytest-asyncio==0.24.0
httpx==0.27.2                    # Async HTTP client for tests
```

### Installation

```bash
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

---

## Ollama + Gemma 4 E2B

### Setup

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull Gemma 4 E2B model (2.5GB download)
ollama pull gemma4:e2b

# Verify installation
ollama list
# Should show: gemma4:e2b
```

### Python Client Usage

```python
import ollama

def call_gemma(prompt: str, system: str = None) -> str:
    """
    Wrapper for Ollama API calls
    """
    response = ollama.generate(
        model="gemma4:e2b",
        prompt=prompt,
        system=system,
        options={
            "temperature": 0.7,
            "top_p": 0.9,
            "num_predict": 512,  # Max tokens
        }
    )
    return response["response"]
```

### Few-Shot Prompt Template

```python
# prompts/simplify_grade8.txt

SYSTEM_PROMPT = """
You are an expert educational content writer specializing in making complex text accessible to Grade 8 readers (ages 13-14). Your goal is to preserve all factual content while using simpler sentence structures and vocabulary.

Key constraints:
- Use words an 8th grader would know
- Keep sentences under 20 words
- Break complex ideas into multiple simple sentences
- Use active voice
- Avoid jargon unless explained immediately
"""

FEW_SHOT_EXAMPLES = """
Example 1:
Original: "Photosynthesis is the biochemical process by which autotrophic organisms convert light energy into chemical energy stored in glucose molecules."
Simplified: "Photosynthesis is how plants make their own food. They use sunlight to create a sugar called glucose. This sugar gives them energy to grow."

Example 2:
Original: "The mitochondria, often referred to as the powerhouse of the cell, are responsible for ATP synthesis through oxidative phosphorylation."
Simplified: "Mitochondria are tiny parts inside cells. They make energy for the cell. We call them the powerhouse of the cell because they create so much energy."

Now simplify this:
{user_text}
"""
```

### Multimodal Input (Image + Text)

Gemma 4 E2B supports image inputs — useful for safety checking generated images:

```python
import base64

def verify_image_safety(image_path: str, concept: str) -> bool:
    """
    Use Gemma 4 multimodal to verify generated image is autism-safe
    """
    with open(image_path, "rb") as f:
        image_b64 = base64.b64encode(f.read()).decode()
    
    prompt = f"""
    Analyze this image intended to illustrate "{concept}" for an autistic learner.
    
    Check for these autism-unsafe characteristics:
    - High contrast or clutter
    - Multiple competing focal points
    - Neon or saturated colors
    - Busy backgrounds
    - Chaotic composition
    
    Respond with: SAFE or UNSAFE (reason)
    """
    
    response = ollama.generate(
        model="gemma4:e2b",
        prompt=prompt,
        images=[image_b64]
    )
    
    return response["response"].startswith("SAFE")
```

---

## Kokoro TTS Integration

### Docker Setup

```yaml
# docker-compose.yml — Kokoro TTS service

services:
  kokoro-tts:
    image: ghcr.io/remsky/kokoro-fastapi-cpu:v0.2.2
    container_name: kokoro-tts
    ports:
      - "8880:8880"
    environment:
      - LOG_LEVEL=info
    volumes:
      - ./voice_profiles:/app/voice_profiles
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8880/health"]
      interval: 30s
      timeout: 5s
      retries: 3
```

### Python Client

```python
import requests

def generate_tts(
    text: str,
    voice_profile: str = "af_bella",
    speed: float = 0.85
) -> dict:
    """
    Generate TTS audio via Kokoro-FastAPI
    OpenAI-compatible endpoint
    """
    payload = {
        "model": "kokoro",
        "input": text,
        "voice": voice_profile,
        "speed": speed,
        "response_format": "wav"
    }
    
    response = requests.post(
        "http://localhost:8880/v1/audio/speech",
        json=payload,
        timeout=5
    )
    response.raise_for_status()
    
    audio_data = response.content
    
    # Save to file
    output_path = f"/tmp/audio_{hash(text)}.wav"
    with open(output_path, "wb") as f:
        f.write(audio_data)
    
    return {
        "audio_url": output_path,
        "duration_ms": len(audio_data) // 44.1,  # 44.1kHz
        "format": "wav"
    }
```

### Voice Cloning

```python
def clone_voice(sample_audio_path: str, voice_name: str) -> str:
    """
    Register a new voice profile from 10-second sample
    Returns: voice_profile_id
    """
    with open(sample_audio_path, "rb") as f:
        files = {"audio": f}
        data = {"name": voice_name}
        
        response = requests.post(
            "http://localhost:8880/v1/voices/create",
            files=files,
            data=data
        )
    
    return response.json()["voice_id"]

# Usage
educator_voice_id = clone_voice("/tmp/teacher_sample.wav", "educator_calm")

# Use in TTS
generate_tts("This is the narration...", voice_profile=educator_voice_id)
```

### Per-Word Timestamps

```python
def extract_word_timestamps(audio_path: str) -> list[dict]:
    """
    Extract word-level timing from Kokoro output
    Uses Kokoro's built-in alignment feature
    """
    response = requests.get(
        f"http://localhost:8880/v1/audio/timestamps",
        params={"audio_path": audio_path}
    )
    
    return response.json()["timestamps"]
    # Returns: [{"word": "The", "start_ms": 0, "end_ms": 180}, ...]
```

---

## Manim Animation Pipeline

### Installation

```bash
pip install manim==0.18.1
sudo apt-get install -y ffmpeg   # Required for video rendering
```

### Writer-Reviewer Loop

```python
import subprocess
import tempfile
from pathlib import Path

def generate_manim_animation(
    concept: str,
    slide_content: str,
    max_retries: int = 2
) -> str:
    """
    Full writer-reviewer loop for Manim code generation
    Returns: path to rendered MP4
    """
    # Load system prompts
    writer_prompt = Path("prompts/manim_expert.txt").read_text()
    reviewer_prompt = Path("prompts/manim_reviewer.txt").read_text()
    
    attempt = 0
    while attempt <= max_retries:
        # Writer Step
        if attempt == 0:
            code = call_gemma(
                prompt=f"Generate Manim Scene code for: {concept}\n\nContext: {slide_content}",
                system=writer_prompt
            )
        else:
            # Reviewer Step (fixing previous error)
            code = call_gemma(
                prompt=f"Fix this Manim code:\n\n{code}\n\nError:\n{error_log}",
                system=reviewer_prompt
            )
        
        # Write code to temporary file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(code)
            scene_file = f.name
        
        # Render Step
        try:
            result = subprocess.run(
                ["manim", "-ql", scene_file, "Scene", "-o", "output.mp4"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                # Success!
                output_path = Path("media/videos/output.mp4")
                return str(output_path)
            else:
                error_log = result.stderr
                attempt += 1
        
        except subprocess.TimeoutExpired:
            error_log = "Manim rendering timed out (>30s)"
            attempt += 1
    
    # All retries exhausted — fallback
    raise ManimGenerationError("Failed to generate valid Manim animation after 2 retries")
```

### Example Generated Code

```python
# Generated by Gemma 4 E2B (Writer)

from manim import *

class Scene(Scene):
    def construct(self):
        # Title
        title = Text("Projectile Motion", font_size=48)
        self.play(Write(title))
        self.wait(1)
        self.play(title.animate.to_edge(UP))
        
        # Create projectile (ball)
        ball = Dot(point=LEFT * 5 + DOWN * 2, radius=0.2, color=BLUE)
        
        # Trajectory path
        path = ParametricFunction(
            lambda t: np.array([
                5 * t - 5,
                -4.9 * t**2 + 10 * t - 2,
                0
            ]),
            t_range=[0, 2],
            color=YELLOW
        )
        
        # Animate
        self.play(Create(path))
        self.play(MoveAlongPath(ball, path), run_time=2, rate_func=linear)
        self.wait(1)
```

---

## Stable Diffusion 1.5

### Setup

```python
from diffusers import StableDiffusionPipeline
import torch

# One-time setup (downloads 4GB model weights)
pipe = StableDiffusionPipeline.from_pretrained(
    "runwayml/stable-diffusion-v1-5",
    torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32
)

# Move to GPU if available
device = "cuda" if torch.cuda.is_available() else "cpu"
pipe = pipe.to(device)
```

### Generation with Autism-Safe Constraints

```python
AUTISM_SAFE_NEGATIVE = """
high contrast, cluttered, busy background, neon colors, 
flashing elements, multiple faces, photorealistic crowds, 
chaotic composition, sharp geometric patterns, intense shadows
"""

def generate_image(concept: str, slide_content: str) -> str:
    """
    Generate autism-safe illustration
    """
    # Build positive prompt
    prompt = f"""
    A simple, clean watercolor illustration of {concept}.
    Soft pastel color palette with muted tones.
    Minimal composition with one clear focal point.
    Generous white space. Calming and uncluttered visual design.
    Gentle, diffused lighting.
    """
    
    # Generate
    image = pipe(
        prompt=prompt,
        negative_prompt=AUTISM_SAFE_NEGATIVE,
        num_inference_steps=25,  # Balance speed/quality
        guidance_scale=7.5,
        height=512,
        width=512
    ).images[0]
    
    # Save
    output_path = f"/tmp/image_{hash(concept)}.png"
    image.save(output_path)
    
    return output_path
```

### Safety Verification (Optional)

```python
# Use Gemma 4 E2B multimodal to verify output
is_safe = verify_image_safety(output_path, concept)
if not is_safe:
    # Regenerate with stricter negative prompt
    pass
```

---

## LivePortrait Avatar Generation

### Installation

```bash
git clone https://github.com/KwaiVGI/LivePortrait
cd LivePortrait
pip install -r requirements.txt
```

### Python Integration

```python
import subprocess

def generate_avatar_video(
    source_image_path: str,
    audio_path: str,
    output_path: str = "/tmp/avatar.mp4"
) -> str:
    """
    Generate lip-synced talking avatar video
    """
    cmd = [
        "python", "inference.py",
        "--source_image", source_image_path,
        "--driving_audio", audio_path,
        "--output", output_path
    ]
    
    result = subprocess.run(
        cmd,
        cwd="/path/to/LivePortrait",
        capture_output=True,
        timeout=30
    )
    
    if result.returncode != 0:
        raise AvatarGenerationError(result.stderr)
    
    return output_path

# Usage
avatar_video = generate_avatar_video(
    source_image_path="/media/educator_photo.jpg",
    audio_path="/tmp/audio_123.wav"
)
```

---

## textstat FK Scoring

### Installation

```bash
pip install textstat==0.7.3
```

### Usage

```python
import textstat

def compute_fk_grade(text: str) -> float:
    """
    Compute Flesch-Kincaid Grade Level
    Returns: grade level (e.g., 8.7 = 8th grade, 7th month)
    """
    return textstat.flesch_kincaid_grade(text)

def verify_fk_target(text: str, target: float, tolerance: float = 1.0) -> bool:
    """
    Check if text meets target FK level (with tolerance)
    """
    actual = compute_fk_grade(text)
    return actual <= (target + tolerance)

# Example
original = "Photosynthesis is the biochemical process..."
simplified = "Photosynthesis is how plants make food..."

print(f"Original FK: {compute_fk_grade(original)}")  # 14.2
print(f"Simplified FK: {compute_fk_grade(simplified)}")  # 7.8
print(f"Meets Grade 8 target: {verify_fk_target(simplified, 9.0)}")  # True
```

---

## WebGazer.js Gaze Tracking

### Frontend Integration

```typescript
// frontend/src/lib/gazeObserver.ts

import WebGazer from 'webgazer';

export class GazeObserver {
    private fixationBuffer: Array<{x: number, y: number, t: number}> = [];
    private isActive: boolean = false;

    async start() {
        await WebGazer.setGazeListener((data, elapsedTime) => {
            if (data == null) return;
            this.fixationBuffer.push({
                x: data.x,
                y: data.y,
                t: elapsedTime
            });
        }).begin();
        
        this.isActive = true;
    }

    flushSignals(): {fixationDensity: number, regressionCount: number} {
        const fixDensity = this.computeFixationDensity(this.fixationBuffer);
        const regressions = this.countRegressions(this.fixationBuffer);
        
        this.fixationBuffer = [];
        
        return {
            fixationDensity: fixDensity,
            regressionCount: regressions
        };
    }

    private computeFixationDensity(buffer: Array<{x: number, y: number, t: number}>): number {
        // Group nearby points into fixations (< 30px distance)
        // Return: avg fixation duration / total time
        // Higher = more sustained attention
        // Implementation details...
    }

    private countRegressions(buffer: Array<{x: number, y: number, t: number}>): number {
        // Count leftward saccades (dyslexia signal)
        let regressionCount = 0;
        for (let i = 1; i < buffer.length; i++) {
            if (buffer[i].x < buffer[i-1].x - 50) {  // Threshold
                regressionCount++;
            }
        }
        return regressionCount;
    }

    stop() {
        WebGazer.end();
        this.isActive = false;
    }
}
```

---

## Pre-fetch Manager Implementation

### Core Logic

```python
from concurrent.futures import ThreadPoolExecutor, Future
from typing import Dict, Optional, Any
import time

class PrefetchManager:
    def __init__(self, max_workers: int = 4):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.cache: Dict[str, Any] = {}
        self.active_tasks: Dict[str, Future] = {}
        self.cache_ttl: Dict[str, float] = {}
        self.TTL_SECONDS = 600  # 10 minutes
    
    def start_prefetch(
        self,
        action_candidates: list[int],
        slide_content: str,
        session_id: str
    ):
        """
        Start background generation for top-N actions
        """
        for action_id in action_candidates[:2]:  # Top 2 only
            cache_key = self._make_key(session_id, action_id, slide_content)
            
            # Skip if already cached
            if self._is_cached(cache_key):
                continue
            
            # Submit async task
            future = self.executor.submit(
                self._generate_for_action,
                action_id,
                slide_content,
                session_id
            )
            self.active_tasks[cache_key] = future
    
    def get_cached_or_wait(
        self,
        action_id: int,
        slide_content: str,
        session_id: str,
        timeout: int = 30
    ) -> Optional[dict]:
        """
        Retrieve from cache or block until ready
        """
        cache_key = self._make_key(session_id, action_id, slide_content)
        
        # Immediate cache hit
        if self._is_cached(cache_key):
            return self.cache[cache_key]
        
        # Wait for active task
        if cache_key in self.active_tasks:
            future = self.active_tasks.pop(cache_key)
            try:
                result = future.result(timeout=timeout)
                self._cache_result(cache_key, result)
                return result
            except TimeoutError:
                return None  # Trigger fallback
        
        # Not pre-fetched — generate synchronously
        result = self._generate_for_action(action_id, slide_content, session_id)
        self._cache_result(cache_key, result)
        return result
    
    def _generate_for_action(
        self,
        action_id: int,
        slide_content: str,
        session_id: str
    ) -> dict:
        """
        Dispatch to appropriate generator
        """
        if action_id == 2:
            return text_simplify(slide_content)
        elif action_id == 3:
            # Route by content type
            if is_stem_content(slide_content):
                return manim_gen(slide_content)
            else:
                return image_gen(slide_content)
        elif action_id == 4:
            return quiz_injector(slide_content, session_id)
        else:
            return {}
    
    def _make_key(self, session_id: str, action_id: int, content: str) -> str:
        return f"{session_id}:{action_id}:{hash(content)}"
    
    def _is_cached(self, key: str) -> bool:
        if key not in self.cache:
            return False
        # Check TTL
        if time.time() - self.cache_ttl.get(key, 0) > self.TTL_SECONDS:
            del self.cache[key]
            del self.cache_ttl[key]
            return False
        return True
    
    def _cache_result(self, key: str, result: dict):
        self.cache[key] = result
        self.cache_ttl[key] = time.time()
```

---

## Error Handling Patterns

### Retry Decorator

```python
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import requests

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(requests.exceptions.RequestException)
)
def call_external_service(url: str, payload: dict) -> dict:
    response = requests.post(url, json=payload, timeout=10)
    response.raise_for_status()
    return response.json()
```

### Fallback Chain

```python
def generate_with_fallback(action_id: int, content: str) -> dict:
    """
    Attempt primary generator → fallback on timeout/error
    """
    try:
        # Primary
        result = primary_generator(action_id, content, timeout=30)
        return result
    except TimeoutError:
        # Fallback 1
        try:
            result = fallback_generator_1(action_id, content, timeout=15)
            return result
        except Exception:
            # Final fallback
            return minimal_fallback(action_id, content)
```

---

## Testing Strategy

### Unit Test Example

```python
# __tests__/test_text_simplify.py

import pytest
from generators.text_simplify import simplify_text
from textstat import flesch_kincaid_grade

def test_fk_verification_grade8():
    original = "Photosynthesis is the biochemical process by which autotrophic organisms convert light energy."
    
    result = simplify_text(original, target_level="grade8")
    
    assert result["fk_grade"] <= 9.0
    assert len(result["simplified_text"]) > 0
    assert "simplified" in result
    assert result["original_fk"] > result["fk_grade"]  # Actually simplified

def test_fk_retry_on_failure(monkeypatch):
    """Test that FK verification triggers retry when target not met"""
    
    call_count = 0
    
    def mock_gemma_call(prompt, system):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return "This is a very complex and sophisticated sentence."  # FK ~12
        else:
            return "This is a simple sentence."  # FK ~3
    
    monkeypatch.setattr("generators.text_simplify.call_gemma", mock_gemma_call)
    
    result = simplify_text("Complex text", target_level="grade8")
    
    assert call_count == 2  # Retry happened
    assert result["fk_grade"] <= 9.0
```

### Integration Test Example

```python
# __tests__/integration/test_full_pipeline.py

import pytest
from httpx import AsyncClient
from main import app

@pytest.mark.asyncio
async def test_generate_endpoint_text_simplify():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/api/generate", json={
            "action_id": 2,
            "slide_content": "The mitochondria...",
            "learner_level": "grade8",
            "session_id": "test-123",
            "confidence": 0.75,
            "state_vector": {}
        })
    
    assert response.status_code == 200
    data = response.json()
    assert "simplified_text" in data["content"]
    assert data["content"]["fk_grade"] <= 9.0
```

---

## Deployment Configuration

### Docker Compose Full Stack

```yaml
# docker-compose.yml

version: '3.8'

services:
  gen-engine:
    build: .
    container_name: gen-engine
    ports:
      - "8001:8001"
    environment:
      - OLLAMA_HOST=http://ollama:11434
      - KOKORO_HOST=http://kokoro-tts:8880
      - LOG_LEVEL=info
    volumes:
      - ./prompts:/app/prompts:ro
      - gen-cache:/app/cache
    depends_on:
      - ollama
      - kokoro-tts
    restart: unless-stopped

  ollama:
    image: ollama/ollama:latest
    container_name: ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama-models:/root/.ollama
    restart: unless-stopped

  kokoro-tts:
    image: ghcr.io/remsky/kokoro-fastapi-cpu:v0.2.2
    container_name: kokoro-tts
    ports:
      - "8880:8880"
    volumes:
      - kokoro-voices:/app/voice_profiles
    restart: unless-stopped

  prometheus:
    image: prom/prometheus:v2.54.1
    container_name: prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml:ro
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
    restart: unless-stopped

volumes:
  ollama-models:
  gen-cache:
  kokoro-voices:
```

---

<div align="center">

**Next:** [Latest Research Findings](./latest_findings.md)

</div>