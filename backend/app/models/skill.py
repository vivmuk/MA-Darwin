"""Skill rule models (PRD §8)."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


class SkillRuleSection(str, Enum):
    HOUSE = "house"
    STYLE = "style"


class SkillRule(BaseModel):
    """Versioned generation rule (PRD §8)."""

    id: str
    text: str
    section: SkillRuleSection
    origin: str
    credit: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    active: bool = True
