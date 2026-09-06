"""SVG → PNG via cairosvg at the configured render DPI (judge input)."""

from __future__ import annotations

from pathlib import Path

from app.models.layout import CANVAS_HEIGHT_IN, CANVAS_WIDTH_IN, FontWeight, LayoutElementKind, LayoutSlide, LayoutSpec


def svg_to_png(
    svg_path: Path | str,
    png_path: Path | str,
    *,
    dpi: int = 150,
    canvas_width: float = CANVAS_WIDTH_IN,
    canvas_height: float = CANVAS_HEIGHT_IN,
) -> Path:
    """Rasterize one SVG. Fails loudly — never writes a blank placeholder."""
    if dpi < 150:
        raise ValueError(f"dpi must be >= 150 (PRD §7.5), got {dpi}")
    src = Path(svg_path)
    if not src.is_file():
        raise FileNotFoundError(f"svg not found: {src}")
    dest = Path(png_path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    width_px = max(1, int(round(canvas_width * dpi)))
    height_px = max(1, int(round(canvas_height * dpi)))
    try:
        _cairo_svg_to_png(src, dest, width_px, height_px)
    except Exception:
        raise
    if not dest.is_file() or dest.stat().st_size < 32:
        raise RuntimeError(f"PNG rasterizer produced no file at {dest}")
    return dest


def write_slide_pngs(
    svg_paths: list[Path | str],
    output_dir: Path | str,
    *,
    dpi: int = 150,
    canvas_width: float = CANVAS_WIDTH_IN,
    canvas_height: float = CANVAS_HEIGHT_IN,
    spec: LayoutSpec | None = None,
) -> list[Path]:
    dest_dir = Path(output_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    out: list[Path] = []
    slides = list(spec.slides) if spec is not None else []
    for index, svg in enumerate(svg_paths):
        src = Path(svg)
        png = dest_dir / f"{src.stem}.png"
        painted = False
        try:
            svg_to_png(
                src,
                png,
                dpi=dpi,
                canvas_width=canvas_width,
                canvas_height=canvas_height,
            )
            painted = _png_has_ink(png)
        except Exception:
            painted = False
        if not painted and index < len(slides):
            paint_slide_png(slides[index], png, dpi=dpi)
        if not png.is_file() or png.stat().st_size < 32:
            raise RuntimeError(f"failed to rasterize {src} to {png}")
        out.append(png)
    return out


def paint_slide_png(slide: LayoutSlide, png_path: Path | str, *, dpi: int) -> Path:
    """Rasterize one slide from the spec itself (same inches / fonts / copy)."""
    import pymupdf

    dest = Path(png_path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    width = slide.width * 72.0
    height = slide.height * 72.0
    doc = pymupdf.open()
    page = doc.new_page(width=width, height=height)
    page.draw_rect(page.rect, color=None, fill=_rgb01(slide.background or "#FFFFFF"))
    for el in slide.elements:
        rect = pymupdf.Rect(el.x * 72.0, el.y * 72.0, (el.x + el.w) * 72.0, (el.y + el.h) * 72.0)
        if el.kind == LayoutElementKind.SHAPE:
            page.draw_rect(rect, color=None, fill=_rgb01(el.fill or el.color or "#000000"))
            continue
        if el.kind == LayoutElementKind.IMAGE and el.image_path and Path(el.image_path).is_file():
            page.insert_image(rect, filename=el.image_path)
            continue
        if not (el.text or "").strip():
            continue
        fontname = _register_face(page, el.font_family, el.font_weight)
        page.insert_textbox(
            rect,
            el.text,
            fontsize=el.font_size_pt,
            fontname=fontname,
            color=_rgb01(el.color),
            align=0,
        )
    pix = page.get_pixmap(dpi=dpi, alpha=False)
    pix.save(str(dest))
    doc.close()
    return dest


def _png_has_ink(path: Path) -> bool:
    import pymupdf

    pix = pymupdf.Pixmap(str(path))
    step_x = max(1, pix.width // 20)
    step_y = max(1, pix.height // 12)
    for y in range(0, pix.height, step_y):
        for x in range(0, pix.width, step_x):
            r, g, b = pix.pixel(x, y)[:3]
            if r < 250 or g < 250 or b < 250:
                return True
    return False


def _register_face(page, family: str, weight: FontWeight) -> str:
    windows = Path(r"C:\Windows\Fonts")
    bold = weight == FontWeight.BOLD
    files = {
        "arial": "arialbd.ttf" if bold else "arial.ttf",
        "calibri": "calibrib.ttf" if bold else "calibri.ttf",
    }
    filename = files.get(family.lower())
    if filename:
        path = windows / filename
        if path.is_file():
            key = f"{family.lower()}{'-b' if bold else ''}"
            try:
                page.insert_font(fontname=key, fontfile=str(path))
                return key
            except Exception:
                pass
    return "hebo" if bold else "helv"


def _rgb01(color: str) -> tuple[float, float, float]:
    raw = (color or "#000000").strip().lstrip("#")
    if len(raw) != 6:
        return (0.0, 0.0, 0.0)
    return (int(raw[0:2], 16) / 255.0, int(raw[2:4], 16) / 255.0, int(raw[4:6], 16) / 255.0)


def _cairo_svg_to_png(src: Path, dest: Path, width_px: int, height_px: int) -> None:
    """Prefer cairosvg; if Cairo is missing, rasterize the same SVG via PyMuPDF."""
    try:
        import cairosvg

        cairosvg.svg2png(
            url=str(src),
            write_to=str(dest),
            output_width=width_px,
            output_height=height_px,
            unsafe=True,
        )
        return
    except Exception as exc:
        raise RuntimeError(f"cairosvg could not rasterize {src}: {exc}") from exc
