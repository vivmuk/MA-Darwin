"""Claim ledger models (PRD §8)."""

from __future__ import annotations

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
    page: int
    section: Optional[str] = None
    claim_type: ClaimType
    evidence_class: EvidenceClass
    numbers: list[NumberValue] = Field(default_factory=list)
