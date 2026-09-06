"""Deck generator — slide_plan → pptx + slide_map (PRD §7.4 / Prompt 4)."""

from __future__ import annotations

import json
from copy import deepcopy
from io import BytesIO
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE_TYPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt

from app.models.blueprint import Blueprint
from app.models.claim import ClaimLedger, ClaimLedgerEntry, EvidenceClass
from app.models.document import ExtractedAsset
from app.models.run import Brief, GenerationResult
from app.models.slide import SlideMap, SlideMapEntry, SlidePlan, SlidePlanSlide
from app.paths import CONFIG_DIR

# Widescreen 16:9
_SLIDE_W = Inches(13.333333)
_SLIDE_H = Inches(7.5)

_NAVY = RGBColor(0x1B, 0x2A, 0x4A)
_BODY = RGBColor(0x2C, 0x3E, 0x50)
_FONT = "Arial"
_MAX_BULLETS = 6

_ENDPOINT_LABELS = {
    EvidenceClass.SECONDARY_ENDPOINT: "Secondary endpoint",
    EvidenceClass.EXPLORATORY: "Exploratory",
    EvidenceClass.POST_HOC: "Post hoc",
}

_SHAPE_TAGS = {
    qn("p:sp"),
    qn("p:pic"),
    qn("p:grpSp"),
    qn("p:cxnSp"),
    qn("p:graphicFrame"),
}


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

    Planning is a separate step: this function persists the given plan, then
    lays it out. It does not ask a model to write pptx.
    """
    if any(arg is None for arg in (blueprint, ledger, brief, slide_plan)):
        raise NotImplementedError

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    plan_path = out / "slide_plan.json"
    _write_json(slide_plan, plan_path)

    claims = {entry.id: entry for entry in ledger.entries}
    locked = set(locked_slides or [])
    prior = Presentation(str(prior_deck_path)) if prior_deck_path and locked else None
    if locked and prior is None:
        raise ValueError("locked_slides requires prior_deck_path")

    role_by_index = {i + 1: spec.role for i, spec in enumerate(blueprint.slides)}
    spec_by_role = {spec.role: spec for spec in blueprint.slides}
    asset_by_id = {a.id: a for a in (assets or [])}
    endpoint_labels = _endpoint_labels_from_config()

    prs = Presentation()
    prs.slide_width = _SLIDE_W
    prs.slide_height = _SLIDE_H

    entries: list[SlideMapEntry] = []
    notes_pages: list[int] = []

    for planned in slide_plan.slides:
        slide_no = planned.slide
        if slide_no in locked:
            src_idx = slide_no - 1
            if src_idx < 0 or src_idx >= len(prior.slides):
                raise ValueError(f"locked slide {slide_no} missing from prior deck")
            dest = _copy_slide(prior, src_idx, prs)
            entries.extend(_map_copied_slide(dest, slide_no, planned, claims))
            notes_pages.extend(_pages_for_claims(planned.claim_ids, claims))
            continue

        dest = prs.slides.add_slide(prs.slide_layouts[6])
        role = planned.role or role_by_index.get(slide_no, "")
        spec = spec_by_role.get(role)
        max_claims = spec.max_claims if spec else _MAX_BULLETS
        requires_visual = bool(spec.requires_visual) if spec else False
        slide_entries, pages = _render_slide(
            dest,
            planned,
            claims,
            asset_by_id,
            max_claims=max_claims,
            requires_visual=requires_visual,
            endpoint_labels=endpoint_labels,
            skill_version=skill_version,
        )
        entries.extend(slide_entries)
        notes_pages.extend(pages)

    deck_path = out / "deck.pptx"
    prs.save(str(deck_path))

    slide_map = SlideMap(deck_path=str(deck_path.as_posix()), entries=entries)
    map_path = out / "slide_map.json"
    _write_json(slide_map, map_path)

    return GenerationResult(
        deck_path=str(deck_path),
        slide_map_path=str(map_path),
        slide_plan_path=str(plan_path),
        slide_map=slide_map,
        speaker_notes_pages=sorted(set(notes_pages)),
    )


def load_slide_map(path: Path | str) -> SlideMap:
    """Load and validate a ``slide_map.json`` artifact."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return SlideMap.model_validate(payload)


def _write_json(model, path: Path) -> None:
    path.write_text(model.model_dump_json(indent=2) + "\n", encoding="utf-8")


