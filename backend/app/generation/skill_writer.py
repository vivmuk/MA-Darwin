"""Write deck.pptx using sundai-powerpoint capability — editable charts first."""

from __future__ import annotations

import importlib.util
import io
import sys
from collections.abc import Callable
from pathlib import Path
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt

from app.generation.skill_lineage import scripts_dir
from app.models.claim import ClaimLedger
from app.models.document import ExtractedAsset
from app.models.layout import LayoutSpec
from app.models.slide import SlideChart, SlidePlan, SlidePlanSlide

PALETTE = {
    "navy": "12283A",
    "slate": "5B6B79",
    "teal": "0E7C7B",
    "muted_teal": "5B9A98",
    "gold": "C89B3C",
    "oxblood": "8C2F39",
    "cloud": "E8ECEF",
    "white": "FFFFFF",
}

CANVAS_W = 13.333
CANVAS_H = 7.5


def write_skill_pptx(
    plan: SlidePlan,
    ledger: ClaimLedger,
    output_path: Path | str,
    *,
    assets: list[ExtractedAsset] | None = None,
    prior_spec: LayoutSpec | None = None,
    locked_slides: list[int] | None = None,
    on_slide: Callable[..., None] | None = None,
) -> Path:
    """Build a consulting-grade M2M deck. Venice never writes this file."""
    dest = Path(output_path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    prs = Presentation()
    prs.slide_width = Inches(CANVAS_W)
    prs.slide_height = Inches(CANVAS_H)
    claims = {entry.id: entry for entry in ledger.entries}
    assets_by_id = {a.id: a for a in (assets or [])}
    locked = set(locked_slides or [])
    prior_by_slide = {s.slide: s for s in (prior_spec.slides if prior_spec else [])}

    for planned in plan.slides:
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        if planned.slide in locked and planned.slide in prior_by_slide:
            _paint_from_prior(slide, planned, prior_by_slide[planned.slide], claims)
        else:
            _paint_slide(slide, planned, claims, assets_by_id)
        if on_slide is not None:
            on_slide(planned)
    prs.save(str(dest))
    _try_validate(dest)
    return dest


def _paint_slide(slide, planned: SlidePlanSlide, claims: dict, assets_by_id: dict[str, ExtractedAsset]) -> None:
    _bar(slide, PALETTE["teal"] if planned.role != "safety" else PALETTE["oxblood"])
    if planned.role == "title":
        _textbox(slide, 0.5, 0.28, 2.2, 0.32, "DRAFT", size=11, bold=True, color=PALETTE["oxblood"])
    else:
        eyebrow = (planned.role or "").replace("_", " ").upper()
        _textbox(slide, 0.5, 0.22, 8.0, 0.28, eyebrow, size=11, bold=True, color=PALETTE["teal"])
    _textbox(slide, 0.5, 0.55, 12.3, 1.05, planned.headline, size=26, bold=True, color=PALETTE["navy"])

    body_top = 1.75
    if planned.chart and planned.chart.categories and planned.chart.series:
        notes_extra = _add_chart(slide, planned.chart)
        body_top = 6.05
        bullets = planned.bullets[:3]
        if bullets:
            _textbox(slide, 0.5, body_top, 12.3, 0.7, "\n".join(f"• {b}" for b in bullets), size=12, color=PALETTE["slate"])
    else:
        text = planned.body or "\n".join(f"• {b}" for b in planned.bullets)
        if not text:
            text = _fallback_body(planned, claims)
        _textbox(slide, 0.5, 1.75, 12.3, 4.6, text, size=16, color=PALETTE["navy"])
        notes_extra = ""
        for fig in planned.figures[:1]:
            asset = assets_by_id.get(fig.asset_id)
            if asset and asset.path and Path(asset.path).is_file():
                slide.shapes.add_picture(asset.path, Inches(8.6), Inches(2.0), Inches(4.2), Inches(3.6))

    footer = planned.citation or _citation(planned, claims)
    if planned.role == "title":
        footer = (footer + "  ·  DRAFT for qualified medical review").strip(" ·")
    _textbox(slide, 0.5, 7.05, 12.3, 0.32, footer, size=10, color=PALETTE["slate"])

    notes = planned.speaker_notes or _citation(planned, claims)
    if notes_extra:
        notes = f"{notes}\n{notes_extra}"
    if planned.role == "title" and "DRAFT" not in notes.upper():
        notes = f"{notes}\nKeep DRAFT on the title slide. Do not call this compliant."
    slide.notes_slide.notes_text_frame.text = notes


def _paint_from_prior(slide, planned: SlidePlanSlide, prior, claims: dict) -> None:
    """Locked slides keep prior copy; still apply skill chrome."""
    _bar(slide, PALETTE["teal"])
    texts = [el.text for el in prior.elements if getattr(el, "text", None)]
    headline = texts[0] if texts else planned.headline
    body = "\n".join(texts[1:]) if len(texts) > 1 else ""
    _textbox(slide, 0.5, 0.55, 12.3, 1.05, headline, size=26, bold=True, color=PALETTE["navy"])
    if body:
        _textbox(slide, 0.5, 1.75, 12.3, 4.6, body, size=16, color=PALETTE["navy"])
    slide.notes_slide.notes_text_frame.text = planned.speaker_notes or _citation(planned, claims)


def _add_chart(slide, chart: SlideChart) -> str:
    """Native OOXML chart first; matplotlib PNG only if that hard-fails."""
    series = {item.name: list(item.values) for item in chart.series}
    try:
        add_fn = _load_chart_fn()
        add_fn(
            slide,
            chart.categories,
            series,
            left=Inches(0.5),
            top=Inches(1.7),
            width=Inches(12.3),
            height=Inches(4.15),
        )
        return ""
    except Exception as exc:
        path = _matplotlib_fallback(chart)
        if path is None:
            _textbox(
                slide,
                0.5,
                1.8,
                12.3,
                1.2,
                f"Chart unavailable ({exc}). Values remain in speaker notes.",
                size=14,
                color=PALETTE["oxblood"],
            )
            return f"Raster fallback failed: native editable chart unavailable because {exc}."
        slide.shapes.add_picture(str(path), Inches(0.5), Inches(1.7), Inches(12.3), Inches(4.15))
        return (
            "Raster fallback: native editable chart unavailable because "
            f"{exc}. PNG is not a substitute when OOXML charts work."
        )


def _load_chart_fn():
    path = scripts_dir() / "add_editable_chart.py"
    spec = importlib.util.spec_from_file_location("sundai_add_editable_chart", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.add_clustered_column_chart


def _matplotlib_fallback(chart: SlideChart) -> Path | None:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
    except Exception:
        return None
    fig, ax = plt.subplots(figsize=(12.3, 4.15), dpi=200)
    x = np.arange(len(chart.categories))
    width = 0.8 / max(len(chart.series), 1)
    colors = [PALETTE["oxblood"], PALETTE["teal"], PALETTE["muted_teal"], PALETTE["navy"], PALETTE["slate"]]
    for i, series in enumerate(chart.series):
        ax.bar(x + i * width, series.values, width, label=series.name, color="#" + colors[i % len(colors)])
    ax.set_xticks(x + width * (len(chart.series) - 1) / 2)
    ax.set_xticklabels(chart.categories, fontsize=8)
    ax.legend(fontsize=8)
    ax.set_title(chart.title or "")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    buf = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format="png")
    plt.close(fig)
    tmp = Path(__file__).resolve().parents[3] / "runs" / "_chart_fallback.png"
    tmp.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_bytes(buf.getvalue())
    return tmp


def _try_validate(deck: Path) -> None:
    validator = scripts_dir() / "office" / "validate.py"
    if not validator.is_file():
        return
    try:
        import subprocess

        subprocess.run(
            [sys.executable, str(validator), str(deck)],
            check=False,
            capture_output=True,
            timeout=30,
        )
    except Exception:
        return


def _bar(slide, hex6: str) -> None:
    shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(CANVAS_W), Inches(0.09))
    shape.fill.solid()
    shape.fill.fore_color.rgb = _rgb(hex6)
    shape.line.fill.background()


