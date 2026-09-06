"""Slide planner — claim/figure assignment before layout (Prompt 4)."""

from __future__ import annotations

from pathlib import Path

from app.models.blueprint import Blueprint
from app.models.claim import ClaimLedger
from app.models.document import ExtractedAsset
from app.models.layout import LayoutSpec
from app.models.run import Brief
from app.models.slide import HumanComment, SlidePlan


def plan_slides(
    *,
    blueprint: Blueprint,
    ledger: ClaimLedger,
    brief: Brief,
    skill_version: str,
    one_off_comments: list[HumanComment] | None = None,
    prompt_path: Path | str | None = None,
) -> SlidePlan:
    """Produce ``slide_plan.json``: which claims/figures go on which slide.

    Planning is a separate step from pptx layout — the model must not emit
    python-pptx code here.

    Parameters
    ----------
    blueprint:
        Slide roles and constraints.
    ledger:
        Validated claim ledger.
    brief:
        Structured generation brief.
    skill_version:
        Active skill directory name (e.g. ``v1``).
    one_off_comments:
        ``scope: this-deck-only`` comments injected for the next round only.
    prompt_path:
        Optional override for ``prompts/slide_plan.md``.

    Returns
    -------
    SlidePlan
        Artifact suitable for ``slide_plan.json``.
    """
    raise NotImplementedError


def emit_layout_spec(
    *,
    plan: SlidePlan,
    blueprint: Blueprint,
    ledger: ClaimLedger,
    assets: list[ExtractedAsset] | None = None,
    prior_spec: LayoutSpec | None = None,
    locked_slides: list[int] | None = None,
) -> LayoutSpec:
    """Deterministic layout emission: SlidePlan → explicit inch coordinates."""
    if any(arg is None for arg in (plan, blueprint, ledger)):
        raise NotImplementedError
    from app.generation.layout import compose_layout_spec

    return compose_layout_spec(
        plan=plan,
        blueprint=blueprint,
        ledger=ledger,
        assets=assets,
        prior_spec=prior_spec,
        locked_slides=locked_slides,
    )


def write_slide_plan(plan: SlidePlan, output_path: Path | str) -> Path:
    """Serialize a slide plan to disk.

    Parameters
    ----------
    plan:
        Planned slide assignments.
    output_path:
        Destination path (typically ``round_n/slide_plan.json``).

    Returns
    -------
    Path
        Path written.
    """
    raise NotImplementedError
