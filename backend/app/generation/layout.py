"""Compose a LayoutSpec from a SlidePlan. Explicit inches only — no autofit."""

from __future__ import annotations

from pathlib import Path

from app.models.blueprint import Blueprint
from app.models.claim import ClaimLedger, ClaimLedgerEntry, EvidenceClass
from app.models.document import ExtractedAsset
from app.models.layout import (
    CANVAS_HEIGHT_IN,
    CANVAS_WIDTH_IN,
    FontWeight,
    LayoutElement,
    LayoutElementKind,
    LayoutSlide,
    LayoutSpec,
    TextAlign,
)
from app.models.slide import SlidePlan, SlidePlanSlide
from app.paths import CONFIG_DIR

_NAVY = "#1B2A4A"
_BODY = "#2C3E50"
_FONT = "Arial"
_MAX_BULLETS = 6

_ENDPOINT_LABELS = {
    EvidenceClass.SECONDARY_ENDPOINT: "Secondary endpoint",
    EvidenceClass.EXPLORATORY: "Exploratory",
    EvidenceClass.POST_HOC: "Post hoc",
}


def compose_layout_spec(
    *,
    plan: SlidePlan,
    blueprint: Blueprint,
    ledger: ClaimLedger,
    assets: list[ExtractedAsset] | None = None,
    prior_spec: LayoutSpec | None = None,
    locked_slides: list[int] | None = None,
) -> LayoutSpec:
    """Emit the layout spec the planner/generator owns. Coordinates are inches."""
    claims = {entry.id: entry for entry in ledger.entries}
    role_by_index = {i + 1: spec.role for i, spec in enumerate(blueprint.slides)}
    spec_by_role = {spec.role: spec for spec in blueprint.slides}
    asset_by_id = {a.id: a for a in (assets or [])}
    labels = _endpoint_labels()
    locked = set(locked_slides or [])
    prior_by_n = {s.slide: s for s in (prior_spec.slides if prior_spec else [])}

    slides: list[LayoutSlide] = []
    for planned in plan.slides:
        if planned.slide in locked and planned.slide in prior_by_n:
            slides.append(prior_by_n[planned.slide].model_copy(deep=True))
            continue
        role = planned.role or role_by_index.get(planned.slide, "")
        spec = spec_by_role.get(role)
        max_claims = spec.max_claims if spec else _MAX_BULLETS
        requires_visual = bool(spec.requires_visual) if spec else False
        slides.append(
            _compose_slide(
                planned,
                claims,
                asset_by_id,
                max_claims=max_claims,
                requires_visual=requires_visual,
                endpoint_labels=labels,
            )
        )
    return LayoutSpec(canvas_width=CANVAS_WIDTH_IN, canvas_height=CANVAS_HEIGHT_IN, slides=slides)


