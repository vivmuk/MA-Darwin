"""Skill evolution engine (Phase 8)."""

from app.evolution.credit import (
    persist_credits,
    retire_stale_candidates,
    rules_for_removal,
    update_credits,
)
from app.evolution.feedback_router import (
    load_candidates,
    record_inferred_pattern,
    route_comment,
    route_comments,
    save_candidates,
    unique_deck_ids,
)
from app.evolution.promotion import (
    UnmeasurableRuleError,
    apply_promotions,
    is_measurable_rule,
    promote_rule,
    validate_rule_text,
    write_skill_rule,
)
from app.evolution.regression import (
    activate_skill_version,
    evaluate_regression,
    guard_promotion,
    load_regression_set,
)

__all__ = [
    "UnmeasurableRuleError",
    "activate_skill_version",
    "apply_promotions",
    "evaluate_regression",
    "guard_promotion",
    "is_measurable_rule",
    "load_candidates",
    "load_regression_set",
    "persist_credits",
    "promote_rule",
    "record_inferred_pattern",
    "retire_stale_candidates",
    "route_comment",
    "route_comments",
    "rules_for_removal",
    "save_candidates",
    "unique_deck_ids",
    "update_credits",
    "validate_rule_text",
    "write_skill_rule",
]
