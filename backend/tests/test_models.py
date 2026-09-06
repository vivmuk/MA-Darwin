"""Tests for PRD §8 Pydantic models."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.models import (
    Brief,
    ClaimLedgerEntry,
    ClaimType,
    EvidenceClass,
    GateCheckResult,
    GateResult,
    HumanComment,
    JudgeCriterionScore,
    JudgeScore,
    NumberValue,
    Round,
    Run,
    RunStatus,
    Scope,
    Severity,
    SkillRule,
    SkillRuleSection,
    SlideMapEntry,
)


def test_claim_ledger_entry_matches_prd_section_8() -> None:
    entry = ClaimLedgerEntry(
        id="C-014",
        text="Primary endpoint met",
        verbatim="The primary endpoint was met (p=0.01)",
        page=4,
        section="Results",
        claim_type=ClaimType.VERBATIM,
        evidence_class=EvidenceClass.PRIMARY_ENDPOINT,
        numbers=[NumberValue(value=0.01, p_value="0.01", raw="p=0.01")],
    )
    dumped = entry.model_dump()
    assert set(dumped) >= {
        "id",
        "text",
        "verbatim",
        "page",
        "section",
        "claim_type",
        "evidence_class",
        "numbers",
    }


def test_slide_map_entry_matches_prd() -> None:
    entry = SlideMapEntry(
        slide=3,
        element_id="tb_2",
        text="N=420",
        claim_ids=["C-014"],
    )
    assert entry.model_dump() == {
        "slide": 3,
        "element_id": "tb_2",
        "text": "N=420",
        "claim_ids": ["C-014"],
    }


def test_human_comment_and_skill_rule() -> None:
    comment = HumanComment(
        id="hc_1",
        slide=2,
        x=0.4,
        y=0.6,
        text="Tighten bullets",
        severity=Severity.MUST_FIX,
        criterion_tag="information_density",
        scope=Scope.ALWAYS,
    )
    rule = SkillRule(
        id="sr_1",
        text="max 5 bullets, max 12 words each",
        section=SkillRuleSection.STYLE,
        origin="deck_x/round_1/hc_1",
        credit=0,
        created_at=datetime.now(timezone.utc),
        active=True,
    )
    assert comment.scope == Scope.ALWAYS
    assert rule.section == SkillRuleSection.STYLE


def test_run_and_round_with_gates() -> None:
    gate1 = GateResult(
        gate="gate1",
        passed=True,
        checks=[GateCheckResult(name="claim_mapping", passed=True)],
    )
    gate3 = JudgeScore(
        deck_score=82.0,
        worst_slide_score=70.0,
        slide_scores={1: 90.0, 2: 70.0},
        criteria=[
            JudgeCriterionScore(
                criterion="visual_hierarchy",
                weight=15,
                score=14,
                rationale="Clear title hierarchy",
            )
        ],
        passed=True,
    )
    rnd = Round(
        n=1,
        deck_path="round_1/deck.pptx",
        slide_images=["round_1/slides/slide_01.png"],
        gate1=gate1,
        gate2=None,
        gate3=gate3,
        human={},
        mutations=[],
        locked_slides=[1],
    )
    run = Run(
        id="run_abcdef012345",
        paper_id="paper_1",
        brief=Brief(notes="Create an 8 slide MSL deck"),
        rounds=[rnd],
        status=RunStatus.CREATED,
    )
    assert run.rounds[0].gate3 is not None
    assert run.rounds[0].gate3.deck_score == 82.0


def test_invalid_claim_type_rejected() -> None:
    with pytest.raises(ValidationError):
        ClaimLedgerEntry(
            id="C-001",
            text="x",
            verbatim="x",
            page=1,
            claim_type="invented",  # type: ignore[arg-type]
            evidence_class=EvidenceClass.DESIGN,
        )
