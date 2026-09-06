"""Promote candidate / always-scoped rules into the skill (PRD §7.10)."""

from __future__ import annotations

from pathlib import Path

from app.models.run import MutationRecord, PromotionResult, RoutedFeedback
from app.models.skill import CandidateRule, SkillRule


def is_measurable_rule(text: str) -> bool:
    """Return True iff rule text contains a testable / measurable condition."""
    raise NotImplementedError


def validate_rule_text(text: str) -> None:
    """Reject vague rule text with a clear error message.

    Raises
    ------
    ValueError
        If the rule has no measurable condition.
    """
    raise NotImplementedError


def promote_rule(
    feedback: RoutedFeedback,
    *,
    skill_dir: Path | str,
    candidates: list[CandidateRule],
    promotion_threshold: int,
    max_mutations_per_round: int,
    mutations_so_far: list[MutationRecord],
) -> PromotionResult:
    """Attempt promotion into ``style_rules.md``.

    Promote when ``scope == always`` or a candidate's counter reaches
    ``promotion_threshold`` across different decks. ``house_rules.md`` is
    never edited here.
    """
    raise NotImplementedError


def apply_promotions(
    routed: list[RoutedFeedback],
    *,
    skill_dir: Path | str,
    candidates_path: Path | str,
    defaults_config: Path | str | None = None,
) -> list[PromotionResult]:
    """Apply all eligible promotions for a round, respecting mutation caps."""
    raise NotImplementedError


def write_skill_rule(rule: SkillRule, skill_dir: Path | str) -> Path:
    """Append a promoted rule to ``style_rules.md`` and return the path touched."""
    raise NotImplementedError
