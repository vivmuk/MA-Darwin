"""Regression-set gate before committing skill promotions (PRD §7.10)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from app.config import get_threshold
from app.models.run import RegressionReport
from app.models.skill import SkillRule
from app.paths import BACKEND_DIR, REPO_ROOT, SKILLS_DIR

# No flag may skip this gate. Missing scores fail closed (treat after as 0).
_DEFAULT_REGRESSION_DIRS = (
    BACKEND_DIR / "tests" / "regression",
    REPO_ROOT / "tests" / "regression",
)


def default_regression_dir() -> Path:
    for path in _DEFAULT_REGRESSION_DIRS:
        if path.is_dir():
            return path
    return _DEFAULT_REGRESSION_DIRS[0]


def load_regression_set(regression_dir: Path | str) -> list[Path]:
    """List fixed papers / gold decks under ``tests/regression/`` (5–8 items)."""
    root = Path(regression_dir)
    if not root.is_dir():
        raise FileNotFoundError(f"regression set not found: {root}")
    items = sorted(p for p in root.iterdir() if p.is_dir() and not p.name.startswith("."))
    if not items:
        items = sorted(p for p in root.glob("*.json") if p.name != "manifest.json")
    return items


def _read_score(item: Path, *names: str) -> float | None:
    candidates = [item] if item.is_file() and item.suffix == ".json" else [item / n for n in names]
    for path in candidates:
        if not path.is_file():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and "deck_score" in data:
            return float(data["deck_score"])
    return None


def _regenerate_item(item: Path, skill_dir: Path) -> float:
    """Regenerate one regression deck score.

    Real generation is owned by another module; this gate reads the score
    artifact that regeneration must leave behind (``current.json``). If that
    artifact is missing, score is 0 — fail closed, never skip.
    """
    _ = skill_dir
    current = _read_score(item, "current.json", "after_score.json", "regenerated.json")
    if current is None:
        return 0.0
    return current


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
    skill = Path(skill_dir)
    items = load_regression_set(regression_dir)
    befores: list[float] = []
    afters: list[float] = []
    for item in items:
        before = _read_score(item, "baseline.json", "gold_score.json", "score.json")
        if before is None:
            before = 0.0
        after = _regenerate_item(item, skill)
        befores.append(before)
        afters.append(after)
    n = len(items)
    mean_before = sum(befores) / n if n else 0.0
    mean_after = sum(afters) / n if n else 0.0
    delta = mean_after - mean_before
    # Empty set cannot prove safety — fail closed.
    passed = n > 0 and delta >= -abs(tolerance)
    return RegressionReport(
        passed=passed,
        mean_score_before=round(mean_before, 4),
        mean_score_after=round(mean_after, 4),
        delta=round(delta, 4),
        tolerance=float(tolerance),
        decks_evaluated=n,
    )


def _append_changelog(skill_dir: Path, text: str) -> None:
    path = skill_dir / "CHANGELOG.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = path.read_text(encoding="utf-8") if path.is_file() else "# Changelog\n"
    if not existing.endswith("\n"):
        existing += "\n"
    path.write_text(existing + text, encoding="utf-8")


def guard_promotion(
    rule: SkillRule,
    *,
    skill_dir: Path | str,
    regression_dir: Path | str | None = None,
    tolerance: float | None = None,
) -> RegressionReport:
    """Run regression before committing ``rule``; reject and log on failure."""
    skill = Path(skill_dir)
    regen_dir = Path(regression_dir) if regression_dir is not None else default_regression_dir()
    tol = float(tolerance if tolerance is not None else get_threshold("regression_tolerance", 2))
    report = evaluate_regression(skill_dir=skill, regression_dir=regen_dir, tolerance=tol)
    if not report.passed:
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        _append_changelog(
            skill,
            (
                f"\n## Rejected {stamp}\n\n"
                f"- Rule `{rule.id}`: `{rule.text}`\n"
                f"- Regression rejected: delta {report.delta} "
                f"(tolerance {report.tolerance}); "
                f"before {report.mean_score_before} → after {report.mean_score_after}; "
                f"decks={report.decks_evaluated}\n"
            ),
        )
    return report


def activate_skill_version(version: str, *, skills_root: Path | str | None = None) -> Path:
    """Make a prior skill version active (rollback) in one call."""
    root = Path(skills_root) if skills_root is not None else SKILLS_DIR
    dest = root / version
    if not dest.is_dir():
        raise FileNotFoundError(f"skill version not found: {dest}")
    (root / "ACTIVE").write_text(version.strip() + "\n", encoding="utf-8")
    return dest
