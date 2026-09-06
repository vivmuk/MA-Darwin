"""Serve the exported Next.js UI from FastAPI when a build is present."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse

from app.paths import BACKEND_DIR, REPO_ROOT


def frontend_dir() -> Path | None:
    raw = os.environ.get("MA_DARWIN_FRONTEND_DIR", "").strip()
    candidates: list[Path] = []
    if raw:
        candidates.append(Path(raw))
    candidates.extend(
        (
            REPO_ROOT / "frontend" / "out",
            BACKEND_DIR / "web",
        )
    )
    for path in candidates:
        if (path / "index.html").is_file():
            return path
    return None


def mount_frontend(application: FastAPI, root: Path | None = None) -> bool:
    """Mount static UI routes. Returns True when a frontend build was found."""

    directory = root or frontend_dir()
    if directory is None:
        return False

    next_assets = directory / "_next"
    if next_assets.is_dir():
        application.mount("/_next", StaticFiles(directory=next_assets), name="next-static")

    for child in sorted(directory.iterdir()):
        if child.is_dir() and child.name != "_next":
            application.mount(
                f"/{child.name}",
                StaticFiles(directory=child, html=True),
                name=f"frontend-{child.name}",
            )

    index = directory / "index.html"

    @application.get("/", include_in_schema=False)
    def frontend_index() -> FileResponse:
        return FileResponse(index, media_type="text/html")

    @application.get("/{name}", include_in_schema=False)
    def frontend_root_file(name: str) -> FileResponse:
        if "/" in name or "\\" in name or name in {".", ".."}:
            raise HTTPException(status_code=404, detail="Not Found")
        direct = directory / name
        if direct.is_file():
            return FileResponse(direct)
        html = directory / f"{name}.html"
        if html.is_file():
            return FileResponse(html, media_type="text/html")
        raise HTTPException(status_code=404, detail="Not Found")

    return True
