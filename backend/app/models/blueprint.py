"""Blueprint data models (PRD §7.3) — data files, not code."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.models.claim import EvidenceClass
from app.models.run import DeckType


class BlueprintSlide(BaseModel):
    """One slide role within a blueprint."""

    role: str
    required_content: list[str] = Field(default_factory=list)
    allowed_evidence_classes: list[EvidenceClass] = Field(default_factory=list)
    max_claims: int = Field(6, ge=1)
    requires_visual: bool = False
    counts_against_slide_count: bool = True


class Blueprint(BaseModel):
    """Loaded blueprint document (e.g. blueprints/msl_physician_8.json)."""

    id: str
    name: str
    deck_type: DeckType = DeckType.MSL_PHYSICIAN
    slide_count: int = Field(8, ge=1)
    description: str = ""
    slides: list[BlueprintSlide] = Field(default_factory=list)
