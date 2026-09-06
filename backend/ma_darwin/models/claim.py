"""Claim ledger — every extractable fact with page provenance."""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


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
    ci_low: Optional[float] = None
    ci_high: Optional[float] = None
    p_value: Optional[float] = None
    raw: str = Field(description="Exact numeric token as it appeared in source.")


class ClaimLedgerEntry(BaseModel):
    id: str = Field(description="Stable claim id, e.g. C-014")
    text: str
    verbatim: str
    page: int = Field(ge=1)
    section: str = ""
    claim_type: ClaimType
    evidence_class: EvidenceClass
    numbers: list[NumberValue] = Field(default_factory=list)

    @field_validator("id")
    @classmethod
    def validate_claim_id(cls, value: str) -> str:
        if not value.startswith("C-"):
            raise ValueError("claim id must start with 'C-'")
        return value


class ClaimLedger(BaseModel):
    paper_id: str
    entries: list[ClaimLedgerEntry] = Field(default_factory=list)

    def get(self, claim_id: str) -> ClaimLedgerEntry:
        for entry in self.entries:
            if entry.id == claim_id:
                return entry
        raise KeyError(claim_id)

    def ids(self) -> set[str]:
        return {e.id for e in self.entries}
