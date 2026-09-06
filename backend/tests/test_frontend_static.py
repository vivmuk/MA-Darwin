"""FastAPI serves the exported Next.js UI without hiding API routes."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.app import create_app
from app.paths import REPO_ROOT
from app.storage.run_store import RunStore


def _client(tmp_path: Path, frontend: Path | None, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    store = RunStore(root=tmp_path / "runs", db_path=tmp_path / "t.sqlite3")
    monkeypatch.setattr("app.api.frontend_static.frontend_dir", lambda: frontend)
    return TestClient(create_app(store=store, check_fonts=False))


def test_root_is_404_without_frontend(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    with _client(tmp_path, None, monkeypatch) as client:
        assert client.get("/").status_code == 404
        assert client.get("/health").json() == {"status": "ok"}


def test_root_serves_exported_ui(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    out = tmp_path / "web"
    out.mkdir()
    (out / "index.html").write_text("<html><body>MA·Darwin</body></html>", encoding="utf-8")
    (out / "app").mkdir()
    (out / "app" / "index.html").write_text("<html><body>Demo</body></html>", encoding="utf-8")
    (out / "_next").mkdir()
    (out / "_next" / "chunk.js").write_text("console.log(1)", encoding="utf-8")
    (out / "favicon.ico").write_bytes(b"ico")

    with _client(tmp_path, out, monkeypatch) as client:
        home = client.get("/")
        assert home.status_code == 200
        assert "MA·Darwin" in home.text
        assert "text/html" in home.headers["content-type"]

        demo = client.get("/app/")
        assert demo.status_code == 200
        assert "Demo" in demo.text

        assert client.get("/_next/chunk.js").status_code == 200
        assert client.get("/favicon.ico").status_code == 200
        assert client.get("/health").json() == {"status": "ok"}
        assert client.get("/api/health").json() == {"status": "ok"}
        assert client.get("/docs").status_code == 200


def test_zac_app_does_not_restore_missing_runs() -> None:
    script = (REPO_ROOT / "frontend" / "public" / "app" / "script.js").read_text(encoding="utf-8")
    assert "async function restoreLastDeck" in script
    assert "fetch(`/api/runs/${runId}`)" in script or 'fetch(`/api/runs/${runId}`)' in script
    assert "isMissingRun" in script
    assert "clearStoredDeck" in script
    assert "showView('upload')" in script
    boot = script.split("/* ---------- boot")[-1]
    assert "showView('upload')" in boot
    assert "restoreLastDeck()" in boot
