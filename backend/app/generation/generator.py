"""Deck generator — slide_plan → pptx + slide_map (PRD §7.4 / Prompt 4)."""

from __future__ import annotations

from pathlib import Path

from app.models.blueprint import Blueprint
from app.models.claim import ClaimLedger
from app.models.document import ExtractedAsset
from app.models.run import Brief, GenerationResult
from app.models.slide import SlideMap, SlidePlan


def generate_deck(
    *,
    blueprint: Blueprint,
    ledger: ClaimLedger,
    brief: Brief,
    skill_version: str,
    slide_plan: SlidePlan,
    output_dir: Path | str,
    locked_slides: list[int] | None = None,
    prior_deck_path: Path | str | None = None,
    assets: list[ExtractedAsset] | None = None,
) -> GenerationResult:
    """Render a ``SlidePlan`` into ``deck.pptx`` and ``slide_map.json``.

    Locked slides are copied byte-identical from ``prior_deck_path`` and never
    regenerated. Speaker notes must carry page references for every claim.

    Parameters
    ----------
    blueprint:
        Active blueprint.
    ledger:
        Claim ledger (generator may only use mapped claims).
    brief:
        Structured brief.
    skill_version:
        Active skill version id.
    slide_plan:
        Output of ``planner.plan_slides``.
    output_dir:
        Round directory for artifacts.
    locked_slides:
        1-based slide indices that must be copied through unchanged.
    prior_deck_path:
        Previous round pptx providing locked slide bytes.
    assets:
        Extracted paper figures/tables available for embedding.

    Returns
    -------
    GenerationResult
        Paths and slide map for the generated deck.
    """
    raise NotImplementedError


def load_slide_map(path: Path | str) -> SlideMap:
    """Load and validate a ``slide_map.json`` artifact.

    Parameters
    ----------
    path:
        Path to ``slide_map.json``.

    Returns
    -------
    SlideMap
        Validated slide map.
    """
    raise NotImplementedError
