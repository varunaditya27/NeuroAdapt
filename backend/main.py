from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.db import ensure_schema
from backend.routers.action import router as action_router
from backend.routers.feedback import router as feedback_router
from backend.routers.health import router as health_router
from backend.routers.session import router as session_router
from backend.routers.lessons import router as lessons_router
from backend.routers.preferences import router as preferences_router
from backend.routers.state import router as state_router
from backend.routers.state_history import router as state_history_router
from backend.routers.analytics import router as analytics_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="NeuroAdapt Backend",
        version="0.1.0",
        description="FastAPI service for NeuroAdapt state/action/feedback orchestration.",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router)
    app.include_router(session_router)
    app.include_router(lessons_router)
    app.include_router(preferences_router)
    app.include_router(state_router)
    app.include_router(state_history_router)
    app.include_router(action_router)
    app.include_router(feedback_router)
    app.include_router(analytics_router)

    @app.on_event("startup")
    async def _startup() -> None:
        try:
            await ensure_schema()
        except Exception:
            # Demo mode can still serve state/action from memory if Postgres is
            # temporarily unavailable during local startup.
            pass

    return app


app = create_app()
