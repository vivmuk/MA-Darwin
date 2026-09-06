"""Filesystem + SQLite run storage.

Artifacts live at runs/{run_id}/round_{n}/ and are never overwritten.
Each round is an immutable snapshot.
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from ma_darwin.config_loader import RUNS_DIR
from ma_darwin.models.brief import Brief
from ma_darwin.models.run import Round, Run, RunStatus
from ma_darwin.storage.db import connect, init_db

_RUN_ID_RE = re.compile(r"^run_[0-9a-f]{12}$")


class RoundExistsError(FileExistsError):
    """Raised when attempting to write into an existing round directory."""


class RunStore:
    def __init__(self, root: Path | None = None, db_path: Path | None = None) -> None:
        self.root = Path(root) if root is not None else RUNS_DIR
        self.root.mkdir(parents=True, exist_ok=True)
        self.db_path = Path(db_path) if db_path is not None else self.root / "ma_darwin.sqlite3"
        init_db(self.db_path)

    @staticmethod
    def new_run_id() -> str:
        return f"run_{uuid.uuid4().hex[:12]}"

    def run_dir(self, run_id: str) -> Path:
        self._validate_run_id(run_id)
        return self.root / run_id

    def round_dir(self, run_id: str, round_n: int) -> Path:
        if round_n < 1:
            raise ValueError("round_n must be >= 1")
        return self.run_dir(run_id) / f"round_{round_n}"

    def create_run(
        self,
        *,
        paper_id: str,
        brief: Brief,
        blueprint_id: str = "msl_physician_8",
        skill_version: str = "v1",
        run_id: str | None = None,
    ) -> Run:
        rid = run_id or self.new_run_id()
        self._validate_run_id(rid)
        run = Run(
            id=rid,
            paper_id=paper_id,
            brief=brief,
            blueprint_id=blueprint_id,
            skill_version=skill_version,
            status=RunStatus.CREATED,
        )
        path = self.run_dir(rid)
        if path.exists():
            raise FileExistsError(f"run directory already exists: {path}")
        path.mkdir(parents=True)
        (path / "run.json").write_text(run.model_dump_json(indent=2), encoding="utf-8")
        now = _iso(run.created_at)
        with connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO runs (
                    id, paper_id, blueprint_id, skill_version, status,
                    brief_json, best_round_n, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run.id,
                    run.paper_id,
                    run.blueprint_id,
                    run.skill_version,
                    run.status.value,
                    run.brief.model_dump_json(),
                    run.best_round_n,
                    now,
                    now,
                ),
            )
            conn.commit()
        return run

    def start_round(self, run_id: str, round_n: int) -> Path:
        """Create an immutable round directory. Fails if it already exists."""
        rdir = self.round_dir(run_id, round_n)
        if rdir.exists():
            raise RoundExistsError(
                f"round directory already exists (immutable): {rdir}"
            )
        rdir.mkdir(parents=True)
        meta = {
            "run_id": run_id,
            "round": round_n,
            "created_at": _iso(datetime.now(timezone.utc)),
        }
        (rdir / "round_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
        return rdir

    def write_artifact(
        self,
        run_id: str,
        round_n: int,
        relative_name: str,
        content: str | bytes,
        *,
        overwrite: bool = False,
    ) -> Path:
        """Write a file into a round directory. Overwrite is forbidden by default."""
        if Path(relative_name).is_absolute() or ".." in Path(relative_name).parts:
            raise ValueError(f"invalid artifact path: {relative_name}")
        rdir = self.round_dir(run_id, round_n)
        if not rdir.is_dir():
            raise FileNotFoundError(f"round directory missing: {rdir}")
        target = rdir / relative_name
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and not overwrite:
            raise RoundExistsError(f"artifact already exists (immutable): {target}")
        if isinstance(content, bytes):
            target.write_bytes(content)
        else:
            target.write_text(content, encoding="utf-8")
        return target

    def save_round(self, run_id: str, round_obj: Round) -> Path:
        """Persist round metadata into DB and round_meta snapshot (no overwrite of prior rounds)."""
        rdir = self.round_dir(run_id, round_obj.n)
        if not rdir.is_dir():
            rdir = self.start_round(run_id, round_obj.n)
        payload = round_obj.model_dump_json(indent=2)
        snapshot = rdir / "round.json"
        if snapshot.exists():
            raise RoundExistsError(f"round snapshot already exists: {snapshot}")
        snapshot.write_text(payload, encoding="utf-8")
        with connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO rounds (run_id, n, payload_json, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (run_id, round_obj.n, payload, _iso(round_obj.created_at)),
            )
            conn.execute(
                "UPDATE runs SET updated_at = ? WHERE id = ?",
                (_iso(datetime.now(timezone.utc)), run_id),
            )
            conn.commit()
        self._refresh_run_json(run_id)
        return snapshot

    def update_status(
        self,
        run_id: str,
        status: RunStatus,
        *,
        best_round_n: Optional[int] = None,
    ) -> Run:
        run = self.get_run(run_id)
        run.status = status
        run.updated_at = datetime.now(timezone.utc)
        if best_round_n is not None:
            run.best_round_n = best_round_n
        with connect(self.db_path) as conn:
            conn.execute(
                """
                UPDATE runs
                SET status = ?, best_round_n = ?, updated_at = ?
                WHERE id = ?
                """,
                (run.status.value, run.best_round_n, _iso(run.updated_at), run_id),
            )
            conn.commit()
        self._write_run_json(run)
        return run

    def get_run(self, run_id: str) -> Run:
        with connect(self.db_path) as conn:
            row = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
            if row is None:
                raise KeyError(run_id)
            round_rows = conn.execute(
                "SELECT payload_json FROM rounds WHERE run_id = ? ORDER BY n ASC",
                (run_id,),
            ).fetchall()
        rounds = [Round.model_validate_json(r["payload_json"]) for r in round_rows]
        return Run(
            id=row["id"],
            paper_id=row["paper_id"],
            brief=Brief.model_validate_json(row["brief_json"]),
            blueprint_id=row["blueprint_id"],
            skill_version=row["skill_version"],
            rounds=rounds,
            status=RunStatus(row["status"]),
            best_round_n=row["best_round_n"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    def list_runs(self) -> list[str]:
        with connect(self.db_path) as conn:
            rows = conn.execute("SELECT id FROM runs ORDER BY created_at ASC").fetchall()
        return [r["id"] for r in rows]

    def _refresh_run_json(self, run_id: str) -> None:
        self._write_run_json(self.get_run(run_id))

    def _write_run_json(self, run: Run) -> None:
        path = self.run_dir(run.id) / "run.json"
        path.write_text(run.model_dump_json(indent=2), encoding="utf-8")

    @staticmethod
    def _validate_run_id(run_id: str) -> None:
        if not _RUN_ID_RE.match(run_id):
            raise ValueError(f"invalid run_id format: {run_id}")


def _iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()