def _textbox(
    slide,
    x: float,
    y: float,
    w: float,
    h: float,
    text: str,
    *,
    size: int,
    bold: bool = False,
    color: str = "12283A",
) -> None:
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    try:
        tf.vertical_anchor = MSO_ANCHOR.TOP
    except Exception:
        pass
    _disable_autofit(tf)
    para = tf.paragraphs[0]
    para.alignment = PP_ALIGN.LEFT
    run = para.add_run()
    run.text = text
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.name = "Arial"
    run.font.color.rgb = _rgb(color)


def _disable_autofit(text_frame) -> None:
    body = text_frame._txBody
    pr = body.find(qn("a:bodyPr"))
    if pr is None:
        return
    for tag in ("a:spAutoFit", "a:normAutofit", "a:noAutofit"):
        node = pr.find(qn(tag))
        if node is not None:
            pr.remove(node)
    pr.append(pr.makeelement(qn("a:noAutofit"), {}))


def _rgb(hex6: str) -> RGBColor:
    raw = hex6.strip().lstrip("#")
    if len(raw) != 6:
        raw = "000000"
    return RGBColor(int(raw[0:2], 16), int(raw[2:4], 16), int(raw[4:6], 16))


def _citation(planned: SlidePlanSlide, claims: dict) -> str:
    bits = []
    for cid in planned.claim_ids:
        entry = claims.get(cid)
        if entry is not None:
            bits.append(f"{cid} p.{entry.page}")
    return " · ".join(bits)


def _fallback_body(planned: SlidePlanSlide, claims: dict) -> str:
    lines = []
    for cid in planned.claim_ids:
        entry = claims.get(cid)
        if entry is not None and entry.text:
            lines.append(f"• {entry.text}")
    return "\n".join(lines) or planned.headline
