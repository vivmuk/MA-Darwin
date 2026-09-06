"""Ingestion document types (PDF pages and extracted assets)."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class PageText(BaseModel):
    """Full text extracted from one PDF page."""

    page: int = Field(..., ge=1)
    text: str


class ExtractedAsset(BaseModel):
    """Figure or table image extracted from the paper."""

    id: str
    kind: str = Field(..., description="figure | table")
    page: int = Field(..., ge=1)
    caption: str = ""
    path: str
    width_px: Optional[int] = Field(default=None, ge=1)
    height_px: Optional[int] = Field(default=None, ge=1)


class ParsedDocument(BaseModel):
    """Combined PDF parse result written under runs/{id}/assets/."""

    paper_id: str
    page_count: int = Field(..., ge=0)
    pages: list[PageText] = Field(default_factory=list)
    assets: list[ExtractedAsset] = Field(default_factory=list)
