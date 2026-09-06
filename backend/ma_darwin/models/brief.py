"""Brief — structured request parsed from the reviewer's freeform input."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class DeckType(str, Enum):
    MSL_PHYSICIAN = "msl_physician"


class Brief(BaseModel):
    slide_count: int = Field(default=8, ge=1, le=30)
    deck_type: DeckType = DeckType.MSL_PHYSICIAN
    audience: str = "treating physician / HCP"
    purpose: str = "medical-to-medical scientific exchange"
    notes: str = ""
    raw_text: str = Field(
        default="",
        description="Original freeform brief; treated as user intent, not PDF data.",
    )
