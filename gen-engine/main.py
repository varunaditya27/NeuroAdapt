"""
gen-engine FastAPI Application Entry Point

================================================================================
PURPOSE:
    Main application server for the Generative Synthesis Engine microservice.
    Initializes FastAPI, loads all routers, and serves /api/generate endpoint.

DEPENDENCIES:
    - fastapi==0.115.6 : Web framework
    - uvicorn==0.32.1 : ASGI application server
    - pydantic==2.10.6 : Request/response validation
    - orchestration.action_router : Routes by action_id to appropriate generator
    - routers.generate : POST /api/generate route
    - routers.health : GET /health route

EXTERNAL SERVICES:
    - Ollama (http://localhost:11434) : Local LLM serving Gemma 4 E2B
    - Kokoro TTS (http://localhost:8880) : Audio generation service
    - Stable Diffusion (local via diffusers) : Image generation
    - Manim (subprocess) : STEM animation rendering
    - LivePortrait (subprocess) : Avatar video generation

STARTUP/SHUTDOWN:
    - Initialize generator caches on startup
    - Load prompt templates from prompts/
    - Warm up Ollama connection
    - Initialize Prometheus metrics

ENVIRONMENT VARIABLES:
    - OLLAMA_URL : Default "http://localhost:11434"
    - TTS_URL : Default "http://localhost:8880"
    - GENERATION_CACHE_SIZE : Max in-memory cache entries (default: 500)
    - LOG_LEVEL : "DEBUG", "INFO", "WARNING", "ERROR" (default: "INFO")

KEY FUNCTIONS:
    - app.get("/health") : Health check endpoint
    - app.post("/api/generate") : Main content generation endpoint
    - app lifespan : Initialize all generators and clean up resources

INTEGRATION POINTS:
    - Backend (NeuroAdapt orchestrator) sends POST requests to /api/generate
    - Returns {action_id, content, generation_time_ms, warning?, timestamp}
    - Forwards state_vector and confidence from orchestrator to generators

METRICS (Prometheus):
    - gen_engine_requests_total : Total requests by action_id
    - gen_engine_generation_time_seconds : Latency histogram
    - gen_engine_cache_hit_ratio : Cache effectiveness
    - gen_engine_errors_total : Failures by error type
================================================================================
"""

import os
import sys
import logging
import shutil
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from pathlib import Path
from datetime import datetime
from typing import Any, Optional, Tuple

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import JSONResponse, Response
import requests
from orchestration.prefetch_manager import prefetch_manager
from orchestration.llm_provider import verify_llm_provider
from models.response_schemas import HealthResponse
from routers.generate import router as generate_router
from routers.health import router as health_router

# ============================================================================
# CONFIGURATION & LOGGING
# ============================================================================

load_dotenv()

CONFIG: dict[str, Any] = {
    "OLLAMA_URL": os.getenv("OLLAMA_URL", "http://localhost:11434"),
    "KOKORO_TTS_URL": os.getenv("KOKORO_TTS_URL") or os.getenv("TTS_URL", "http://localhost:8880"),
    "POSTGRES_URL": os.getenv("POSTGRES_URL")
    or os.getenv("DATABASE_URL", "postgresql://user:pass@localhost/neuroadapt"),
    "LOG_LEVEL": os.getenv("LOG_LEVEL", "INFO"),
    "CACHE_MAX_SIZE": int(os.getenv("CACHE_MAX_SIZE", os.getenv("GENERATION_CACHE_SIZE", "100"))),
    "CACHE_TTL_SECONDS": int(os.getenv("CACHE_TTL_SECONDS", "600")),
}

SERVICE_CHECKS = [
    ("Ollama", f"{CONFIG['OLLAMA_URL']}/api/tags"),
    ("Kokoro TTS", f"{CONFIG['KOKORO_TTS_URL']}/health"),
]
HEALTH_REFRESH_INTERVAL_SECONDS = max(1.0, float(os.getenv("HEALTH_REFRESH_INTERVAL_SECONDS", "5")))
REQUIRED_PROMPTS = [
    "simplify_grade5",
    "simplify_grade8",
    "simplify_university",
    "manim_expert",
    "manim_reviewer",
    "image_gen_base",
    "analogy_generator",
]

