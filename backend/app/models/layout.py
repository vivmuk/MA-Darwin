"""LayoutSpec — source of truth for slide geometry (inches on a 13.333 × 7.5 canvas)."""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


CANVAS_WIDTH_IN = 13.333333
CANVAS_HEIGHT_IN = 7.5


class TextAlign(str, Enum):
    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"


class FontWeight(str, Enum):
    NORMAL = "normal"
    BOLD = "bold"


class LayoutElementKind(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    SHAPE = "shape"


class LayoutElement(BaseModel):
    """One absolutely positioned element. No autofit, no implicit size."""

    id: str
    kind: LayoutElementKind = LayoutElementKind.TEXT
    x: float = Field(..., description="Left edge in inches")
    y: float = Field(..., description="Top edge in inches")
    w: float = Field(..., gt=0, description="Width in inches")
    h: float = Field(..., gt=0, description="Height in inches")
    font_family: str = "Arial"
    font_size_pt: float = Field(16, gt=0)
    font_weight: FontWeight = FontWeight.NORMAL
    color: str = "#2C3E50"
    alignment: TextAlign = TextAlign.LEFT
    text: str = ""
    claim_ids: list[str] = Field(default_factory=list)
    image_path: Optional[str] = None
    fill: Optional[str] = None


class LayoutSlide(BaseModel):
    """One slide in the layout spec."""

    slide: int = Field(..., ge=1)
    role: str = ""
    width: float = CANVAS_WIDTH_IN
    height: float = CANVAS_HEIGHT_IN
    background: str = "#FFFFFF"
    elements: list[LayoutElement] = Field(default_factory=list)
    speaker_notes: str = ""


class LayoutSpec(BaseModel):
    """Artifact: layout_spec.json — explicit layout for every render target."""

    canvas_width: float = CANVAS_WIDTH_IN
    canvas_height: float = CANVAS_HEIGHT_IN
    slides: list[LayoutSlide] = Field(default_factory=list)
