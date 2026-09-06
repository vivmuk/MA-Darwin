"""Slide planner — Venice Opus 4.8 emits SlidePlan JSON; never python-pptx."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from app.generation.skill_lineage import load_skill_bundle, load_skill_text
from app.llm_env import chat_text, llm_configured
from app.models.blueprint import Blueprint
from app.models.claim import ClaimLedger
from app.models.document import ExtractedAsset
from app.models.layout import LayoutSpec
from app.models.run import Brief
from app.models.slide import ChartSeries, HumanComment, SlideChart, SlidePlan, SlidePlanSlide
from app.paths import REPO_ROOT


def plan_slides(
    *,
    blueprint: Blueprint,
    ledger: ClaimLedger,
    brief: Brief,
    skill_version: str,
    one_off_comments: list[HumanComment] | None = None,
    prompt_path: Path | str | None = None,
) -> SlidePlan:
    """Produce ``slide_plan.json``: which claims/figures go on which slide."""
    if any(arg is None for arg in (blueprint, ledger, brief)):
        raise NotImplementedError

    prompt = _load_prompt(prompt_path)
    bundle = load_skill_bundle(skill_version)
    skill = bundle.text or load_skill_text(skill_version)
    payload = {
        "blueprint": json.loads(blueprint.model_dump_json()),
        "brief": json.loads(brief.model_dump_json()),
        "skill_version": skill_version,
        "skill_name": bundle.display_name(),
        "ledger": json.loads(ledger.model_dump_json()),
        "one_off_comments": [json.loads(c.model_dump_json()) for c in (one_off_comments or [])],
    }
    # Keep both Darwin (skills/v1) and sundai-powerpoint. 48k leaves house-rules intact.
    skill_block = skill[:48000] if skill else "(skill files missing on this host)"
    system = (
        prompt
        + "\n\nYou receive the active MA-Darwin skill AND the sundai-powerpoint "
        f"skill ({bundle.display_name()}). Honour 8-slide M2M structure, DRAFT "
        "marking, Arial + teal top rule, speaker notes on every slide, citation "
        "footers, dedicated safety slide, dense limitations, and editable-chart "
        "requirement on quantitative slides. Do not emit python-pptx or OOXML.\n\n"
        + skill_block
        + "\n\nReturn ONLY a SlidePlan JSON object. For quantitative slides "
        "(evidence / primary_endpoint / safety with ≥3 series or categories) "
        "include a `chart` object: {title, categories, series:[{name, values}]} "
        "using only numbers that appear in the ledger. Add `bullets`, `citation`, "
        "and full `speaker_notes` (how to open, what not to claim) on every slide."
    )
    if llm_configured():
        raw = chat_text(
            system=system,
            user=json.dumps(payload, ensure_ascii=False),
            max_tokens=8192,
            temperature=0,
        )
        parsed = _parse_plan_json(raw)
        if parsed is not None:
            parsed.skill_version = skill_version
            parsed.blueprint_id = parsed.blueprint_id or blueprint.id
            return _sanitize_plan(parsed, ledger, blueprint, skill_version)

    return _heuristic_plan(blueprint, ledger, brief, skill_version)


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
    dest = Path(output_path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(plan.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return dest


def _load_prompt(prompt_path: Path | str | None) -> str:
    if prompt_path is not None:
        path = Path(prompt_path)
    else:
        path = REPO_ROOT / "prompts" / "slide_plan.md"
        if not path.is_file():
            path = REPO_ROOT / "backend" / "prompts" / "slide_plan.md"
    if path.is_file():
        return path.read_text(encoding="utf-8")
    return "Assign ledger claims to blueprint roles. Return SlidePlan JSON only."


def _parse_plan_json(text: str) -> SlidePlan | None:
    if not (text or "").strip():
        return None
    blob = text.strip()
    fence = re.search(r"```(?:json)?\s*(\{.*\})\s*```", blob, re.DOTALL)
    if fence:
        blob = fence.group(1)
    else:
        start = blob.find("{")
        end = blob.rfind("}")
        if start >= 0 and end > start:
            blob = blob[start : end + 1]
    try:
        data: Any = json.loads(blob)
        return SlidePlan.model_validate(data)
    except (json.JSONDecodeError, ValueError):
        return None


def _sanitize_plan(
    plan: SlidePlan,
    ledger: ClaimLedger,
    blueprint: Blueprint,
    skill_version: str,
) -> SlidePlan:
    known = {entry.id for entry in ledger.entries}
    slides: list[SlidePlanSlide] = []
    for slide in plan.slides:
        claims = [cid for cid in slide.claim_ids if cid in known]
        chart = slide.chart
        if chart is not None and (not chart.categories or not chart.series):
            chart = None
        slides.append(
            slide.model_copy(
                update={
                    "claim_ids": claims,
                    "chart": chart,
                    "speaker_notes": slide.speaker_notes
                    or _default_notes(slide.role, claims, ledger),
                }
            )
        )
    if not slides:
        return _heuristic_plan(blueprint, ledger, Brief(), skill_version)
    return SlidePlan(blueprint_id=blueprint.id, skill_version=skill_version, slides=slides)


def _heuristic_plan(
    blueprint: Blueprint,
    ledger: ClaimLedger,
    brief: Brief,
    skill_version: str,
) -> SlidePlan:
    del brief
    entries = list(ledger.entries)
    by_type: dict[str, list[str]] = {}
    for entry in entries:
        kind = entry.evidence_class.value if hasattr(entry.evidence_class, "value") else str(entry.evidence_class)
        by_type.setdefault(kind, []).append(entry.id)
    used: set[str] = set()
    slides: list[SlidePlanSlide] = []
    for i, role in enumerate(blueprint.slides, start=1):
        allowed = {c.value if hasattr(c, "value") else str(c) for c in role.allowed_evidence_classes}
        picked: list[str] = []
        for kind in allowed:
            for cid in by_type.get(kind, []):
                if cid not in used and len(picked) < role.max_claims:
                    picked.append(cid)
                    used.add(cid)
        if not picked and entries:
            leftover = next((e.id for e in entries if e.id not in used), entries[0].id)
            picked = [leftover]
            used.add(leftover)
        headline = _headline_for(role.role, picked, ledger)
        chart = _chart_from_claims(role.role, picked, ledger)
        slides.append(
            SlidePlanSlide(
                slide=i,
                role=role.role,
                headline=headline,
                claim_ids=picked,
                bullets=_bullets_for(picked, ledger, role.max_claims),
                citation=_citation_for(picked, ledger),
                speaker_notes=_default_notes(role.role, picked, ledger),
                required_content_filled=list(role.required_content[:2]),
                chart=chart,
            )
        )
    return SlidePlan(blueprint_id=blueprint.id, skill_version=skill_version, slides=slides)


def _headline_for(role: str, claim_ids: list[str], ledger: ClaimLedger) -> str:
    claims = {e.id: e for e in ledger.entries}
    first = claims.get(claim_ids[0]) if claim_ids else None
    if role == "title":
        return "DRAFT — Medical-to-medical scientific exchange"
    if role == "references":
        return "References"
    if first is not None and first.text:
        text = first.text.strip()
        return text[:110] + ("…" if len(text) > 110 else "")
    return role.replace("_", " ").title()


def _bullets_for(claim_ids: list[str], ledger: ClaimLedger, limit: int) -> list[str]:
    claims = {e.id: e for e in ledger.entries}
    out: list[str] = []
    for cid in claim_ids[:limit]:
        entry = claims.get(cid)
        if entry is None:
            continue
        text = entry.text.strip()
        if text:
            out.append(text[:160])
    return out


def _citation_for(claim_ids: list[str], ledger: ClaimLedger) -> str:
    claims = {e.id: e for e in ledger.entries}
    bits = []
    for cid in claim_ids:
        entry = claims.get(cid)
        if entry is not None:
            bits.append(f"{cid} p.{entry.page}")
    return " · ".join(bits)


def _default_notes(role: str, claim_ids: list[str], ledger: ClaimLedger) -> str:
    cites = _citation_for(claim_ids, ledger)
    opener = {
        "title": "Open as DRAFT scientific exchange. Do not claim compliance or approval.",
        "safety": "Give safety the same prominence as efficacy. Do not bury AE rates.",
        "limitations_relevance": "State what remains unknown. Do not invent missing CIs.",
        "primary_endpoint": "Read the finding, not a conclusion. Name design and N.",
    }.get(role, "Stay inside the source PDF. No promotional language.")
    return f"{opener} {cites}".strip()


def _chart_from_claims(role: str, claim_ids: list[str], ledger: ClaimLedger) -> SlideChart | None:
    if role not in {"primary_endpoint", "key_secondary", "safety"}:
        return None
    claims = {e.id: e for e in ledger.entries}
    cats: list[str] = []
    vals: list[float] = []
    for cid in claim_ids:
        entry = claims.get(cid)
        if entry is None:
            continue
        for number in entry.numbers:
            raw = getattr(number, "value", None)
            if raw is None:
                continue
            try:
                vals.append(float(raw))
                cats.append(cid)
            except (TypeError, ValueError):
                continue
            if len(cats) >= 4:
                break
        if len(cats) >= 4:
            break
    if len(cats) < 3:
        return None
    return SlideChart(
        title="Source values from the claim ledger",
        categories=cats,
        series=[ChartSeries(name="Reported", values=vals)],
    )
