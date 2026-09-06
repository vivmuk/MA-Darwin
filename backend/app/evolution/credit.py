"""Rule credit counters and stale-candidate retirement (PRD §7.10)."""

from __future__ import annotations

from pathlib import Path

from app.models.gates import Gate3Result
from app.models.run import CreditUpdate
from app.models.skill import CandidateRule, SkillRule


def update_credits(
    active_rules: list[SkillRule],
    *,
    previous_gate3: Gate3Result | None,
    current_gate3: Gate3Result,
) -> list[CreditUpdate]:
    """Adjust credit for each active rule based on tagged criterion score delta.

    Improved → ``credit += 1``; dropped → ``credit -= 1``.
    """
    raise NotImplementedError


def rules_for_removal(
    active_rules: list[SkillRule],
    *,
    credit_removal_threshold: int = -3,
) -> list[SkillRule]:
    """Return rules at or below the removal credit threshold for UI surfacing."""
    raise NotImplementedError


def retire_stale_candidates(
    candidates: list[CandidateRule],
    *,
    decks_since: dict[str, int],
    stale_after_decks: int = 10,
) -> list[CandidateRule]:
    """Retire candidates with no reaffirmation within ``stale_after_decks`` decks."""
    raise NotImplementedError


def persist_credits(skill_dir: Path | str, rules: list[SkillRule]) -> None:
    """Persist updated credit counters alongside the skill version."""
    raise NotImplementedError
