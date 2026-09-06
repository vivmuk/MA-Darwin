"""Gate and judge score models (PRD §§7.6–7.8, §8)."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

from app.models.common import CheckLocation, IssueCoordinates


class GateCheckResult(BaseModel):
    """Single mechanical check outcome."""

    name: str
    passed: bool
    message: str = ""
    flagged: bool = False
    locations: list[CheckLocation] = Field(default_factory=list)


class Gate1Result(BaseModel):
    """Artifact: gate1.json — content & compliance report."""

    gate: Literal["gate1"] = "gate1"
    passed: bool
    checks: list[GateCheckResult] = Field(default_factory=list)


class Gate2Result(BaseModel):
    """Artifact: gate2.json — visual auto-check report."""

    gate: Literal["gate2"] = "gate2"
    passed: bool
    checks: list[GateCheckResult] = Field(default_factory=list)


# Back-compat alias used by Round / older call sites.
GateResult = Gate1Result


class JudgeCriterionScore(BaseModel):
    """One rubric criterion score from the vision judge."""

    criterion: str
    weight: float
    score: Optional[float] = None  # None when N/A (e.g. charts with no visual)
    rationale: str = ""
    coordinates: Optional[IssueCoordinates] = None
    scope: Literal["slide", "deck"] = "slide"
    slide: Optional[int] = Field(default=None, ge=1)


class SlideJudgeResult(BaseModel):
    """Per-slide Gate 3 aggregate and criterion breakdown."""

    slide: int = Field(..., ge=1)
    role: str
    score: float
    criteria: list[JudgeCriterionScore] = Field(default_factory=list)


class SlideScoreSummary(BaseModel):
    """Compact slide → score pair for UI tiles and trend lines."""

    slide: int = Field(..., ge=1)
    score: float


class Gate3Result(BaseModel):
    """Artifact: gate3.json — vision-judge report (PRD §7.8)."""

    gate: Literal["gate3"] = "gate3"
    deck_score: float
    worst_slide_score: float
    slide_scores: list[SlideScoreSummary] = Field(default_factory=list)
    slide_results: list[SlideJudgeResult] = Field(default_factory=list)
    deck_criteria: list[JudgeCriterionScore] = Field(default_factory=list)
    criteria: list[JudgeCriterionScore] = Field(
        default_factory=list,
        description="Flattened criterion scores (slide + deck) for scorecard UI",
    )
    passed: bool = False
    judge_runs: int = Field(3, ge=1)
    temperature: float = 0.0


# Back-compat name from Prompt 1 / PRD §8.
JudgeScore = Gate3Result
