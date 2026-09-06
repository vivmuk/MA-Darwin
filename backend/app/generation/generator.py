"""Deck generator — SlidePlan → LayoutSpec → pptx + slide_map."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

from app.generation.layout import compose_layout_spec, load_layout_spec, write_layout_spec
from app.generation.skill_writer import write_skill_pptx
from app.models.blueprint import Blueprint
from app.models.claim import ClaimLedger, ClaimLedgerEntry
from app.models.document import ExtractedAsset
from app.models.layout import LayoutElementKind, LayoutSpec
from app.models.run import Brief, GenerationResult
from app.models.slide import SlideMap, SlideMapEntry, SlidePlan


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
    on_slide: Callable[..., None] | None = None,
) -> GenerationResult:
    """Compose a LayoutSpec, then write pptx + maps from that spec.

    Locked slides are copied from the prior ``layout_spec.json`` (same folder as
    ``prior_deck_path``) and never recomposed.
    """
    if any(arg is None for arg in (blueprint, ledger, brief, slide_plan)):
        raise NotImplementedError

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    plan_path = out / "slide_plan.json"
    plan_path.write_text(slide_plan.model_dump_json(indent=2) + "\n", encoding="utf-8")

    prior_spec = _load_prior_spec(prior_deck_path, locked_slides)
    spec = compose_layout_spec(
        plan=slide_plan,
        blueprint=blueprint,
        ledger=ledger,
        assets=assets,
        prior_spec=prior_spec,
        locked_slides=locked_slides,
    )
    spec_path = write_layout_spec(spec, out / "layout_spec.json")
    deck_path = write_skill_pptx(
        slide_plan,
        ledger,
        out / "deck.pptx",
        assets=assets,
        prior_spec=prior_spec,
        locked_slides=locked_slides,
        on_slide=on_slide,
    )
    del skill_version

    claims = {entry.id: entry for entry in ledger.entries}
    slide_map = _slide_map_from_spec(spec, deck_path)
    map_path = out / "slide_map.json"
    map_path.write_text(slide_map.model_dump_json(indent=2) + "\n", encoding="utf-8")

    return GenerationResult(
        deck_path=str(deck_path),
        slide_map_path=str(map_path),
        slide_plan_path=str(plan_path),
        slide_map=slide_map,
        layout_spec_path=str(spec_path),
        layout_spec=spec,
        speaker_notes_pages=_notes_pages(spec, claims),
    )


def load_slide_map(path: Path | str) -> SlideMap:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return SlideMap.model_validate(payload)


def _load_prior_spec(
    prior_deck_path: Path | str | None,
    locked_slides: list[int] | None,
) -> LayoutSpec | None:
    locked = set(locked_slides or [])
    if not locked:
        return None
    if prior_deck_path is None:
        raise ValueError("locked_slides requires prior_deck_path")
    prior = Path(prior_deck_path)
    spec_path = prior.with_name("layout_spec.json")
    if not spec_path.is_file():
        raise ValueError(f"locked slides require prior layout_spec.json beside {prior}")
    return load_layout_spec(spec_path)


def _slide_map_from_spec(spec: LayoutSpec, deck_path: Path) -> SlideMap:
    entries: list[SlideMapEntry] = []
    for slide in spec.slides:
        for el in slide.elements:
            if el.kind != LayoutElementKind.TEXT:
                continue
            if not (el.text or "").strip():
                continue
            entries.append(
                SlideMapEntry(
                    slide=slide.slide,
                    element_id=el.id,
                    text=el.text,
                    claim_ids=list(el.claim_ids),
                )
            )
    return SlideMap(deck_path=str(deck_path.as_posix()), entries=entries)


def _notes_pages(spec: LayoutSpec, claims: dict[str, ClaimLedgerEntry]) -> list[int]:
    pages: list[int] = []
    for slide in spec.slides:
        for el in slide.elements:
            for cid in el.claim_ids:
                entry = claims.get(cid)
                if entry is not None:
                    pages.append(entry.page)
    return sorted(set(pages))
