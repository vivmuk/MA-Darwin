"""Slide map and human review comments."""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Severity(str, Enum):
    MUST_FIX = "must_fix"
    NICE_TO_HAVE = "nice_to_have"


class Scope(str, Enum):
    THIS_DECK_ONLY = "this_deck_only"
    ALWAYS = "always"


class SlideMapEntry(BaseModel):
    slide: int = Field(ge=1)
    element_id: str
    text: str
    claim_ids: list[str] = Field(min_length=1)

    def assert_mapped(self) -> None:
        """Unmapped text is a bug, not a warning."""
        if not self.claim_ids:
            raise ValueError(f"element {self.element_id} has no claim_ids")


class SlideMap(BaseModel):
    entries: list[SlideMapEntry] = Field(default_factory=list)

    def claim_ids_for_slide(self, slide: int) -> set[str]:
        ids: set[str] = set()
        for entry in self.entries:
            if entry.slide == slide:
                ids.update(entry.claim_ids)
        return ids

    def unmapped_elements(self) -> list[SlideMapEntry]:
        return [e for e in self.entries if not e.claim_ids]


class HumanComment(BaseModel):
    id: str
    slide: int = Field(ge=1)
    x: float
    y: float
    text: str
    severity: Severity
    criterion_tag: str
    scope: Scope
    override_score: Optional[float] = None
