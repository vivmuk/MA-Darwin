"""FastAPI application entrypoint (Phase 6 expands routes)."""

from __future__ import annotations

from fastapi import FastAPI

from ma_darwin import __version__

app = FastAPI(title="MA-Darwin", version=__version__)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__}
