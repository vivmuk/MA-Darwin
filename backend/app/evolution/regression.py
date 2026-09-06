"""Regression-set gate before committing skill promotions (PRD §7.10)."""

from __future__ import annotations

from pathlib import Path

from app.models.run import RegressionReport
from app.models.skill import SkillRule


def load_regression_set(regression_dir: Path | str) -> list[Path]:
    """List fixed papers / gold decks under ``tests/regression/`` (5–8 items)."""
    raise NotImplementedError


def evaluate_regression(
    *,
    skill_dir: Path | str,
    regression_dir: Path | str,
    tolerance: float,
) -> RegressionReport:
    """Regenerate the regression set and compare mean deck scores.

    If mean score drops by more than ``tolerance``, the promotion must be rejected.
    This gate is not optional and must not be bypassable by a flag.
    """
    raise NotImplementedError


def guard_promotion(
    rule: SkillRule,
    *,
    skill_dir: Path | str,
    regression_dir: Path | str | None = None,
    tolerance: float | None = None,
) -> RegressionReport:
    """Run regression before committing ``rule``; reject and log on failure."""
    raise NotImplementedError


def activate_skill_version(version: str, *, skills_root: Path | str | None = None) -> Path:
    """Make a prior skill version active (rollback) in one call."""
    raise NotImplementedError
