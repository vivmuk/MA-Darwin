"""Run and Round — immutable round snapshots under runs/{run_id}/round_{n}/."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field

from ma_darwin.models.brief import Brief
from ma_darwin.models.gates import Gate1Report, Gate2Report, Gate3Report
from ma_darwin.models.slide import HumanComment


class RunStatus(str, Enum):
    CREATED = "created"
    INGESTING = "ingesting"
    GENERATING = "generating"
    RENDERING = "rendering"
    GATING = "gating"
    AWAITING_HUMAN = "awaiting_human"
    REITERATING = "reiterating"
    EXPORT_READY = "export_ready"
    FAILED = "failed"
    STOPPED = "stopped"


class Round(BaseModel):
    n: int = Field(ge=1)
    deck_path: Optional[str] = None
    slide_images: list[str] = Field(default_factory=list)
    gate1: Optional[Gate1Report] = None
    gate2: Optional[Gate2Report] = None
    gate3: Optional[Gate3Report] = None
    human_comments: list[HumanComment] = Field(default_factory=list)
    mutations: list[dict[str, Any]] = Field(default_factory=list)
    locked_slides: list[int] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Run(BaseModel):
    id: str
    paper_id: str
    brief: Brief
    blueprint_id: str = "msl_physician_8"
    skill_version: str = "v1"
    rounds: list[Round] = Field(default_factory=list)
    status: RunStatus = RunStatus.CREATED
    best_round_n: Optional[int] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def current_round(self) -> Optional[Round]:
        if not self.rounds:
            return None
        return max(self.rounds, key=lambda r: r.n)