def _endpoint_labels_from_config() -> dict[EvidenceClass, str]:
    labels = dict(_ENDPOINT_LABELS)
    cfg_path = CONFIG_DIR / "compliance.yaml"
    if not cfg_path.is_file():
        return labels
    try:
        import yaml

        data = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
        for key, value in (data.get("endpoint_labels") or {}).items():
            try:
                labels[EvidenceClass(key)] = str(value)
            except ValueError:
                continue
    except Exception:
        return labels
    return labels


def _pages_for_claims(claim_ids: list[str], claims: dict[str, ClaimLedgerEntry]) -> list[int]:
    return [claims[cid].page for cid in claim_ids if cid in claims]


def _notes_for_claims(claim_ids: list[str], claims: dict[str, ClaimLedgerEntry]) -> str:
    parts = []
    for cid in claim_ids:
        entry = claims.get(cid)
        if entry is None:
            continue
        parts.append(f"{cid} p.{entry.page}")
    return "; ".join(parts)


def _render_slide(
    slide,
    planned: SlidePlanSlide,
    claims: dict[str, ClaimLedgerEntry],
    asset_by_id: dict[str, ExtractedAsset],
    *,
    max_claims: int,
    requires_visual: bool,
    endpoint_labels: dict[EvidenceClass, str],
    skill_version: str,
) -> tuple[list[SlideMapEntry], list[int]]:
    del skill_version  # reserved: house/style rules constrain layout, not copy
    n = planned.slide
    claim_ids = [cid for cid in planned.claim_ids if cid in claims][:max_claims]
    if not claim_ids:
        claim_ids = list(planned.claim_ids[:max_claims])

    entries: list[SlideMapEntry] = []

    headline = planned.headline.strip() or (claims[claim_ids[0]].text if claim_ids and claim_ids[0] in claims else planned.role)
    headline = _ensure_endpoint_labels(headline, claim_ids, claims, endpoint_labels)
    hid = f"s{n}_headline"
    _add_textbox(
        slide,
        hid,
        headline,
        left=Inches(0.5),
        top=Inches(0.32),
        width=Inches(12.3),
        height=Inches(1.05),
        size_pt=28,
        bold=True,
        color=_NAVY,
    )
    entries.append(SlideMapEntry(slide=n, element_id=hid, text=headline, claim_ids=list(claim_ids)))

    body_top = Inches(1.5)
    used_width = Inches(12.3)
    has_figure = False
    if requires_visual or planned.figures:
        for fig in planned.figures:
            asset = asset_by_id.get(fig.asset_id)
            if asset is None or not Path(asset.path).is_file():
                continue
            pic = slide.shapes.add_picture(
                str(asset.path),
                Inches(8.0),
                Inches(1.55),
                Inches(4.7),
            )
            pic.name = f"s{n}_figure_{fig.asset_id}"
            cap = fig.caption or asset.caption
            if cap:
                cid = f"s{n}_caption_{fig.asset_id}"
                _add_textbox(
                    slide,
                    cid,
                    cap,
                    left=Inches(8.0),
                    top=Inches(6.2),
                    width=Inches(4.7),
                    height=Inches(0.55),
                    size_pt=12,
                    bold=False,
                    color=_BODY,
                )
                entries.append(
                    SlideMapEntry(slide=n, element_id=cid, text=cap, claim_ids=list(claim_ids))
                )
            used_width = Inches(7.2)
            has_figure = True
            break

    bullets = _body_bullets(planned, claim_ids, claims, endpoint_labels)
    for i, (text, ids) in enumerate(bullets):
        eid = f"s{n}_body_{i}"
        _add_textbox(
            slide,
            eid,
            text,
            left=Inches(0.5),
            top=body_top + Inches(0.55 * i),
            width=used_width,
            height=Inches(0.5),
            size_pt=16,
            bold=False,
            color=_BODY,
        )
        entries.append(SlideMapEntry(slide=n, element_id=eid, text=text, claim_ids=ids))

    notes = _notes_for_claims(claim_ids, claims) or planned.speaker_notes
    slide.notes_slide.notes_text_frame.text = notes
    _ = has_figure
    return entries, _pages_for_claims(claim_ids, claims)


