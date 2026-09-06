"""Rule credit counters and stale-candidate retirement (PRD §7.10)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from app.models.gates import Gate3Result
from app.models.run import CreditUpdate
from app.models.skill import CandidateRule, SkillRule


def _mean_criterion(gate3: Gate3Result | None, tag: str) -> Optional[float]:
    if gate3 is None or not tag:
        return None
    scores: list[float] = []
    for item in gate3.criteria:
        if item.criterion == tag and item.score is not None:
            scores.append(float(item.score))
    for slide in gate3.slide_results:
        for item in slide.criteria:
            if item.criterion == tag and item.score is not None:
                scores.append(float(item.score))
    if not scores:
        return None
    return sum(scores) / len(scores)


def _tag_for_rule(rule: SkillRule, credit_map: dict[str, dict]) -> str:
    stored = credit_map.get(rule.id, {})
    if stored.get("criterion_tag"):
        return str(stored["criterion_tag"])
    # Origin sometimes carries the comment; tag may be stored beside credit.
    return str(stored.get("tag") or "")


def update_credits(
    active_rules: list[SkillRule],
    *,
    previous_gate3: Gate3Result | None,
    current_gate3: Gate3Result,
    credit_map: dict[str, dict] | None = None,
) -> list[CreditUpdate]:
    """Adjust credit for each active rule based on tagged criterion score delta."""
    mapping = credit_map or {}
    updates: list[CreditUpdate] = []
    for rule in active_rules:
        if not rule.active:
            continue
        tag = _tag_for_rule(rule, mapping)
        before = _mean_criterion(previous_gate3, tag)
        after = _mean_criterion(current_gate3, tag)
        if before is None or after is None:
            continue
        previous_credit = rule.credit
        if after > before:
            rule.credit += 1
            improved = True
        elif after < before:
            rule.credit -= 1
            improved = False
        else:
            continue
        updates.append(
            CreditUpdate(
                rule_id=rule.id,
                previous_credit=previous_credit,
                new_credit=rule.credit,
                criterion_tag=tag,
                improved=improved,
            )
        )
    return updates


def rules_for_removal(
    active_rules: list[SkillRule],
    *,
    credit_removal_threshold: int = -3,
) -> list[SkillRule]:
    """Return rules at or below the removal credit threshold for UI surfacing."""
    return [r for r in active_rules if r.active and r.credit <= credit_removal_threshold]


def retire_stale_candidates(
    candidates: list[CandidateRule],
    *,
    decks_since: dict[str, int],
    stale_after_decks: int = 10,
) -> list[CandidateRule]:
    """Retire candidates with no reaffirmation within ``stale_after_decks`` decks."""
    retired: list[CandidateRule] = []
    for cand in candidates:
        elapsed = decks_since.get(cand.id, 0)
        if not cand.retired and elapsed >= stale_after_decks:
            cand.retired = True
            retired.append(cand)
    return retired


def persist_credits(skill_dir: Path | str, rules: list[SkillRule]) -> None:
    """Persist updated credit counters alongside the skill version."""
    dest = Path(skill_dir) / "credits.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    existing: dict[str, dict] = {}
    if dest.is_file():
        raw = json.loads(dest.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            existing = raw
    for rule in rules:
        slot = existing.setdefault(rule.id, {})
        slot["credit"] = rule.credit
        slot["active"] = rule.active
        slot["text"] = rule.text
    dest.write_text(json.dumps(existing, indent=2) + "\n", encoding="utf-8")


def load_credit_map(skill_dir: Path | str) -> dict[str, dict]:
    path = Path(skill_dir) / "credits.json"
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}
