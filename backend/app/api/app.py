"""FastAPI application factory (PRD §9 / Prompt 6)."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

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
            check_required_fonts()
        app.state.store = store or RunStore(root=_runs_root())
        from app import orchestrator

        orchestrator.set_store(app.state.store)
        yield

    application = FastAPI(title="MA-Darwin API", version="0.1.0", lifespan=_lifespan)
    application.include_router(router)
    if store is not None:
        application.state.store = store
    return application


app = create_app()
