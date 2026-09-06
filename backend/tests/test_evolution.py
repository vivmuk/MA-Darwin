"""Evolution engine tests — frozen fixtures only; no live generator/judge output."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from app.evolution.credit import rules_for_removal, update_credits
from app.evolution.feedback_router import (
    record_inferred_pattern,
    route_comment,
    route_comments,
    unique_deck_ids,
)
from app.evolution.promotion import (
    UnmeasurableRuleError,
    apply_promotions,
    is_measurable_rule,
    validate_rule_text,
)
from app.evolution.regression import activate_skill_version, evaluate_regression
from app.models.gates import Gate3Result, JudgeCriterionScore
from app.models.run import FeedbackTier, PromotionDecision
from app.models.skill import SkillRule, SkillRuleSection
from app.models.slide import CommentsFile, HumanComment, Scope, Severity

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _skill_tree(tmp_path: Path) -> Path:
    skill = tmp_path / "skills" / "v1"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("# skill\n", encoding="utf-8")
    (skill / "house_rules.md").write_text("# House rules\n- human only\n", encoding="utf-8")
    (skill / "style_rules.md").write_text("# Style rules\n", encoding="utf-8")
    (skill / "CHANGELOG.md").write_text("# Changelog\n", encoding="utf-8")
    return skill


def _regression_set(tmp_path: Path, *, baseline: float, current: float, n: int = 5) -> Path:
    root = tmp_path / "regression"
    for i in range(1, n + 1):
        item = root / f"paper_{i:02d}"
        item.mkdir(parents=True)
        (item / "baseline.json").write_text(
            json.dumps({"deck_score": baseline}) + "\n", encoding="utf-8"
        )
        (item / "current.json").write_text(
            json.dumps({"deck_score": current}) + "\n", encoding="utf-8"
        )
    return root


def test_this_deck_only_never_written_to_skill_files(tmp_path: Path) -> None:
    payload = json.loads((FIXTURES / "comments.json").read_text(encoding="utf-8"))
    comments_file = CommentsFile.model_validate(payload)
    one_off = next(c for c in comments_file.comments if c.scope == Scope.THIS_DECK_ONLY)
    skill = _skill_tree(tmp_path)
    house_before = (skill / "house_rules.md").read_text(encoding="utf-8")
    candidates_path = tmp_path / "candidates.json"
    routed = route_comments(
        [one_off],
        run_id=comments_file.run_id,
        round_n=comments_file.round_n,
        candidates_path=candidates_path,
    )
    assert routed[0].tier == FeedbackTier.ONE_OFF
    apply_promotions(
        routed,
        skill_dir=skill,
        candidates_path=candidates_path,
        regression_dir=_regression_set(tmp_path, baseline=80, current=80),
    )
    for name in ("SKILL.md", "house_rules.md", "style_rules.md", "CHANGELOG.md"):
        text = (skill / name).read_text(encoding="utf-8")
        assert one_off.text not in text
        assert one_off.id not in text
    if candidates_path.is_file():
        assert one_off.text not in candidates_path.read_text(encoding="utf-8")
    assert (skill / "house_rules.md").read_text(encoding="utf-8") == house_before


def test_vague_rule_rejected_by_measurability_validator() -> None:
    assert is_measurable_rule("max 5 bullets, max 12 words each") is True
    fixture_rule = json.loads((FIXTURES / "skill_rule.json").read_text(encoding="utf-8"))
    assert is_measurable_rule(fixture_rule["text"]) is True
    with pytest.raises(UnmeasurableRuleError, match="no measurable condition"):
        validate_rule_text("Make slides cleaner")
    with pytest.raises(UnmeasurableRuleError, match="no measurable condition"):
        validate_rule_text("polish the deck and make it nicer")


def test_regression_drop_rejects_and_logs_changelog(tmp_path: Path) -> None:
    skill = _skill_tree(tmp_path)
    style_before = (skill / "style_rules.md").read_text(encoding="utf-8")
    house_before = (skill / "house_rules.md").read_text(encoding="utf-8")
    regen = _regression_set(tmp_path, baseline=80.0, current=70.0, n=5)
    comment = HumanComment(
        id="hc_always",
        slide=1,
        x=0.1,
        y=0.1,
        text="max 5 bullets, max 12 words each",
        severity=Severity.MUST_FIX,
        criterion_tag="information_density",
        scope=Scope.ALWAYS,
    )
    candidates_path = tmp_path / "candidates.json"
    routed = route_comments(
        [comment],
        run_id="run_aaaaaaaaaaaa",
        round_n=1,
        candidates_path=candidates_path,
    )
    results = apply_promotions(
        routed,
        skill_dir=skill,
        candidates_path=candidates_path,
        regression_dir=regen,
    )
    assert results[0].decision == PromotionDecision.REJECTED_REGRESSION
    assert results[0].regression_delta is not None
    assert results[0].regression_delta <= -2
    changelog = (skill / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "Rejected" in changelog
    assert "delta" in changelog.lower()
    assert (skill / "style_rules.md").read_text(encoding="utf-8") == style_before
    assert (skill / "house_rules.md").read_text(encoding="utf-8") == house_before


def test_candidate_requires_distinct_decks_not_rounds(tmp_path: Path) -> None:
    candidates: list = []
    text = "max 4 bullets per slide"
    record_inferred_pattern(text, run_id="run_deck_aaaaaa", round_n=1, candidates=candidates)
    record_inferred_pattern(text, run_id="run_deck_aaaaaa", round_n=2, candidates=candidates)
    record_inferred_pattern(text, run_id="run_deck_aaaaaa", round_n=3, candidates=candidates)
    assert len(candidates) == 1
    assert unique_deck_ids(candidates[0]) == {"run_deck_aaaaaa"}
    assert candidates[0].occurrence_count == 1

    record_inferred_pattern(text, run_id="run_deck_bbbbbb", round_n=1, candidates=candidates)
    record_inferred_pattern(text, run_id="run_deck_cccccc", round_n=1, candidates=candidates)
    assert candidates[0].occurrence_count == 3
    assert unique_deck_ids(candidates[0]) == {
        "run_deck_aaaaaa",
        "run_deck_bbbbbb",
        "run_deck_cccccc",
    }

    from app.evolution.promotion import promote_rule
    from app.models.run import RoutedFeedback

    skill = _skill_tree(tmp_path)
    regen = _regression_set(tmp_path, baseline=80.0, current=80.0, n=5)
    deferred = promote_rule(
        RoutedFeedback(
            comment_id="hc_r2",
            tier=FeedbackTier.CANDIDATE,
            proposed_rule_text=text,
        ),
        skill_dir=skill,
        candidates=candidates[:1] and [
            type(candidates[0]).model_validate(
                {
                    **candidates[0].model_dump(mode="json"),
                    "evidence": [
                        e
                        for e in candidates[0].evidence
                        if (e.deck_id or e.run_id) == "run_deck_aaaaaa"
                    ],
                    "occurrence_count": 1,
                }
            )
        ],
        promotion_threshold=3,
        max_mutations_per_round=2,
        mutations_so_far=[],
        regression_dir=regen,
    )
    assert deferred.decision == PromotionDecision.DEFERRED

    promoted = promote_rule(
        RoutedFeedback(
            comment_id="hc_d3",
            tier=FeedbackTier.CANDIDATE,
            proposed_rule_text=text,
        ),
        skill_dir=skill,
        candidates=candidates,
        promotion_threshold=3,
        max_mutations_per_round=2,
        mutations_so_far=[],
        regression_dir=regen,
    )
    assert promoted.decision == PromotionDecision.PROMOTED
    assert text in (skill / "style_rules.md").read_text(encoding="utf-8")
    assert "human only" in (skill / "house_rules.md").read_text(encoding="utf-8")


def test_credit_and_removal_threshold() -> None:
    rule = SkillRule.model_validate(
        json.loads((FIXTURES / "skill_rule.json").read_text(encoding="utf-8"))
    )
    prev = Gate3Result(
        deck_score=80,
        worst_slide_score=70,
        criteria=[
            JudgeCriterionScore(
                criterion="information_density",
                weight=10,
                score=8,
                rationale="ok",
            )
        ],
    )
    curr = Gate3Result(
        deck_score=70,
        worst_slide_score=60,
        criteria=[
            JudgeCriterionScore(
                criterion="information_density",
                weight=10,
                score=5,
                rationale="worse",
            )
        ],
    )
    updates = update_credits(
        [rule],
        previous_gate3=prev,
        current_gate3=curr,
        credit_map={rule.id: {"criterion_tag": "information_density"}},
    )
    assert updates and updates[0].improved is False
    assert rule.credit == -1
    rule.credit = -3
    assert rules_for_removal([rule]) == [rule]


def test_rollback_activates_prior_version(tmp_path: Path) -> None:
    root = tmp_path / "skills"
    v1 = _skill_tree(tmp_path)
    # _skill_tree uses tmp_path/skills/v1 — copy as v2 sibling
    v2 = root / "v2"
    shutil.copytree(v1, v2)
    (v2 / "style_rules.md").write_text("# v2 style\n", encoding="utf-8")
    active = activate_skill_version("v1", skills_root=root)
    assert active.name == "v1"
    assert (root / "ACTIVE").read_text(encoding="utf-8").strip() == "v1"
    activate_skill_version("v2", skills_root=root)
    assert (root / "ACTIVE").read_text(encoding="utf-8").strip() == "v2"


def test_empty_regression_set_fails_closed(tmp_path: Path) -> None:
    skill = _skill_tree(tmp_path)
    empty = tmp_path / "empty_reg"
    empty.mkdir()
    with pytest.raises(FileNotFoundError):
        # load on missing
        from app.evolution.regression import load_regression_set

        load_regression_set(tmp_path / "does_not_exist")
    report = evaluate_regression(skill_dir=skill, regression_dir=empty, tolerance=2)
    assert report.passed is False
    assert report.decks_evaluated == 0
