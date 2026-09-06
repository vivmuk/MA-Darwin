"""LayoutSpec → one SVG per slide. Deterministic, no external processes."""

from __future__ import annotations

import html
from pathlib import Path

from app.models.layout import LayoutElement, LayoutElementKind, LayoutSlide, LayoutSpec, TextAlign
from app.rendering.text_metrics import LINE_HEIGHT, text_block_size

_PT = 72.0


def render_slide_svg(slide: LayoutSlide) -> str:
    """Return an SVG whose user units are points (72 / inch) — 1:1 with LayoutSpec inches."""
    w = slide.width * _PT
    h = slide.height * _PT
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'width="{slide.width}in" height="{slide.height}in" viewBox="0 0 {w} {h}">',
        f'<rect width="{w}" height="{h}" fill="{_esc(slide.background)}"/>',
    ]
    for el in slide.elements:
        parts.append(_element_svg(el))
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def write_slide_svgs(spec: LayoutSpec, output_dir: Path | str) -> list[Path]:
    dest = Path(output_dir)
    dest.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for slide in spec.slides:
        path = dest / f"slide_{slide.slide:02d}.svg"
        path.write_text(render_slide_svg(slide), encoding="utf-8")
        paths.append(path)
    return paths


def _esc(value: str) -> str:
    return html.escape(value or "", quote=True)


def _element_svg(el: LayoutElement) -> str:
    if el.kind == LayoutElementKind.SHAPE:
        fill = el.fill or el.color
        return (
            f'<rect x="{el.x * _PT}" y="{el.y * _PT}" width="{el.w * _PT}" height="{el.h * _PT}" '
            f'fill="{_esc(fill)}" data-id="{_esc(el.id)}"/>'
        )
    if el.kind == LayoutElementKind.IMAGE and el.image_path:
        href = Path(el.image_path).resolve().as_posix()
        return (
            f'<image x="{el.x * _PT}" y="{el.y * _PT}" width="{el.w * _PT}" height="{el.h * _PT}" '
            f'preserveAspectRatio="none" href="file:///{href}" data-id="{_esc(el.id)}"/>'
        )
    return _text_svg(el)


def _text_svg(el: LayoutElement) -> str:
    _, _, lines = text_block_size(el)
    weight = "700" if el.font_weight.value == "bold" else "400"
    if el.alignment == TextAlign.CENTER:
        anchor, x = "middle", (el.x + el.w / 2) * _PT
    elif el.alignment == TextAlign.RIGHT:
        anchor, x = "end", (el.x + el.w) * _PT
    else:
        anchor, x = "start", el.x * _PT
    chunks = []
    for i, line in enumerate(lines):
        y = (el.y + (el.font_size_pt / 72.0) * (0.85 + i * LINE_HEIGHT)) * _PT
        chunks.append(
            f'<text x="{x}" y="{y}" font-family="{_esc(el.font_family)}" '
            f'font-size="{el.font_size_pt}" font-weight="{weight}" fill="{_esc(el.color)}" '
            f'text-anchor="{anchor}" data-id="{_esc(el.id)}">{_esc(line)}</text>'
        )
    return "\n".join(chunks)
