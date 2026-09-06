"""FastAPI application factory (PRD §9 / Prompt 6)."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.llm_env import ensure_dotenv
from app.paths import RUNS_DIR
from app.rendering.font_check import check_required_fonts
from app.storage.run_store import RunStore

ensure_dotenv()


def _runs_root() -> Path:
    override = os.environ.get("MA_DARWIN_RUNS_DIR")
    return Path(override) if override else RUNS_DIR


def create_app(*, store: RunStore | None = None, check_fonts: bool = True) -> FastAPI:
    """Build the MA-Darwin API. ``store`` is injected by tests."""

    @asynccontextmanager
    async def _lifespan(app: FastAPI):
        if check_fonts:
            try:
                check_required_fonts()
            except RuntimeError:
                if os.environ.get("MA_DARWIN_RELAX_FONTS") != "1":
                    raise
        app.state.store = store or RunStore(root=_runs_root())
        from app import orchestrator

        orchestrator.set_store(app.state.store)
        yield

    application = FastAPI(title="MA-Darwin API", version="0.1.0", lifespan=_lifespan)
    origins = [o.strip() for o in os.environ.get("CORS_ORIGINS", "*").split(",") if o.strip()]
    application.add_middleware(
        CORSMiddleware,
        allow_origins=origins or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(router)
    application.include_router(router, prefix="/api")
    if store is not None:
        application.state.store = store
    return application


app = create_app()
