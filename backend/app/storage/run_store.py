"""Filesystem + SQLite run storage.

Artifacts live at runs/{run_id}/round_{n}/ and are never overwritten.
SQLite holds run metadata only; files live on disk.
"""

from __future__ import annotations

import json
import re
import shutil
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from app.models.run import Brief, Round, Run, RunStatus
from app.paths import REPO_ROOT, RUNS_DIR

_RUN_ID_RE = re.compile(r"^run_[0-9a-f]{12}$")


class RoundExistsError(FileExistsError):
    """Raised when attempting to write into an existing round directory."""


def _iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def _connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Path) -> None:
    with _connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS runs (
                id TEXT PRIMARY KEY,
                paper_id TEXT NOT NULL,
                blueprint_id TEXT NOT NULL,
                skill_version TEXT NOT NULL,
                status TEXT NOT NULL,
                brief_json TEXT NOT NULL,
                brief_text TEXT NOT NULL DEFAULT '',
                best_round_n INTEGER,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.commit()


class RunStore:
    """Create and load runs; persist round artifacts immutably on disk."""

    def __init__(self, root: Path | None = None, db_path: Path | None = None) -> None:
        self.root = Path(root) if root is not None else RUNS_DIR
        self.root.mkdir(parents=True, exist_ok=True)
        self.db_path = Path(db_path) if db_path is not None else self.root / "ma_darwin.sqlite3"
        init_db(self.db_path)

    @staticmethod
    def new_run_id() -> str:
        return f"run_{uuid.uuid4().hex[:12]}"

    def _validate_run_id(self, run_id: str) -> None:
        if not _RUN_ID_RE.match(run_id):
            raise ValueError(f"invalid run_id: {run_id!r}")

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
        paper_path: Path | str,
        brief: str | Brief,
        blueprint_id: str = "msl_physician_8",
        skill_version: str = "v1",
        run_id: str | None = None,
        paper_id: str | None = None,
    ) -> Run:
        """Create runs/{run_id}/ with manifest.json and SQLite metadata. No model calls."""
        paper = Path(paper_path)
        if not paper.is_file():
            raise FileNotFoundError(f"paper not found: {paper}")

        rid = run_id or self.new_run_id()
        self._validate_run_id(rid)
        pid = paper_id or paper.stem

        if isinstance(brief, Brief):
            brief_model = brief
            brief_text = brief.notes
        else:
            brief_text = brief
            brief_model = Brief(notes=brief_text)

        now = datetime.now(timezone.utc)
        run = Run(
            id=rid,
            paper_id=pid,
            brief=brief_model,
            brief_text=brief_text,
            blueprint_id=blueprint_id,
            skill_version=skill_version,
            status=RunStatus.CREATED,
            created_at=now,
            updated_at=now,
        )

        path = self.run_dir(rid)
        if path.exists():
            raise FileExistsError(f"run directory already exists: {path}")
        path.mkdir(parents=True)

        # Store a copy of the paper under the run directory for provenance.
        papers_dir = path / "paper"
        papers_dir.mkdir()
        dest_paper = papers_dir / paper.name
        shutil.copy2(paper, dest_paper)

        try:
            paper_rel = str(dest_paper.relative_to(REPO_ROOT))
        except ValueError:
            paper_rel = str(dest_paper)

        manifest = {
            "id": run.id,
            "paper_id": run.paper_id,
            "paper_path": paper_rel,
            "source_paper": str(paper.resolve()),
            "brief": brief_text,
            "brief_parsed": run.brief.model_dump(mode="json"),
            "blueprint_id": run.blueprint_id,
            "skill_version": run.skill_version,
            "status": run.status.value,
            "rounds": [],
            "created_at": _iso(run.created_at),
            "updated_at": _iso(run.updated_at),
        }
        (path / "manifest.json").write_text(
            json.dumps(manifest, indent=2) + "\n",
            encoding="utf-8",
        )
        (path / "run.json").write_text(run.model_dump_json(indent=2) + "\n", encoding="utf-8")

        with _connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO runs (
                    id, paper_id, blueprint_id, skill_version, status,
                    brief_json, brief_text, best_round_n, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run.id,
                    run.paper_id,
                    run.blueprint_id,
                    run.skill_version,
                    run.status.value,
                    run.brief.model_dump_json(),
                    brief_text,
                    run.best_round_n,
                    _iso(run.created_at),
                    _iso(run.updated_at),
                ),
            )
            conn.commit()

        return run

    def get_run(self, run_id: str) -> Run:
        """Load a run from disk (run.json), falling back to SQLite + manifest."""
        self._validate_run_id(run_id)
        run_json = self.run_dir(run_id) / "run.json"
        if run_json.is_file():
            return Run.model_validate_json(run_json.read_text(encoding="utf-8"))

        with _connect(self.db_path) as conn:
            row = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
        if row is None:
            raise KeyError(f"run not found: {run_id}")

        brief = Brief.model_validate_json(row["brief_json"])
        rounds = self._load_all_rounds(run_id)
        return Run(
            id=row["id"],
            paper_id=row["paper_id"],
            brief=brief,
            brief_text=row["brief_text"] or "",
            blueprint_id=row["blueprint_id"],
            skill_version=row["skill_version"],
            rounds=rounds,
            status=RunStatus(row["status"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            best_round_n=row["best_round_n"],
        )

    def save_round_artifact(
        self,
        run_id: str,
        round_n: int,
        name: str,
        data: Any,
        *,
        binary: bytes | None = None,
    ) -> Path:
        """Write an artifact into runs/{run_id}/round_{n}/.

        Round directories are immutable once created with a round.json snapshot:
        creating the same round again raises RoundExistsError. Additional
        artifacts may be written into an existing round directory.
        """
        self._validate_run_id(run_id)
        if "/" in name or "\\" in name or name in (".", ".."):
            raise ValueError(f"invalid artifact name: {name!r}")

        rdir = self.round_dir(run_id, round_n)
        rdir.mkdir(parents=True, exist_ok=True)

        if binary is not None:
            out = rdir / name
            if out.exists():
                raise FileExistsError(f"artifact already exists: {out}")
            out.write_bytes(binary)
            return out

        if isinstance(data, (dict, list)):
            payload = json.dumps(data, indent=2) + "\n"
            out = rdir / (name if name.endswith(".json") else f"{name}.json")
        elif isinstance(data, str):
            payload = data if data.endswith("\n") else data + "\n"
            out = rdir / name
        else:
            # Pydantic models and similar
            if hasattr(data, "model_dump_json"):
                payload = data.model_dump_json(indent=2) + "\n"
                out = rdir / (name if name.endswith(".json") else f"{name}.json")
            else:
                payload = json.dumps(data, indent=2, default=str) + "\n"
                out = rdir / (name if name.endswith(".json") else f"{name}.json")

        if out.exists():
            raise FileExistsError(f"artifact already exists: {out}")
        out.write_text(payload, encoding="utf-8")
        return out

    def save_round(self, run_id: str, round_obj: Round) -> Path:
        """Persist a Round snapshot. Fails if round_{n}/round.json already exists."""
        rdir = self.round_dir(run_id, round_obj.n)
        round_json = rdir / "round.json"
        if round_json.exists():
            raise RoundExistsError(f"round already saved: {round_json}")
        rdir.mkdir(parents=True, exist_ok=True)
        round_json.write_text(round_obj.model_dump_json(indent=2) + "\n", encoding="utf-8")

        run = self.get_run(run_id)
        # Replace same-n if present (shouldn't happen) else append.
        run.rounds = [r for r in run.rounds if r.n != round_obj.n] + [round_obj]
        run.rounds.sort(key=lambda r: r.n)
        run.updated_at = datetime.now(timezone.utc)
        self._persist_run(run)
        return round_json

    def load_round(self, run_id: str, round_n: int) -> Round:
        """Load round_{n}/round.json for a run."""
        round_json = self.round_dir(run_id, round_n) / "round.json"
        if not round_json.is_file():
            raise FileNotFoundError(f"round not found: {round_json}")
        return Round.model_validate_json(round_json.read_text(encoding="utf-8"))

    def _load_all_rounds(self, run_id: str) -> list[Round]:
        path = self.run_dir(run_id)
        if not path.is_dir():
            return []
        rounds: list[Round] = []
        for child in sorted(path.glob("round_*")):
            rj = child / "round.json"
            if rj.is_file():
                rounds.append(Round.model_validate_json(rj.read_text(encoding="utf-8")))
        return rounds

    def _persist_run(self, run: Run) -> None:
        path = self.run_dir(run.id)
        path.mkdir(parents=True, exist_ok=True)
        (path / "run.json").write_text(run.model_dump_json(indent=2) + "\n", encoding="utf-8")

        manifest_path = path / "manifest.json"
        if manifest_path.is_file():
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        else:
            manifest = {"id": run.id}
        manifest.update(
            {
                "status": run.status.value,
                "rounds": [r.n for r in run.rounds],
                "updated_at": _iso(run.updated_at),
                "best_round_n": run.best_round_n,
            }
        )
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

        with _connect(self.db_path) as conn:
            conn.execute(
                """
                UPDATE runs SET
                    status = ?, brief_json = ?, brief_text = ?,
                    best_round_n = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    run.status.value,
                    run.brief.model_dump_json(),
                    run.brief_text,
                    run.best_round_n,
                    _iso(run.updated_at),
                    run.id,
                ),
            )
            conn.commit()


# Module-level helpers matching the deliverable API surface.
_default_store: Optional[RunStore] = None


def _store() -> RunStore:
    global _default_store
    if _default_store is None:
        _default_store = RunStore()
    return _default_store


def create_run(*, paper_path: Path | str, brief: str, **kwargs: Any) -> Run:
    return _store().create_run(paper_path=paper_path, brief=brief, **kwargs)


def get_run(run_id: str) -> Run:
    return _store().get_run(run_id)


def save_round_artifact(
    run_id: str,
    round_n: int,
    name: str,
    data: Any,
    *,
    binary: bytes | None = None,
) -> Path:
    return _store().save_round_artifact(run_id, round_n, name, data, binary=binary)


def load_round(run_id: str, round_n: int) -> Round:
    return _store().load_round(run_id, round_n)
