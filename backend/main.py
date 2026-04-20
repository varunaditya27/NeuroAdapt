from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routers.action import router as action_router
from backend.routers.feedback import router as feedback_router
from backend.routers.health import router as health_router
from backend.routers.state import router as state_router


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
    app.include_router(state_router)
    app.include_router(action_router)
    app.include_router(feedback_router)

    return app


app = create_app()
