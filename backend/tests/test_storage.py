"""Tests for run storage and CLI new-run."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.cli import main
from app.models.run import Round, RunStatus
from app.storage.run_store import RoundExistsError, RunStore


@pytest.fixture
def paper_pdf(tmp_path: Path) -> Path:
    pdf = tmp_path / "sample_paper.pdf"
    # Minimal PDF bytes — storage only copies the file; no parsing yet.
    pdf.write_bytes(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n")
    return pdf


@pytest.fixture
def store(tmp_path: Path) -> RunStore:
    return RunStore(root=tmp_path / "runs", db_path=tmp_path / "runs" / "test.sqlite3")


def test_create_run_writes_manifest(store: RunStore, paper_pdf: Path) -> None:
    run = store.create_run(
        paper_path=paper_pdf,
        brief="Create an 8 slide medical affairs MSL deck",
    )
    run_dir = store.run_dir(run.id)
    assert run_dir.is_dir()
    manifest_path = run_dir / "manifest.json"
    assert manifest_path.is_file()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["id"] == run.id
    assert manifest["status"] == RunStatus.CREATED.value
    assert "brief" in manifest
    assert (run_dir / "paper" / paper_pdf.name).is_file()


def test_get_run_roundtrip(store: RunStore, paper_pdf: Path) -> None:
    created = store.create_run(paper_path=paper_pdf, brief="brief text")
    loaded = store.get_run(created.id)
    assert loaded.id == created.id
    assert loaded.brief_text == "brief text"
    assert loaded.paper_id == paper_pdf.stem


def test_save_and_load_round(store: RunStore, paper_pdf: Path) -> None:
    run = store.create_run(paper_path=paper_pdf, brief="brief")
    rnd = Round(n=1, deck_path="deck.pptx", locked_slides=[])
    store.save_round(run.id, rnd)
    loaded = store.load_round(run.id, 1)
    assert loaded.n == 1
    assert loaded.deck_path == "deck.pptx"

    with pytest.raises(RoundExistsError):
        store.save_round(run.id, Round(n=1))


def test_save_round_artifact(store: RunStore, paper_pdf: Path) -> None:
    run = store.create_run(paper_path=paper_pdf, brief="brief")
    path = store.save_round_artifact(run.id, 1, "gate1", {"passed": True, "checks": []})
    assert path.name == "gate1.json"
    assert path.is_file()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["passed"] is True


def test_cli_new_run_creates_manifest(
    tmp_path: Path, paper_pdf: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    runs_dir = tmp_path / "runs"
    code = main(
        [
            "new-run",
            "--paper",
            str(paper_pdf),
            "--brief",
            "Create an 8 slide MSL deck for physicians",
            "--runs-dir",
            str(runs_dir),
        ]
    )
    assert code == 0
    out = capsys.readouterr().out.strip()
    assert out.startswith("run_")
    run_id = out.splitlines()[0]
    manifest = runs_dir / run_id / "manifest.json"
    assert manifest.is_file()
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    assert payload["id"] == run_id
