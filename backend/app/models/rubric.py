"""Rubric config models — mirrors config/rubric.yaml."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class RubricCriterion(BaseModel):
    """One scored criterion with weight and written anchors."""

    id: str
    name: str
    weight: float
    anchors: dict[str, str] = Field(default_factory=dict)
    na_when: Optional[str] = None
    scope: str = "slide"  # slide | deck


class Rubric(BaseModel):
    """Loaded Gate 3 rubric (total points, slide + deck criteria)."""

    total_points: int = 100
    slide_criteria: list[RubricCriterion] = Field(default_factory=list)
    deck_criteria: list[RubricCriterion] = Field(default_factory=list)
