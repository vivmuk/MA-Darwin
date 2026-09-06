"""Promote candidate / always-scoped rules into the skill (PRD §7.10)."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

import yaml

from app.config import load_defaults
from app.evolution.feedback_router import unique_deck_ids
from app.evolution.regression import guard_promotion
from app.models.run import (
    FeedbackTier,
    MutationKind,
    MutationRecord,
    PromotionDecision,
    PromotionResult,
    RoutedFeedback,
)
from app.models.skill import CandidateRule, SkillRule, SkillRuleSection

_MEASURABLE = re.compile(
    r"("
    r"\bmax(?:imum)?\b|\bmin(?:imum)?\b|\bat most\b|\bat least\b|"
    r"\bno more than\b|\bno fewer than\b|"
    r"<=|>=|<|>|≤|≥|"
    r"\b\d+(?:\.\d+)?\s*(?:pt|px|%|words?|bullets?|colours?|colors?|fonts?)?\b"
    r")",
    re.IGNORECASE,
)
_HOUSE_FILE = "house_rules.md"
_STYLE_FILE = "style_rules.md"


class UnmeasurableRuleError(ValueError):
    """Raised when proposed rule text has no testable condition."""


def is_measurable_rule(text: str) -> bool:
    """Return True iff rule text contains a testable / measurable condition."""
    if not text or not str(text).strip():
        return False
    return _MEASURABLE.search(text) is not None


def validate_rule_text(text: str) -> None:
    """Reject vague rule text with a clear error message."""
    if not is_measurable_rule(text):
        raise UnmeasurableRuleError(
            "Rule text has no measurable condition. "
            "Need a numeric limit or testable constraint "
            "(e.g. 'max 5 bullets, max 12 words each'); "
            f"got {text!r}."
        )


def _defaults(defaults_config: Path | str | None) -> dict:
    if defaults_config is None:
        return load_defaults()
    data = yaml.safe_load(Path(defaults_config).read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError("defaults config must be a mapping")
    return data


def _next_rule_id(skill_dir: Path) -> str:
    credits = skill_dir / "credits.json"
    n = 1
    if credits.is_file():
        data = json.loads(credits.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            n = len(data) + 1
    style = skill_dir / _STYLE_FILE
    if style.is_file():
        n = max(n, style.read_text(encoding="utf-8").count("<!-- sr_") + 1)
    return f"sr_{n:03d}"


def write_skill_rule(rule: SkillRule, skill_dir: Path | str) -> Path:
    """Append a promoted rule to ``style_rules.md`` and return the path touched."""
    dest_dir = Path(skill_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    house = dest_dir / _HOUSE_FILE
    # Never write house rules here — human-only file.
    if house.is_file():
        before = house.read_text(encoding="utf-8")
    else:
        before = None
    style = dest_dir / _STYLE_FILE
    existing = style.read_text(encoding="utf-8") if style.is_file() else "# Style rules\n"
    if not existing.endswith("\n"):
        existing += "\n"
    block = f"- {rule.text}  <!-- {rule.id} credit={rule.credit} origin={rule.origin} -->\n"
    style.write_text(existing + block, encoding="utf-8")
    if before is not None and house.read_text(encoding="utf-8") != before:
        raise RuntimeError("house_rules.md was modified; promotion aborted")
    credits = dest_dir / "credits.json"
    data: dict = {}
    if credits.is_file():
        loaded = json.loads(credits.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            data = loaded
    data[rule.id] = {
        "credit": rule.credit,
        "active": rule.active,
        "text": rule.text,
        "origin": rule.origin,
        "section": rule.section.value if hasattr(rule.section, "value") else str(rule.section),
    }
    credits.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return style


def _append_changelog(skill_dir: Path, body: str) -> None:
    path = skill_dir / "CHANGELOG.md"
    existing = path.read_text(encoding="utf-8") if path.is_file() else "# Changelog\n"
    if not existing.endswith("\n"):
        existing += "\n"
    path.write_text(existing + body, encoding="utf-8")


def _candidate_for(feedback: RoutedFeedback, candidates: list[CandidateRule]) -> CandidateRule | None:
    text = (feedback.proposed_rule_text or "").strip()
    if not text:
        return None
    needle = re.sub(r"\s+", " ", text.lower())
    for cand in candidates:
        if re.sub(r"\s+", " ", cand.text.lower()) == needle:
            return cand
    return None


def promote_rule(
    feedback: RoutedFeedback,
    *,
    skill_dir: Path | str,
    candidates: list[CandidateRule],
    promotion_threshold: int,
    max_mutations_per_round: int,
    mutations_so_far: list[MutationRecord],
    regression_dir: Path | str | None = None,
    tolerance: float | None = None,
) -> PromotionResult:
    """Attempt promotion into ``style_rules.md``."""
    skill = Path(skill_dir)
    if feedback.tier == FeedbackTier.ONE_OFF:
        return PromotionResult(
            decision=PromotionDecision.DEFERRED,
            message="one-off feedback is never written to a skill file",
        )
    if len(mutations_so_far) >= max_mutations_per_round:
        return PromotionResult(
            decision=PromotionDecision.SKIPPED_CAP,
            message=f"max_mutations_per_round={max_mutations_per_round} reached",
        )

    text = (feedback.proposed_rule_text or "").strip()
    try:
        validate_rule_text(text)
    except UnmeasurableRuleError as exc:
        return PromotionResult(decision=PromotionDecision.REJECTED_VAGUE, message=str(exc))

    cand = _candidate_for(feedback, candidates)
    unique_decks = len(unique_deck_ids(cand)) if cand else 0
    immediate = feedback.tier == FeedbackTier.PROMOTE
    ready = immediate or unique_decks >= promotion_threshold
    if not ready:
        return PromotionResult(
            decision=PromotionDecision.DEFERRED,
            rule_id=cand.id if cand else None,
            message=(
                f"candidate needs {promotion_threshold} decks; "
                f"has {unique_decks} unique decks"
            ),
        )

    rule = SkillRule(
        id=_next_rule_id(skill),
        text=text,
        section=SkillRuleSection.STYLE,
        origin=f"{cand.evidence[-1].run_id}/round_{cand.evidence[-1].round_n}/{feedback.comment_id}"
        if cand and cand.evidence
        else f"comment/{feedback.comment_id}",
        credit=0,
        created_at=datetime.now(timezone.utc),
        active=True,
    )
    report = guard_promotion(
        rule,
        skill_dir=skill,
        regression_dir=regression_dir,
        tolerance=tolerance,
    )
    if not report.passed:
        return PromotionResult(
            decision=PromotionDecision.REJECTED_REGRESSION,
            rule_id=rule.id,
            message="regression gate rejected promotion",
            regression_delta=report.delta,
        )

    write_skill_rule(rule, skill)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    _append_changelog(
        skill,
        (
            f"\n## Promoted {rule.id} ({stamp})\n\n"
            f"- {rule.text}\n"
            f"- origin: {rule.origin}\n"
        ),
    )
    mutations_so_far.append(
        MutationRecord(
            id=f"mut_{len(mutations_so_far) + 1:03d}",
            kind=MutationKind.PROMOTION,
            text=rule.text,
            origin_comment_id=feedback.comment_id,
            rule_id=rule.id,
        )
    )
    return PromotionResult(
        decision=PromotionDecision.PROMOTED,
        rule_id=rule.id,
        message="promoted into style_rules.md",
        regression_delta=report.delta,
    )


def apply_promotions(
    routed: list[RoutedFeedback],
    *,
    skill_dir: Path | str,
    candidates_path: Path | str,
    defaults_config: Path | str | None = None,
    regression_dir: Path | str | None = None,
) -> list[PromotionResult]:
    """Apply all eligible promotions for a round, respecting mutation caps."""
    cfg = _defaults(defaults_config)
    threshold = int(cfg.get("promotion_threshold", 3))
    max_mut = int(cfg.get("max_mutations_per_round", 2))
    tolerance = float(cfg.get("regression_tolerance", 2))
    from app.evolution.feedback_router import load_candidates, save_candidates

    candidates = load_candidates(candidates_path)
    mutations: list[MutationRecord] = []
    results: list[PromotionResult] = []
    for item in routed:
        if item.tier == FeedbackTier.ONE_OFF:
            results.append(
                PromotionResult(
                    decision=PromotionDecision.DEFERRED,
                    message="one-off feedback is never written to a skill file",
                )
            )
            continue
        results.append(
            promote_rule(
                item,
                skill_dir=skill_dir,
                candidates=candidates,
                promotion_threshold=threshold,
                max_mutations_per_round=max_mut,
                mutations_so_far=mutations,
                regression_dir=regression_dir,
                tolerance=tolerance,
            )
        )
    save_candidates(candidates_path, candidates)
    return results
