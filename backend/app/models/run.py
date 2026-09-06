"""Run / Round / Brief / manifest models (PRD §8)."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from app.models.gates import Gate1Result, Gate2Result, Gate3Result
from app.models.layout import LayoutSpec
from app.models.slide import HumanComment, SlideMap


class DeckType(str, Enum):
    MSL_PHYSICIAN = "msl_physician"


class RunStatus(str, Enum):
    CREATED = "created"
    RUNNING = "running"
    AWAITING_REVIEW = "awaiting_review"
    COMPLETE = "complete"
    FAILED = "failed"
    PLATEAU = "plateau"


class Brief(BaseModel):
    """Structured brief fields (PRD §7.2). Freeform text is stored on Run as needed."""

    slide_count: int = Field(8, ge=1)
    deck_type: DeckType = DeckType.MSL_PHYSICIAN
    audience: str = "physician"
    purpose: str = "MSL presentation"
    notes: str = ""


class ScoreOverride(BaseModel):
    """Human override of a Gate 3 criterion score (PRD §7.9)."""

    criterion: str
    slide: Optional[int] = Field(default=None, ge=1)
    original_score: float
    override_score: float
    delta: float
    rationale: str = ""


class HumanReviewState(BaseModel):
    """Typed human review payload on a Round (replaces untyped dict)."""

    approved_slides: list[int] = Field(default_factory=list)
    score_overrides: list[ScoreOverride] = Field(default_factory=list)
    synthesized_approvals: list[str] = Field(
        default_factory=list,
        description="Claim IDs of synthesized claims explicitly approved by a human",
    )
    evaluation_locked: bool = False


class MutationKind(str, Enum):
    ONE_OFF = "one_off"
    CANDIDATE = "candidate"
    PROMOTION = "promotion"
    ROLLBACK = "rollback"
    REJECTION = "rejection"


class MutationRecord(BaseModel):
    """One skill / generation mutation logged on a round (PRD §7.10)."""

    id: str
    kind: MutationKind
    text: str
    origin_comment_id: Optional[str] = None
    rule_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Round(BaseModel):
    """One generate → render → gate → review cycle (PRD §8)."""

    n: int = Field(..., ge=1)
    deck_path: Optional[str] = None
    slide_images: list[str] = Field(default_factory=list)
    slide_svgs: list[str] = Field(default_factory=list)
    layout_spec_path: Optional[str] = None
    gate1: Optional[Gate1Result] = None
    gate2: Optional[Gate2Result] = None
    gate3: Optional[Gate3Result] = None
    human: HumanReviewState = Field(default_factory=HumanReviewState)
    mutations: list[MutationRecord] = Field(default_factory=list)
    locked_slides: list[int] = Field(default_factory=list)
    comments: list[HumanComment] = Field(default_factory=list)
    cost_usd: float = 0.0
    token_count: int = Field(0, ge=0)


class Run(BaseModel):
    """Top-level run record (PRD §8)."""

    id: str
    paper_id: str
    brief: Brief
    blueprint_id: str = "msl_physician_8"
    skill_version: str = "v1"
    rounds: list[Round] = Field(default_factory=list)
    status: RunStatus = RunStatus.CREATED
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    best_round_n: Optional[int] = None
    brief_text: str = ""
    budget_usd: float = 25.0
    auto_rounds_used: int = Field(0, ge=0)


class RunManifest(BaseModel):
    """Artifact: manifest.json — run directory header written by RunStore."""

    id: str
    paper_id: str
    paper_path: str
    source_paper: str = ""
    brief: str
    brief_parsed: Brief
    blueprint_id: str
    skill_version: str
    status: RunStatus
    rounds: list[int] = Field(default_factory=list)
    best_round_n: Optional[int] = None
    created_at: datetime
    updated_at: datetime


class StoppingReason(str, Enum):
    SUCCESS = "success"
    MAX_ROUNDS = "max_rounds"
    BUDGET = "budget"
    PLATEAU = "plateau"
    FAILED = "failed"
    CONTINUE = "continue"


class StoppingDecision(BaseModel):
    """Orchestrator stopping-condition evaluation (PRD §10)."""

    halt: bool
    reason: StoppingReason
    message: str = ""


class ProgressEventType(str, Enum):
    """SSE milestone event names (PRD §9 Zone B / Prompt 6).

    UI-coordinated additions: skill_loaded, ocr_started, ocr_page, library_call.
    Existing names stay stable for the sibling progress animation.
    """

    SKILL_LOADED = "skill_loaded"
    OCR_STARTED = "ocr_started"
    OCR_PAGE = "ocr_page"
    PAGES_PARSED = "pages_parsed"
    CLAIMS_EXTRACTED = "claims_extracted"
    FIGURES_EXTRACTED = "figures_extracted"
    BLUEPRINT_SLOT_FILLED = "blueprint_slot_filled"
    LIBRARY_CALL = "library_call"
    RENDERING = "rendering"
    GATE1_COMPLETE = "gate1_complete"
    GATE2_COMPLETE = "gate2_complete"
    JUDGING_SLIDE = "judging_slide"
    ROUND_COMPLETE = "round_complete"
    AWAITING_REVIEW = "awaiting_review"
    PLATEAU = "plateau"
    ERROR = "error"
    HEARTBEAT = "heartbeat"


class ProgressEvent(BaseModel):
    """Typed SSE progress event payload."""

    event: ProgressEventType
    run_id: str
    round_n: Optional[int] = Field(default=None, ge=1)
    message: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    elapsed_ms: int = Field(0, ge=0)
    token_count: int = Field(0, ge=0)
    cost_usd: float = 0.0
    # Optional milestone counters (only set when relevant).
    pages: Optional[int] = Field(default=None, ge=0)
    claims: Optional[int] = Field(default=None, ge=0)
    figures: Optional[int] = Field(default=None, ge=0)
    slot: Optional[int] = Field(default=None, ge=1)
    slot_total: Optional[int] = Field(default=None, ge=1)
    gate_flags: Optional[int] = Field(default=None, ge=0)
    slide: Optional[int] = Field(default=None, ge=1)
    slide_total: Optional[int] = Field(default=None, ge=1)
    tool: Optional[str] = None
    tools: Optional[list[str]] = None
    skill_name: Optional[str] = None
    skill_version: Optional[str] = None


class GenerationResult(BaseModel):
    """Output of the deck generator (layout spec + pptx + maps)."""

    deck_path: str
    slide_map_path: str
    slide_plan_path: str
    slide_map: SlideMap
    layout_spec_path: str = ""
    layout_spec: Optional[LayoutSpec] = None
    speaker_notes_pages: list[int] = Field(default_factory=list)


class RenderResult(BaseModel):
    """Output of the LayoutSpec render pipeline (SVG + PNG + PDF)."""

    pdf_path: str
    slide_images: list[str] = Field(default_factory=list)
    slide_svgs: list[str] = Field(default_factory=list)
    dpi: int = Field(150, ge=72)


class FeedbackTier(str, Enum):
    ONE_OFF = "one_off"
    CANDIDATE = "candidate"
    PROMOTE = "promote"


class RoutedFeedback(BaseModel):
    """Result of sorting one human comment into an evolution tier."""

    comment_id: str
    tier: FeedbackTier
    proposed_rule_text: Optional[str] = None
    message: str = ""


class PromotionDecision(str, Enum):
    PROMOTED = "promoted"
    REJECTED_VAGUE = "rejected_vague"
    REJECTED_REGRESSION = "rejected_regression"
    DEFERRED = "deferred"
    SKIPPED_CAP = "skipped_cap"


class PromotionResult(BaseModel):
    """Outcome of attempting to promote a rule into the skill."""

    decision: PromotionDecision
    rule_id: Optional[str] = None
    message: str = ""
    regression_delta: Optional[float] = None


class CreditUpdate(BaseModel):
    """Per-rule credit delta after a round."""

    rule_id: str
    previous_credit: int
    new_credit: int
    criterion_tag: str
    improved: bool


class RegressionReport(BaseModel):
    """Regression-set evaluation before committing a promotion."""

    passed: bool
    mean_score_before: float
    mean_score_after: float
    delta: float
    tolerance: float
    decks_evaluated: int = Field(0, ge=0)


class ExportBundleResult(BaseModel):
    """Path and metadata for a written export zip."""

    path: str
    run_id: str
    round_n: int
    contents: list[str] = Field(default_factory=list)