logging.basicConfig(
    level=getattr(logging, str(CONFIG["LOG_LEVEL"])),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# Prometheus metrics
try:
    from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    logger.warning("prometheus-client not available, metrics disabled")


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Run startup and shutdown logic via FastAPI lifespan hooks."""
    logger.info("=" * 80)
    logger.info("gen-engine STARTING UP")
    logger.info("=" * 80)

    app_state["startup_time"] = datetime.now()

    _refresh_services(force=True)
    for service_name, service_info in app_state["services"].items():
        is_available = bool(service_info.get("available"))
        error = service_info.get("error")

        if is_available:
            logger.info(f"✓ {service_name} is available")
        else:
            logger.warning(f"✗ {service_name} unavailable: {error} (will degrade gracefully)")

    # Verify LLM provider configuration
    try:
        provider_name, is_healthy = verify_llm_provider()
        app_state["llm_provider"] = {"name": provider_name, "healthy": is_healthy}
        if is_healthy:
            logger.info(f"✓ LLM provider '{provider_name}' is available")
        else:
            logger.warning(f"⚠ LLM provider '{provider_name}' unhealthy (degradation may occur)")
    except Exception as e:
        logger.error(f"✗ Failed to initialize LLM provider: {e}")
        app_state["llm_provider"] = {"name": "unknown", "healthy": False, "error": str(e)}

    app_state["prompts"] = load_prompts()
    logger.info(f"✓ Loaded {len(app_state['prompts'])} prompt templates")

    missing_required_prompts = [
        prompt_name for prompt_name in REQUIRED_PROMPTS if prompt_name not in app_state["prompts"]
    ]
    app_state["prompt_health"] = {"missing_required": missing_required_prompts}
    if missing_required_prompts:
        logger.warning(
            "✗ Missing required prompt templates: %s", ", ".join(missing_required_prompts)
        )
    else:
        logger.info("✓ All required prompt templates present")

    app_state["cache"] = {}
    logger.info(f"✓ Cache initialized (max size: {CONFIG['CACHE_MAX_SIZE']})")

    logger.info("=" * 80)
    logger.info("gen-engine READY")
    logger.info("=" * 80)

    try:
        yield
    finally:
        logger.info("gen-engine shutting down")
        app_state["cache"].clear()


# ============================================================================
# FASTAPI APP INITIALIZATION
# ============================================================================

app = FastAPI(
    title="gen-engine",
    version="0.1.0",
    description="Generative Synthesis Engine for neurodivergent content adaptation",
    lifespan=lifespan,
)

# Prometheus metrics
if PROMETHEUS_AVAILABLE:
    # Request metrics
    REQUEST_COUNT = Counter(
        "gen_engine_requests_total", "Total number of generation requests", ["action_id", "status"]
    )
    REQUEST_LATENCY = Histogram(
        "gen_engine_request_duration_seconds", "Request duration in seconds", ["action_id"]
    )
    CACHE_HITS = Counter("gen_engine_cache_hits_total", "Total number of cache hits", ["action_id"])
    CACHE_MISSES = Counter(
        "gen_engine_cache_misses_total", "Total number of cache misses", ["action_id"]
    )
    CACHE_SIZE = Gauge("gen_engine_cache_size", "Current cache size")
    FALLBACK_EVENTS = Counter(
        "gen_engine_fallback_events_total",
        "Total fallback events emitted by generation flows",
        ["action_id", "stage"],
    )
    TIMEOUT_EVENTS = Counter(
        "gen_engine_timeout_events_total",
        "Total timeout-triggered degradation events",
        ["action_id", "stage"],
    )
    HYPERFOCUS_OVERRIDES = Counter(
        "gen_engine_hyperfocus_overrides_total",
        "Total no-content responses caused by hyperfocus protection",
        ["reason"],
    )
    FK_VERIFICATION_RESULTS = Counter(
        "gen_engine_fk_verification_results_total",
        "FK verification outcomes for text simplification responses",
        ["target_level", "result"],
    )
    PREFETCH_REQUESTS = Counter(
        "gen_engine_prefetch_requests_total", "Total number of prefetch API requests", ["status"]
    )
    PREFETCH_TASKS_QUEUED = Counter(
        "gen_engine_prefetch_tasks_queued_total",
        "Total number of speculative tasks queued by prefetch requests",
    )

# Global state (Phase 0: minimal)
app_state: dict[str, Any] = {
    "cache": {},
    "prompts": {},
    "prompt_health": {"missing_required": []},
    "services": {},
    "startup_time": None,
}

# ============================================================================
# SERVICE VERIFICATION UTILITIES
# ============================================================================


def verify_service(service_name: str, url: str, timeout: int = 2) -> Tuple[bool, Optional[str]]:
    """
    Verify external service connectivity.
    Returns (is_available, error_message)
    """
    try:
        response = requests.get(url, timeout=timeout)
        if 200 <= response.status_code < 400:
            return True, None
        return False, f"HTTP {response.status_code}"
    except requests.exceptions.Timeout:
        return False, f"Timeout after {timeout}s"
    except requests.exceptions.ConnectionError:
        return False, "Connection refused"
    except Exception as e:
        return False, str(e)


def load_prompts() -> dict[str, str]:
    """Load all prompt templates from prompts/ directory."""
    prompts: dict[str, str] = {}
    prompts_dir = Path(__file__).parent / "prompts"

    if not prompts_dir.exists():
        logger.warning(f"Prompts directory not found at {prompts_dir}")
        return prompts

    for prompt_file in prompts_dir.glob("*.txt"):
        try:
            with open(prompt_file, "r") as f:
                prompts[prompt_file.stem] = f.read()
            logger.debug(f"Loaded prompt: {prompt_file.stem}")
        except Exception as e:
            logger.error(f"Failed to load prompt {prompt_file.stem}: {e}")

    return prompts


def _directory_size_mb(path: Path) -> float:
    """Best-effort recursive directory size in megabytes."""
    if not path.exists():
        return 0.0

    total_bytes = 0
    try:
        for entry in path.rglob("*"):
            if entry.is_file():
                total_bytes += entry.stat().st_size
    except Exception:
        return 0.0

    return round(total_bytes / (1024 * 1024), 1)


def _parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


def _refresh_services(force: bool = False) -> None:
    """Refresh dependency reachability with optional throttling."""
    now = datetime.now()
    services = app_state.setdefault("services", {})

    for service_name, service_url in SERVICE_CHECKS:
        existing = services.get(service_name) or {}
        should_check = force

        if not should_check:
            last_check = _parse_iso_datetime(existing.get("last_check"))
            if last_check is None:
                should_check = True
            else:
                age = (now - last_check).total_seconds()
                should_check = age >= HEALTH_REFRESH_INTERVAL_SECONDS

        if not should_check:
            continue

        is_available, error = verify_service(service_name, service_url)
        services[service_name] = {
            "available": is_available,
            "url": service_url,
            "last_check": now.isoformat(),
            "error": error if not is_available else None,
        }


# ============================================================================
# ROUTES
# ============================================================================


@app.get("/")
async def root() -> dict[str, Any]:
    """Root endpoint with version info."""
    uptime = (
        (datetime.now() - app_state["startup_time"]).total_seconds()
        if app_state["startup_time"]
        else 0
    )
    return {
        "service": "gen-engine",
        "version": "0.1.0",
        "status": "operational",
        "uptime_seconds": uptime,
    }


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Detailed health check endpoint for Kubernetes probes."""
    _refresh_services(force=False)

    services_status = {}

    # Check service status but don't fail if they're unavailable
    # (gen-engine can degrade gracefully)
    for service_name, service_info in app_state["services"].items():
        last_check = service_info.get("last_check")
        age_seconds = None
        parsed_check = _parse_iso_datetime(last_check)
        if parsed_check is not None:
            age_seconds = round(max(0.0, (datetime.now() - parsed_check).total_seconds()), 2)

        services_status[service_name] = {
            "status": "up" if service_info["available"] else "down",
            "error": service_info["error"],
            "last_check": last_check,
            "checked_seconds_ago": age_seconds,
        }

    ollama_reachable = bool(app_state["services"].get("Ollama", {}).get("available", False))
    kokoro_reachable = bool(app_state["services"].get("Kokoro TTS", {}).get("available", False))
    llm_provider_info = app_state.get("llm_provider", {"name": "unknown", "healthy": False})
    groq_reachable = (
        llm_provider_info.get("name") == "groq" and bool(llm_provider_info.get("healthy"))
    )

    disk = shutil.disk_usage("/")
    disk_space_gb = round(disk.free / (1024**3), 1)
    cache_size_mb = _directory_size_mb(Path(__file__).parent / "cache")
    overall_status = "healthy" if bool(llm_provider_info.get("healthy")) else "degraded"

    # Always return 200 OK as long as gen-engine app itself is running
    # External service failures don't make the app unhealthy
    return HealthResponse(
        status=overall_status,
        timestamp=datetime.now().isoformat(),
        groq_reachable=groq_reachable,
        ollama_reachable=ollama_reachable,
        kokoro_reachable=kokoro_reachable,
        llm_provider=llm_provider_info,
        disk_space_gb=disk_space_gb,
        cache_size_mb=cache_size_mb,
        services=services_status,
        cache={
            "entries": len(app_state["cache"]),
            "max_size": CONFIG["CACHE_MAX_SIZE"],
        },
        prompts={
            "loaded": len(app_state.get("prompts", {})),
            "required": len(REQUIRED_PROMPTS),
            "missing_required": app_state.get("prompt_health", {}).get("missing_required", []),
        },
    )


@app.get("/metrics")
async def metrics() -> Response:
    """Prometheus metrics endpoint."""
    if not PROMETHEUS_AVAILABLE:
        return JSONResponse(status_code=503, content={"error": "Prometheus metrics not available"})

    # Update cache size gauge (prefetch cache is the active generation cache).
    try:
        with prefetch_manager._lock:  # noqa: SLF001 - intentional lightweight instrumentation
            CACHE_SIZE.set(len(prefetch_manager._cache))
    except Exception:
        CACHE_SIZE.set(len(app_state["cache"]))

    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


# Include routers
app.include_router(generate_router, prefix="/api", tags=["generation"])
app.include_router(health_router, tags=["health"])

# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        # Pass the in-process app object directly so `python main.py` does not
        # import this module a second time and double-register Prometheus metrics.
        app,
        host="0.0.0.0",
        port=8001,
        reload=False,
        log_level=CONFIG["LOG_LEVEL"].lower(),
    )
