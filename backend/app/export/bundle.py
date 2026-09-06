"""Export bundle assembly (PRD §7.11 / Prompt 9)."""

from __future__ import annotations

from pathlib import Path

from app.models.run import ExportBundleResult, Run


def export_allowed(run: Run, *, round_n: int) -> tuple[bool, str]:
    """Return whether export is allowed and a human-readable blocker message.

    Allowed only when Gate 1 passes, Gate 2 passes, and every slide is locked.
    Enforced server-side.
    """
    raise NotImplementedError


def build_provenance_md(run: Run, *, round_n: int) -> str:
    """Build human-readable provenance covering every claim on every slide."""
    raise NotImplementedError


def build_run_log(run: Run) -> str:
    """Serialize every round, mutation, and human comment with timestamps."""
    raise NotImplementedError


def create_bundle(
    run_id: str,
    *,
    round_n: int | None = None,
    output_path: Path | str | None = None,
) -> ExportBundleResult:
    """Zip deck.pptx, deck.pdf, provenance.md, scores.json, skill_version.txt, run_log.json.

    Raises
    ------
    PermissionError
        If export preconditions are not met.
    """
    raise NotImplementedError
