"""LayoutSpec → deck.pdf via reportlab (export bundle). No LibreOffice."""

from __future__ import annotations

from pathlib import Path

from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from app.models.layout import FontWeight, LayoutElement, LayoutElementKind, LayoutSlide, LayoutSpec
from app.rendering.text_metrics import LINE_HEIGHT, text_block_size

_PT_PER_IN = 72.0
_REGISTERED: set[str] = set()


def write_pdf(spec: LayoutSpec, output_path: Path | str) -> Path:
    dest = Path(output_path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    width = spec.canvas_width * _PT_PER_IN
    height = spec.canvas_height * _PT_PER_IN
    c = canvas.Canvas(str(dest), pagesize=(width, height))
    for slide in spec.slides:
        _draw_slide(c, slide, page_h=height)
        c.showPage()
    c.save()
    if not dest.is_file():
        raise RuntimeError(f"reportlab did not write {dest}")
    return dest


def _draw_slide(c: canvas.Canvas, slide: LayoutSlide, *, page_h: float) -> None:
    c.setFillColor(HexColor(slide.background or "#FFFFFF"))
    c.rect(0, 0, slide.width * _PT_PER_IN, slide.height * _PT_PER_IN, fill=1, stroke=0)
    for el in slide.elements:
        if el.kind == LayoutElementKind.IMAGE and el.image_path and Path(el.image_path).is_file():
            x, y, w, h = _box(el, page_h)
            c.drawImage(el.image_path, x, y, width=w, height=h, preserveAspectRatio=False, mask="auto")
            continue
        if el.kind == LayoutElementKind.SHAPE:
            x, y, w, h = _box(el, page_h)
            c.setFillColor(HexColor(el.fill or el.color or "#000000"))
            c.rect(x, y, w, h, fill=1, stroke=0)
            continue
        _draw_text(c, el, page_h)


def _draw_text(c: canvas.Canvas, el: LayoutElement, page_h: float) -> None:
    _, _, lines = text_block_size(el)
    font_name = _font(el.font_family, el.font_weight)
    c.setFillColor(HexColor(el.color or "#000000"))
    c.setFont(font_name, el.font_size_pt)
    size_in = el.font_size_pt / _PT_PER_IN
    for i, line in enumerate(lines):
        y_top = el.y + size_in * 0.85 + i * size_in * LINE_HEIGHT
        x_left = el.x
        if el.alignment.value == "center":
            x_left = el.x + el.w / 2
            c.drawCentredString(x_left * _PT_PER_IN, page_h - y_top * _PT_PER_IN, line)
        elif el.alignment.value == "right":
            x_left = el.x + el.w
            c.drawRightString(x_left * _PT_PER_IN, page_h - y_top * _PT_PER_IN, line)
        else:
            c.drawString(x_left * _PT_PER_IN, page_h - y_top * _PT_PER_IN, line)


def _box(el: LayoutElement, page_h: float) -> tuple[float, float, float, float]:
    w = el.w * _PT_PER_IN
    h = el.h * _PT_PER_IN
    x = el.x * _PT_PER_IN
    y = page_h - (el.y * _PT_PER_IN) - h
    return x, y, w, h


def _font(family: str, weight: FontWeight) -> str:
    bold = weight == FontWeight.BOLD
    key = f"{family}-{'Bold' if bold else 'Regular'}"
    if key in _REGISTERED:
        return key
    windows = Path(r"C:\Windows\Fonts")
    candidates = []
    if family.lower() == "arial":
        candidates = ["arialbd.ttf" if bold else "arial.ttf"]
    elif family.lower() == "calibri":
        candidates = ["calibrib.ttf" if bold else "calibri.ttf"]
    for name in candidates:
        path = windows / name
        if path.is_file():
            try:
                pdfmetrics.registerFont(TTFont(key, str(path)))
                _REGISTERED.add(key)
                return key
            except Exception:
                break
    return "Times-Bold" if bold else "Times-Roman"
