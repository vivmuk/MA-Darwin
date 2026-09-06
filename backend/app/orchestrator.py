"""Round orchestrator — generate → render → gates → stop/auto-reiterate (Prompt 6)."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from app.models.run import ProgressEvent, Round, Run, StoppingDecision


def run_round(run_id: str, *, round_n: int | None = None) -> Round:
    """Execute one full round: generate → render → gate1 → gate2 → gate3.

    Gates run in order. A failed Gate 1 or Gate 2 short-circuits and does not
    call the vision judge. Always retain the best-scoring deck so far.

    Parameters
    ----------
    run_id:
        Existing run identifier.
    round_n:
        Explicit round number; defaults to ``len(rounds) + 1``.

    Returns
    -------
    Round
        Persisted round snapshot including gate artifacts.
    """
    raise NotImplementedError


def should_auto_reiterate(
    run: Run,
    round_obj: Round,
    *,
    judge_threshold: float | None = None,
    max_auto_rounds: int | None = None,
) -> bool:
    """True when Gate 3 is below threshold and auto-round budget remains."""
    raise NotImplementedError


def check_stopping_conditions(
    run: Run,
    *,
    defaults_config: Path | str | None = None,
) -> StoppingDecision:
    """Evaluate PRD §10 stopping conditions (success, max rounds, budget, plateau)."""
    raise NotImplementedError


def start_run(run_id: str) -> Round:
    """Kick off round 1 for a run (API ``POST /runs/{id}/start``)."""
    raise NotImplementedError


def reiterate(run_id: str) -> Round:
    """Start the next round after human review (API ``POST /runs/{id}/reiterate``)."""
    raise NotImplementedError


def iter_progress_events(run_id: str) -> Iterator[ProgressEvent]:
    """Yield real progress milestones for the SSE ``/runs/{id}/events`` stream."""
    raise NotImplementedError


def parse_brief(run_id: str, brief_text: str | None = None) -> Run:
    """Parse freeform brief into structured fields for user confirmation."""
    raise NotImplementedError
