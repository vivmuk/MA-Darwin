"""Shared geometry and location types used across gate artifacts."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class BoundingBox(BaseModel):
    """Axis-aligned box in slide coordinates (points or normalized 0–1)."""

    x: float
    y: float
    w: float
    h: float


class IssueCoordinates(BaseModel):
    """Point or box highlighting a gate / judge finding on a slide image."""

    x: float
    y: float
    w: Optional[float] = None
    h: Optional[float] = None


class CheckLocation(BaseModel):
    """Element-level failure location for Gate 1 / Gate 2 UI pins."""

    slide: int = Field(..., ge=1, description="1-based slide index")
    element_id: Optional[str] = None
    x: Optional[float] = None
    y: Optional[float] = None
    w: Optional[float] = None
    h: Optional[float] = None
    detail: str = ""