def _body_bullets(
    planned: SlidePlanSlide,
    claim_ids: list[str],
    claims: dict[str, ClaimLedgerEntry],
    endpoint_labels: dict[EvidenceClass, str],
) -> list[tuple[str, list[str]]]:
    if planned.role == "references":
        bullets: list[tuple[str, list[str]]] = []
        for cid in claim_ids:
            entry = claims.get(cid)
            if entry is None:
                bullets.append((cid, [cid]))
                continue
            text = f"{cid} — {entry.text}"
            bullets.append((text, [cid]))
        return bullets[:20]

    bullets = []
    for cid in claim_ids:
        entry = claims.get(cid)
        text = entry.text if entry is not None else cid
        if entry is not None:
            text = _ensure_endpoint_labels(text, [cid], claims, endpoint_labels)
        bullets.append((text, [cid]))
    return bullets[:_MAX_BULLETS]


def _ensure_endpoint_labels(
    text: str,
    claim_ids: list[str],
    claims: dict[str, ClaimLedgerEntry],
    endpoint_labels: dict[EvidenceClass, str],
) -> str:
    out = text
    lower = out.lower()
    for cid in claim_ids:
        entry = claims.get(cid)
        if entry is None:
            continue
        label = endpoint_labels.get(entry.evidence_class)
        if label and label.lower() not in lower:
            out = f"{label}: {out}"
            lower = out.lower()
    return out


def _add_textbox(
    slide,
    name: str,
    text: str,
    *,
    left,
    top,
    width,
    height,
    size_pt: int,
    bold: bool,
    color: RGBColor,
) -> None:
    box = slide.shapes.add_textbox(left, top, width, height)
    box.name = name
    tf = box.text_frame
    tf.word_wrap = True
    tf.auto_size = None
    try:
        tf.vertical_anchor = MSO_ANCHOR.TOP
    except Exception:
        pass
    para = tf.paragraphs[0]
    para.alignment = PP_ALIGN.LEFT
    run = para.add_run()
    run.text = text
    run.font.size = Pt(size_pt)
    run.font.bold = bold
    run.font.name = _FONT
    run.font.color.rgb = color


def _clear_shapes(slide) -> None:
    tree = slide.shapes._spTree
    for child in list(tree):
        if child.tag in _SHAPE_TAGS:
            tree.remove(child)


def _remap_blips(src_slide, dest_slide, element) -> None:
    for blip in element.iter(qn("a:blip")):
        embed = blip.get(qn("r:embed"))
        if not embed:
            continue
        try:
            image_part = src_slide.part.related_part(embed)
        except (KeyError, ValueError):
            continue
        blob = getattr(image_part, "blob", None)
        if blob is None:
            continue
        _, new_rid = dest_slide.part.get_or_add_image_part(BytesIO(blob))
        blip.set(qn("r:embed"), new_rid)


def _copy_slide(src_prs, src_index: int, dest_prs):
    """Copy one slide (shapes + notes) from a prior deck. Never regenerate."""
    src = src_prs.slides[src_index]
    dest = dest_prs.slides.add_slide(dest_prs.slide_layouts[6])
    _clear_shapes(dest)
    for shape in src.shapes:
        new_el = deepcopy(shape.element)
        if shape.shape_type == MSO_SHAPE_TYPE.PICTURE:
            _remap_blips(src, dest, new_el)
        dest.shapes._spTree.append(new_el)
    if src.has_notes_slide:
        dest.notes_slide.notes_text_frame.text = src.notes_slide.notes_text_frame.text
    return dest


def _map_copied_slide(
    slide,
    slide_no: int,
    planned: SlidePlanSlide,
    claims: dict[str, ClaimLedgerEntry],
) -> list[SlideMapEntry]:
    entries: list[SlideMapEntry] = []
    fallback_ids = list(planned.claim_ids)
    n = 0
    for shape in slide.shapes:
        if not getattr(shape, "has_text_frame", False):
            continue
        text = shape.text_frame.text
        if not text.strip():
            continue
        eid = shape.name or f"s{slide_no}_locked_{n}"
        n += 1
        entries.append(
            SlideMapEntry(slide=slide_no, element_id=eid, text=text, claim_ids=list(fallback_ids))
        )
    notes = _notes_for_claims(fallback_ids, claims)
    if notes and slide.has_notes_slide:
        existing = slide.notes_slide.notes_text_frame.text.strip()
        if not existing:
            slide.notes_slide.notes_text_frame.text = notes
    return entries

