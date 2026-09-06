"""Slide plan, slide map, and human review comment models (PRD §§7.4, 7.9, §8)."""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Severity(str, Enum):
    MUST_FIX = "must-fix"
    NICE_TO_HAVE = "nice-to-have"


class Scope(str, Enum):
    THIS_DECK_ONLY = "this-deck-only"
    ALWAYS = "always"


class SlideMapEntry(BaseModel):
    """Maps a slide text element to claim ledger IDs (PRD §8)."""

    slide: int = Field(..., ge=1)
    element_id: str
    text: str
    claim_ids: list[str] = Field(default_factory=list)


class SlideMap(BaseModel):
    """Artifact: slide_map.json — every text element → claim IDs."""

    deck_path: str = ""
    entries: list[SlideMapEntry] = Field(default_factory=list)


class SlidePlanFigure(BaseModel):
    """Figure asset selected for a planned slide."""

    asset_id: str
    caption: str = ""
    page: int = Field(..., ge=1)


class ChartSeries(BaseModel):
    """One editable-chart series (OOXML + embedded Excel)."""

    name: str
    values: list[float] = Field(default_factory=list)


class SlideChart(BaseModel):
    """Skill-writer chart payload — never a raster substitute."""

    title: str = ""
    categories: list[str] = Field(default_factory=list)
    series: list[ChartSeries] = Field(default_factory=list)


class SlidePlanSlide(BaseModel):
    """One slide in the pre-layout plan (Prompt 4 two-stage generation)."""

    slide: int = Field(..., ge=1)
    role: str
    headline: str
    claim_ids: list[str] = Field(default_factory=list)
    figures: list[SlidePlanFigure] = Field(default_factory=list)
    speaker_notes: str = ""
    required_content_filled: list[str] = Field(default_factory=list)
    bullets: list[str] = Field(default_factory=list)
    citation: str = ""
    body: str = ""
    chart: SlideChart | None = None


class SlidePlan(BaseModel):
    """Artifact: slide_plan.json — claim/figure assignment before pptx layout."""

    blueprint_id: str
    skill_version: str = "v1"
    slides: list[SlidePlanSlide] = Field(default_factory=list)


class HumanComment(BaseModel):
    """Pinned review comment (PRD §8)."""

    id: str
    slide: int = Field(..., ge=1)
    x: float
    y: float
    text: str
    severity: Severity
    criterion_tag: str
    scope: Scope


class CommentsFile(BaseModel):
    """Artifact: comments.json — human review pins for a round."""

    run_id: str
    round_n: int = Field(..., ge=1)
    comments: list[HumanComment] = Field(default_factory=list)
