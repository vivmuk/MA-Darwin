"""Route human comments into one-off / candidate / promote tiers (PRD §7.10)."""

from __future__ import annotations

from pathlib import Path

from app.models.run import RoutedFeedback
from app.models.skill import CandidateRule
from app.models.slide import HumanComment


def route_comment(
    comment: HumanComment,
    *,
    run_id: str,
    round_n: int,
    existing_candidates: list[CandidateRule] | None = None,
) -> RoutedFeedback:
    """Sort one human comment into a feedback tier.

    - ``scope == this-deck-only`` → one-off fix (never written to a skill file)
    - ``scope == always`` → immediate promotion candidate
    - inferred pattern → candidate rule with occurrence evidence
    """
    raise NotImplementedError


def route_comments(
    comments: list[HumanComment],
    *,
    run_id: str,
    round_n: int,
    candidates_path: Path | str | None = None,
) -> list[RoutedFeedback]:
    """Route all comments for a round; update ``candidates.json`` as needed."""
    raise NotImplementedError


def load_candidates(path: Path | str) -> list[CandidateRule]:
    """Load candidate rules from ``candidates.json``."""
    raise NotImplementedError


def save_candidates(path: Path | str, candidates: list[CandidateRule]) -> None:
    """Persist candidate rules to ``candidates.json``."""
    raise NotImplementedError
