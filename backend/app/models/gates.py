"""Gate and judge score models (PRD §§7.6–7.8, §8)."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class GateCheckResult(BaseModel):
    """Single mechanical check outcome."""

    name: str
    passed: bool
    message: str = ""
    locations: list[dict[str, Any]] = Field(default_factory=list)


class GateResult(BaseModel):
    """Gate 1 / Gate 2 report (pass/fail + per-check detail)."""

    gate: str
    passed: bool
    checks: list[GateCheckResult] = Field(default_factory=list)


class JudgeCriterionScore(BaseModel):
    """One rubric criterion score from the vision judge."""

    criterion: str
    weight: float
    score: Optional[float] = None  # None when N/A (e.g. charts with no visual)
    rationale: str = ""
    coordinates: Optional[dict[str, float]] = None


class JudgeScore(BaseModel):
    """Gate 3 vision-judge report (PRD §7.8)."""

    deck_score: float
    worst_slide_score: float
    slide_scores: dict[int, float] = Field(default_factory=dict)
    criteria: list[JudgeCriterionScore] = Field(default_factory=list)
    passed: bool = False
