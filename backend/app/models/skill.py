"""Skill rule and candidate models (PRD §7.10, §8)."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class SkillRuleSection(str, Enum):
    HOUSE = "house"
    STYLE = "style"


class SkillRule(BaseModel):
    """Artifact: skill_rule — versioned generation rule (PRD §8)."""

    id: str
    text: str
    section: SkillRuleSection
    origin: str
    credit: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    active: bool = True


class CandidateEvidence(BaseModel):
    """Evidence supporting a candidate rule promotion."""

    run_id: str
    round_n: int = Field(..., ge=1)
    comment_id: Optional[str] = None
    deck_id: str = ""


class CandidateRule(BaseModel):
    """Inferred / pending rule stored in skills candidates.json (PRD §7.10)."""

    id: str
    text: str
    occurrence_count: int = Field(0, ge=0)
    evidence: list[CandidateEvidence] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_seen_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    retired: bool = False
