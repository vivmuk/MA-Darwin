"""Gate report models — Gate 1/2 deterministic; Gate 3 scored."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class GateCheckResult(BaseModel):
    check_id: str
    passed: bool
    message: str = ""
    locations: list[dict[str, Any]] = Field(default_factory=list)


class Gate1Report(BaseModel):
    passed: bool
    checks: list[GateCheckResult] = Field(default_factory=list)


class Gate2Report(BaseModel):
    passed: bool
    checks: list[GateCheckResult] = Field(default_factory=list)
    measurements: dict[str, Any] = Field(default_factory=dict)


class CriterionScore(BaseModel):
    criterion_id: str
    score: Optional[float] = None
    na: bool = False
    rationale: str = ""
    coordinates: Optional[dict[str, float]] = None


class SlideJudgeScore(BaseModel):
    slide: int
    criteria: list[CriterionScore] = Field(default_factory=list)
    total: float = 0.0


class Gate3Report(BaseModel):
    deck_score: float
    worst_slide_score: float
    slide_scores: list[SlideJudgeScore] = Field(default_factory=list)
    deck_criteria: list[CriterionScore] = Field(default_factory=list)
    advanced_to_human: bool = False
