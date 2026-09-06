"""End-to-end tests for run storage — immutable round directories."""

from __future__ import annotations

from pathlib import Path

import pytest

from ma_darwin.models import Brief, Round, RunStatus
from ma_darwin.storage import RoundExistsError, RunStore


@pytest.fixture
def store(tmp_path: Path) -> RunStore:
    return RunStore(root=tmp_path / "runs", db_path=tmp_path / "runs" / "test.sqlite3")


def test_create_run_makes_directory_and_db_row(store: RunStore) -> None:
    run = store.create_run(paper_id="paper-abc", brief=Brief(notes="MSL deck"))
    assert run.id.startswith("run_")
    run_dir = store.run_dir(run.id)
    assert run_dir.is_dir()
    assert (run_dir / "run.json").is_file()
    loaded = store.get_run(run.id)
    assert loaded.paper_id == "paper-abc"
    assert loaded.status == RunStatus.CREATED
    assert store.list_runs() == [run.id]


def test_start_round_creates_immutable_snapshot_dir(store: RunStore) -> None:
    run = store.create_run(paper_id="paper-1", brief=Brief())
    rdir = store.start_round(run.id, 1)
    assert rdir.name == "round_1"
    assert (rdir / "round_meta.json").is_file()
    with pytest.raises(RoundExistsError):
        store.start_round(run.id, 1)


def test_write_artifact_refuses_overwrite(store: RunStore) -> None:
    run = store.create_run(paper_id="paper-1", brief=Brief())
    store.start_round(run.id, 1)
    store.write_artifact(run.id, 1, "gate1.json", '{"passed": true}')
    with pytest.raises(RoundExistsError):
        store.write_artifact(run.id, 1, "gate1.json", '{"passed": false}')


def test_save_round_persists_and_refuses_duplicate(store: RunStore) -> None:
    run = store.create_run(paper_id="paper-1", brief=Brief())
    store.start_round(run.id, 1)
    store.save_round(run.id, Round(n=1, locked_slides=[1]))
    loaded = store.get_run(run.id)
    assert len(loaded.rounds) == 1
    assert loaded.rounds[0].locked_slides == [1]
    with pytest.raises(RoundExistsError):
        store.save_round(run.id, Round(n=1, locked_slides=[2]))


def test_update_status_and_best_round(store: RunStore) -> None:
    run = store.create_run(paper_id="paper-1", brief=Brief())
    store.start_round(run.id, 1)
    store.save_round(run.id, Round(n=1))
    updated = store.update_status(run.id, RunStatus.AWAITING_HUMAN, best_round_n=1)
    assert updated.status == RunStatus.AWAITING_HUMAN
    assert updated.best_round_n == 1


def test_round_two_does_not_touch_round_one_artifacts(store: RunStore) -> None:
    run = store.create_run(paper_id="paper-1", brief=Brief())
    store.start_round(run.id, 1)
    store.write_artifact(run.id, 1, "deck.pptx", b"round1")
    store.save_round(run.id, Round(n=1))
    store.start_round(run.id, 2)
    store.write_artifact(run.id, 2, "deck.pptx", b"round2")
    store.save_round(run.id, Round(n=2))
    r1 = store.round_dir(run.id, 1) / "deck.pptx"
    r2 = store.round_dir(run.id, 2) / "deck.pptx"
    assert r1.read_bytes() == b"round1"
    assert r2.read_bytes() == b"round2"


def test_invalid_run_id_rejected(store: RunStore) -> None:
    with pytest.raises(ValueError):
        store.create_run(
            paper_id="p",
            brief=Brief(),
            run_id="../evil",
        )
