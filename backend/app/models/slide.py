"""Slide map and human review comment models (PRD §8)."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class Severity(str, Enum):
    MUST_FIX = "must-fix"
    NICE_TO_HAVE = "nice-to-have"


class Scope(str, Enum):
    THIS_DECK_ONLY = "this-deck-only"
    ALWAYS = "always"


class SlideMapEntry(BaseModel):
    """Maps a slide text element to claim ledger IDs (PRD §8)."""

    slide: int
    element_id: str
    text: str
    claim_ids: list[str] = Field(default_factory=list)


class HumanComment(BaseModel):
    """Pinned review comment (PRD §8)."""

    id: str
    slide: int
    x: float
    y: float
    text: str
    severity: Severity
    criterion_tag: str
    scope: Scope
