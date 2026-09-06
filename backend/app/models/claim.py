"""Claim ledger models — ledger.json (PRD §7.1, §8)."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ClaimType(str, Enum):
    VERBATIM = "verbatim"
    PARAPHRASE = "paraphrase"
    SYNTHESIZED = "synthesized"


class EvidenceClass(str, Enum):
    PRIMARY_ENDPOINT = "primary_endpoint"
    SECONDARY_ENDPOINT = "secondary_endpoint"
    EXPLORATORY = "exploratory"
    POST_HOC = "post_hoc"
    SAFETY = "safety"
    DESIGN = "design"
    BACKGROUND = "background"
    LIMITATION = "limitation"


class NumberValue(BaseModel):
    """Numeric value embedded in a claim."""

    value: float
    unit: Optional[str] = None
    ci: Optional[str] = None
    p_value: Optional[str] = None
    raw: str = ""


class ClaimLedgerEntry(BaseModel):
    """Single extractable fact from the paper (PRD §8)."""

    id: str
    text: str
    verbatim: str
    page: int = Field(..., ge=1)
    section: Optional[str] = None
    claim_type: ClaimType
    evidence_class: EvidenceClass
    numbers: list[NumberValue] = Field(default_factory=list)


class ClaimLedger(BaseModel):
    """Artifact: ledger.json — full claim ledger for a paper."""

    paper_id: str
    entries: list[ClaimLedgerEntry] = Field(default_factory=list)
    extracted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source_pages: int = Field(0, ge=0)
