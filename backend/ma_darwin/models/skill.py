"""Skill rule models for evolution engine (Phase 8)."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class SkillRuleSection(str, Enum):
    HOUSE = "house"
    STYLE = "style"


class SkillRule(BaseModel):
    id: str
    text: str
    section: SkillRuleSection
    origin: str = Field(description="deck + round + comment id provenance")
    credit: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    active: bool = True
    measurable: bool = Field(
        default=True,
        description="Rules must be testable constraints, not vibes.",
    )
    occurrence_count: int = 0
    candidate: bool = False
    retired: bool = False
    last_reaffirmed_deck: Optional[str] = None
