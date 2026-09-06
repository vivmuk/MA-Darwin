"""Tests for MA-Darwin Pydantic data models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from ma_darwin.models import (
    Brief,
    ClaimLedger,
    ClaimLedgerEntry,
    ClaimType,
    DeckType,
    EvidenceClass,
    HumanComment,
    NumberValue,
    Round,
    Run,
    RunStatus,
    Scope,
    Severity,
    SlideMap,
    SlideMapEntry,
)


def test_brief_defaults() -> None:
    brief = Brief()
    assert brief.slide_count == 8
    assert brief.deck_type == DeckType.MSL_PHYSICIAN


def test_claim_ledger_entry_requires_c_prefix() -> None:
    with pytest.raises(ValidationError):
        ClaimLedgerEntry(
            id="014",
            text="N=120",
            verbatim="N = 120",
            page=1,
            claim_type=ClaimType.VERBATIM,
            evidence_class=EvidenceClass.DESIGN,
        )


def test_claim_ledger_get_and_ids() -> None:
    entry = ClaimLedgerEntry(
        id="C-001",
        text="Randomized N=120",
        verbatim="randomized, N = 120",
        page=2,
        section="Methods",
        claim_type=ClaimType.PARAPHRASE,
        evidence_class=EvidenceClass.DESIGN,
        numbers=[NumberValue(value=120.0, unit="patients", raw="120")],
    )
    ledger = ClaimLedger(paper_id="paper-1", entries=[entry])
    assert ledger.get("C-001").page == 2
    assert ledger.ids() == {"C-001"}
    with pytest.raises(KeyError):
        ledger.get("C-999")


def test_slide_map_entry_requires_claim_ids() -> None:
    with pytest.raises(ValidationError):
        SlideMapEntry(slide=1, element_id="tb_1", text="Hello", claim_ids=[])


def test_slide_map_unmapped_is_empty_when_all_mapped() -> None:
    sm = SlideMap(
        entries=[
            SlideMapEntry(
                slide=1,
                element_id="tb_1",
                text="N=120",
                claim_ids=["C-001"],
            )
        ]
    )
    assert sm.unmapped_elements() == []
    assert sm.claim_ids_for_slide(1) == {"C-001"}


def test_human_comment_scope_always_is_skill_signal() -> None:
    comment = HumanComment(
        id="hc-1",
        slide=3,
        x=0.4,
        y=0.2,
        text="Max 5 bullets",
        severity=Severity.MUST_FIX,
        criterion_tag="information_density",
        scope=Scope.ALWAYS,
    )
    assert comment.scope == Scope.ALWAYS


def test_run_current_round() -> None:
    run = Run(
        id="run_1",
        paper_id="paper-1",
        brief=Brief(notes="8 slide MSL deck"),
        rounds=[Round(n=1), Round(n=2)],
        status=RunStatus.AWAITING_HUMAN,
    )
    assert run.current_round() is not None
    assert run.current_round().n == 2
