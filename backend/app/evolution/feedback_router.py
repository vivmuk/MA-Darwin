"""Route human comments into one-off / candidate / promote tiers (PRD §7.10)."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from app.models.run import FeedbackTier, RoutedFeedback
from app.models.skill import CandidateEvidence, CandidateRule
from app.models.slide import HumanComment, Scope

_WS = re.compile(r"\s+")


def _fingerprint(text: str) -> str:
    return _WS.sub(" ", text.strip().lower())


def unique_deck_ids(candidate: CandidateRule) -> set[str]:
    """Decks that produced this candidate — run/round of the same deck counts once."""
    decks: set[str] = set()
    for item in candidate.evidence:
        decks.add(item.deck_id or item.run_id)
    return decks


def route_comment(
    comment: HumanComment,
    *,
    run_id: str,
    round_n: int,
    existing_candidates: list[CandidateRule] | None = None,
    deck_id: str | None = None,
) -> RoutedFeedback:
    """Sort one human comment into a feedback tier."""
    if comment is None:
        raise TypeError("comment is required")
    deck = deck_id or run_id
    if comment.scope == Scope.THIS_DECK_ONLY:
        return RoutedFeedback(
            comment_id=comment.id,
            tier=FeedbackTier.ONE_OFF,
            proposed_rule_text=comment.text,
            message="one-off fix; discarded after the next generation context",
        )
    if comment.scope == Scope.ALWAYS:
        return RoutedFeedback(
            comment_id=comment.id,
            tier=FeedbackTier.PROMOTE,
            proposed_rule_text=comment.text,
            message="scope=always; immediate promotion candidate",
        )
    # Inferred generalisation of an existing candidate (same fingerprint).
    fp = _fingerprint(comment.text)
    for cand in existing_candidates or []:
        if not cand.retired and _fingerprint(cand.text) == fp:
            return RoutedFeedback(
                comment_id=comment.id,
                tier=FeedbackTier.CANDIDATE,
                proposed_rule_text=cand.text,
                message=f"inferred pattern matches {cand.id} (deck={deck})",
            )
    return RoutedFeedback(
        comment_id=comment.id,
        tier=FeedbackTier.CANDIDATE,
        proposed_rule_text=comment.text,
        message="inferred pattern; stored as inactive candidate",
    )


def record_inferred_pattern(
    text: str,
    *,
    run_id: str,
    round_n: int,
    candidates: list[CandidateRule],
    comment_id: str | None = None,
    deck_id: str | None = None,
) -> CandidateRule:
    """Upsert an inferred candidate. Occurrence counts unique decks, not rounds."""
    deck = deck_id or run_id
    fp = _fingerprint(text)
    now = datetime.now(timezone.utc)
    for cand in candidates:
        if cand.retired:
            continue
        if _fingerprint(cand.text) != fp:
            continue
        already = any((e.deck_id or e.run_id) == deck for e in cand.evidence)
        cand.evidence.append(
            CandidateEvidence(
                run_id=run_id,
                round_n=round_n,
                comment_id=comment_id,
                deck_id=deck,
            )
        )
        if not already:
            cand.occurrence_count = len(unique_deck_ids(cand))
        cand.last_seen_at = now
        return cand
    cand = CandidateRule(
        id=f"cand_{len(candidates) + 1:03d}",
        text=text.strip(),
        occurrence_count=1,
        evidence=[
            CandidateEvidence(
                run_id=run_id,
                round_n=round_n,
                comment_id=comment_id,
                deck_id=deck,
            )
        ],
        created_at=now,
        last_seen_at=now,
        retired=False,
    )
    candidates.append(cand)
    return cand


def route_comments(
    comments: list[HumanComment],
    *,
    run_id: str,
    round_n: int,
    candidates_path: Path | str | None = None,
    deck_id: str | None = None,
) -> list[RoutedFeedback]:
    """Route all comments for a round; update ``candidates.json`` as needed."""
    path = Path(candidates_path) if candidates_path else None
    candidates = load_candidates(path) if path and path.is_file() else []
    routed: list[RoutedFeedback] = []
    for comment in comments:
        item = route_comment(
            comment,
            run_id=run_id,
            round_n=round_n,
            existing_candidates=candidates,
            deck_id=deck_id,
        )
        routed.append(item)
        if item.tier == FeedbackTier.ONE_OFF:
            continue
        # Always-scoped and inferred patterns may accrue candidate evidence.
        # One-offs are never written anywhere persistent.
        if item.proposed_rule_text:
            record_inferred_pattern(
                item.proposed_rule_text,
                run_id=run_id,
                round_n=round_n,
                candidates=candidates,
                comment_id=comment.id,
                deck_id=deck_id or run_id,
            )
    if path is not None:
        save_candidates(path, candidates)
    return routed


def load_candidates(path: Path | str) -> list[CandidateRule]:
    """Load candidate rules from ``candidates.json``."""
    src = Path(path)
    if not src.is_file():
        return []
    data = json.loads(src.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data = data.get("candidates", [])
    return [CandidateRule.model_validate(item) for item in data]


def save_candidates(path: Path | str, candidates: list[CandidateRule]) -> None:
    """Persist candidate rules to ``candidates.json``."""
    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    payload = [c.model_dump(mode="json") for c in candidates]
    dest.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
