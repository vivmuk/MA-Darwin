"""Run / Round / Brief models (PRD §8)."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.models.gates import GateResult, JudgeScore
from app.models.slide import HumanComment


class DeckType(str, Enum):
    MSL_PHYSICIAN = "msl_physician"


class RunStatus(str, Enum):
    CREATED = "created"
    RUNNING = "running"
    AWAITING_REVIEW = "awaiting_review"
    COMPLETE = "complete"
    FAILED = "failed"
    PLATEAU = "plateau"


class Brief(BaseModel):
    """Structured brief fields (PRD §7.2). Freeform text is stored on Run as needed."""

    slide_count: int = 8
    deck_type: DeckType = DeckType.MSL_PHYSICIAN
    audience: str = "physician"
    purpose: str = "MSL presentation"
    notes: str = ""


class Round(BaseModel):
    """One generate → render → gate → review cycle (PRD §8)."""

    n: int
    deck_path: Optional[str] = None
    slide_images: list[str] = Field(default_factory=list)
    gate1: Optional[GateResult] = None
    gate2: Optional[GateResult] = None
    gate3: Optional[JudgeScore] = None
    human: dict[str, Any] = Field(default_factory=dict)
    mutations: list[dict[str, Any]] = Field(default_factory=list)
    locked_slides: list[int] = Field(default_factory=list)
    comments: list[HumanComment] = Field(default_factory=list)


class Run(BaseModel):
    """Top-level run record (PRD §8)."""

    id: str
    paper_id: str
    brief: Brief
    blueprint_id: str = "msl_physician_8"
    skill_version: str = "v1"
    rounds: list[Round] = Field(default_factory=list)
    status: RunStatus = RunStatus.CREATED
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    best_round_n: Optional[int] = None
    # Freeform brief string as supplied on the CLI (passthrough until brief parser lands).
    brief_text: str = ""