def load_layout_spec(path: Path | str) -> LayoutSpec:
    return LayoutSpec.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_layout_spec(spec: LayoutSpec, path: Path | str) -> Path:
    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(spec.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return dest


def _endpoint_labels() -> dict[EvidenceClass, str]:
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


def _claim_ids(planned: SlidePlanSlide, claims: dict[str, ClaimLedgerEntry], max_claims: int) -> list[str]:
    if planned.role == "references":
        ids = [cid for cid in planned.claim_ids if cid in claims]
        return ids or list(planned.claim_ids)
    ids = [cid for cid in planned.claim_ids if cid in claims][:max_claims]
    if not ids:
        ids = list(planned.claim_ids[:max_claims])
    return ids


def _notes(claim_ids: list[str], claims: dict[str, ClaimLedgerEntry], fallback: str) -> str:
    parts = []
    for cid in claim_ids:
        entry = claims.get(cid)
        if entry is None:
            continue
        parts.append(f"{cid} p.{entry.page}")
    return "; ".join(parts) or fallback


def _label(text: str, claim_ids: list[str], claims: dict[str, ClaimLedgerEntry], labels: dict[EvidenceClass, str]) -> str:
    out = text
    lower = out.lower()
    for cid in claim_ids:
        entry = claims.get(cid)
        if entry is None:
            continue
        label = labels.get(entry.evidence_class)
        if label and label.lower() not in lower:
            out = f"{label}: {out}"
            lower = out.lower()
    return out


def _reference_bullets(
    claim_ids: list[str],
    claims: dict[str, ClaimLedgerEntry],
) -> list[tuple[str, list[str]]]:
    """Group citations by page so every cited id can appear on the references slide."""
    by_page: dict[int, list[str]] = {}
    for cid in claim_ids:
        entry = claims.get(cid)
        page = entry.page if entry is not None else 0
        by_page.setdefault(page, []).append(cid)
    out: list[tuple[str, list[str]]] = []
    for page in sorted(by_page):
        ids = by_page[page]
        sample = claims.get(ids[0])
        snippet = f" — {sample.text[:90]}" if sample is not None else ""
        out.append((f"p.{page}: {'; '.join(ids)}{snippet}", ids))
    return out


def _bullets(
    planned: SlidePlanSlide,
    claim_ids: list[str],
    claims: dict[str, ClaimLedgerEntry],
    labels: dict[EvidenceClass, str],
) -> list[tuple[str, list[str]]]:
    if planned.role == "references":
        return _reference_bullets(claim_ids, claims)
    out: list[tuple[str, list[str]]] = []
    for cid in claim_ids:
        entry = claims.get(cid)
        text = entry.text if entry is not None else cid
        if entry is not None:
            text = _label(text, [cid], claims, labels)
        out.append((text, [cid]))
    return out[:_MAX_BULLETS]


def _compose_slide(
    planned: SlidePlanSlide,
    claims: dict[str, ClaimLedgerEntry],
    asset_by_id: dict[str, ExtractedAsset],
    *,
    max_claims: int,
    requires_visual: bool,
    endpoint_labels: dict[EvidenceClass, str],
) -> LayoutSlide:
    n = planned.slide
    claim_ids = _claim_ids(planned, claims, max_claims)
    elements: list[LayoutElement] = []

    headline = planned.headline.strip() or (
        claims[claim_ids[0]].text if claim_ids and claim_ids[0] in claims else planned.role
    )
    headline = _label(headline, claim_ids, claims, endpoint_labels)
    elements.append(
        LayoutElement(
            id=f"s{n}_headline",
            kind=LayoutElementKind.TEXT,
            x=0.5,
            y=0.32,
            w=12.3,
            h=1.05,
            font_family=_FONT,
            font_size_pt=28,
            font_weight=FontWeight.BOLD,
            color=_NAVY,
            alignment=TextAlign.LEFT,
            text=headline,
            claim_ids=list(claim_ids[:1]),
        )
    )

    body_width = 12.3
    if requires_visual or planned.figures:
        for fig in planned.figures:
            asset = asset_by_id.get(fig.asset_id)
            if asset is None or not Path(asset.path).is_file():
                continue
            elements.append(
                LayoutElement(
                    id=f"s{n}_figure_{fig.asset_id}",
                    kind=LayoutElementKind.IMAGE,
                    x=8.0,
                    y=1.55,
                    w=4.7,
                    h=4.4,
                    image_path=str(Path(asset.path)),
                    claim_ids=list(claim_ids[:1]),
                )
            )
            cap = fig.caption or asset.caption
            if cap:
                elements.append(
                    LayoutElement(
                        id=f"s{n}_caption_{fig.asset_id}",
                        kind=LayoutElementKind.TEXT,
                        x=8.0,
                        y=6.1,
                        w=4.7,
                        h=0.7,
                        font_family=_FONT,
                        font_size_pt=14,
                        font_weight=FontWeight.NORMAL,
                        color=_BODY,
                        text=cap,
                        claim_ids=list(claim_ids[:1]),
                    )
                )
            body_width = 7.2
            break

    for i, (text, ids) in enumerate(_bullets(planned, claim_ids, claims, endpoint_labels)):
        elements.append(
            LayoutElement(
                id=f"s{n}_body_{i}",
                kind=LayoutElementKind.TEXT,
                x=0.5,
                y=1.5 + 0.55 * i,
                w=body_width,
                h=0.5,
                font_family=_FONT,
                font_size_pt=16,
                font_weight=FontWeight.NORMAL,
                color=_BODY,
                text=text,
                claim_ids=ids,
            )
        )

    return LayoutSlide(
        slide=n,
        role=planned.role,
        width=CANVAS_WIDTH_IN,
        height=CANVAS_HEIGHT_IN,
        elements=elements,
        speaker_notes=_notes(claim_ids, claims, planned.speaker_notes),
    )
