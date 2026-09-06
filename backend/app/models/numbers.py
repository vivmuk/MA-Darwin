"""Numbers index — numbers_index.json (Prompt 2 / Gate 1 number sweep)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field


class NumberIndexEntry(BaseModel):
    """One numeral found in source text with page and sentence context."""

    raw: str
    value: float
    unit: Optional[str] = None
    page: int = Field(..., ge=1)
    sentence: str
    char_start: Optional[int] = Field(default=None, ge=0)
    char_end: Optional[int] = Field(default=None, ge=0)


class NumbersIndex(BaseModel):
    """Artifact: numbers_index.json — ground truth for the number sweep."""

    paper_id: str
    numbers: list[NumberIndexEntry] = Field(default_factory=list)
    extracted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
