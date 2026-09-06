"""Gate 3 — vision judge (PRD §7.8 / Prompt 5)."""

from __future__ import annotations

from pathlib import Path

from app.models.blueprint import Blueprint
from app.models.gates import Gate3Result, JudgeCriterionScore, SlideJudgeResult
from app.models.rubric import Rubric


def load_rubric(rubric_path: Path | str | None = None) -> Rubric:
    """Load criterion weights and score-band anchors from ``config/rubric.yaml``.

    Anchors must never be inlined in the judge prompt file.
    """
    raise NotImplementedError


def build_contact_sheet(slide_images: list[Path | str], output_path: Path | str) -> Path:
    """Compose all slide PNGs into one contact-sheet image for deck-level criteria."""
    raise NotImplementedError


def judge_slide(
    image_path: Path | str,
    *,
    role: str,
    rubric: Rubric,
    prompt_path: Path | str | None = None,
) -> SlideJudgeResult:
    """Score one slide image against per-slide rubric criteria.

    Must receive no round number, previous scores, or generator reasoning.
    """
    raise NotImplementedError


def judge_deck_level(
    contact_sheet_path: Path | str,
    *,
    rubric: Rubric,
    prompt_path: Path | str | None = None,
) -> list[JudgeCriterionScore]:
    """Score deck-level criteria (consistency, executive feel) once on the contact sheet."""
    raise NotImplementedError


def median_criterion_scores(
    runs: list[list[JudgeCriterionScore]],
) -> list[JudgeCriterionScore]:
    """Reduce N judge runs to median score per criterion (temperature 0, N=3 default)."""
    raise NotImplementedError


def run_gate3(
    *,
    slide_images: list[Path | str],
    blueprint: Blueprint,
    rubric_path: Path | str | None = None,
    prompt_path: Path | str | None = None,
    judge_runs: int = 3,
    temperature: float = 0.0,
    threshold: float | None = None,
) -> Gate3Result:
    """Run the vision judge and produce ``gate3.json``.

    Criterion 6 may be N/A (weights renormalized). Criteria 8 and 10 are
    deck-level only. ``deck_score`` is the mean of slide scores; also report
    ``worst_slide_score``.

    Parameters
    ----------
    slide_images:
        Rendered PNGs (images, not XML).
    blueprint:
        Provides the role for each slide.
    rubric_path:
        Optional path to ``rubric.yaml``.
    prompt_path:
        Optional path to ``prompts/judge.md``.
    judge_runs:
        Number of blind runs at ``temperature`` (median taken).
    temperature:
        Must be 0 for v1.
    threshold:
        Pass threshold; defaults to ``judge_threshold`` from config.

    Returns
    -------
    Gate3Result
        Artifact suitable for ``gate3.json``.
    """
    raise NotImplementedError
