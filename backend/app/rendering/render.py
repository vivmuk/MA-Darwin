"""LayoutSpec → SVG → PNG + PDF. No LibreOffice, no placeholder images."""

from __future__ import annotations

from pathlib import Path

from app.export.pdf_writer import write_pdf
from app.models.layout import LayoutSpec
from app.models.run import RenderResult
from app.rendering.png_renderer import write_slide_pngs
from app.rendering.svg_renderer import write_slide_svgs


def render_deck(
    pptx_path: Path | str | None = None,
    output_dir: Path | str | None = None,
    *,
    layout_spec: LayoutSpec | None = None,
    dpi: int = 150,
) -> RenderResult:
    """Render from ``LayoutSpec``. ``pptx_path`` is ignored (kept for call-site compat)."""
    del pptx_path
    if layout_spec is None:
        raise NotImplementedError
    if output_dir is None:
        raise ValueError("output_dir is required")
    if dpi < 150:
        raise ValueError(f"dpi must be >= 150 (PRD §7.5), got {dpi}")

    out = Path(output_dir)
    slides_dir = out / "slides"
    svg_paths = write_slide_svgs(layout_spec, slides_dir)
    png_paths = write_slide_pngs(
        svg_paths,
        slides_dir,
        dpi=dpi,
        canvas_width=layout_spec.canvas_width,
        canvas_height=layout_spec.canvas_height,
        spec=layout_spec,
    )
    pdf_path = write_pdf(layout_spec, out / "deck.pdf")
    return RenderResult(
        pdf_path=str(pdf_path),
        slide_images=[str(p) for p in png_paths],
        slide_svgs=[str(p) for p in svg_paths],
        dpi=dpi,
    )


def pdf_to_pngs(pdf_path: Path | str, output_dir: Path | str, *, dpi: int = 150) -> list[Path]:
    """Kept for tests that rasterize an existing PDF. Not used by the live pipeline."""
    import pymupdf

    pdf = Path(pdf_path)
    if not pdf.is_file():
        raise FileNotFoundError(f"pdf not found: {pdf}")
    if dpi < 150:
        raise ValueError(f"dpi must be >= 150 (PRD §7.5), got {dpi}")
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    doc = pymupdf.open(pdf)
    paths: list[Path] = []
    try:
        if doc.page_count < 1:
            raise RuntimeError(f"PDF has no pages: {pdf}")
        for index in range(doc.page_count):
            page = doc.load_page(index)
            pix = page.get_pixmap(dpi=dpi)
            dest = out_dir / f"slide_{index + 1:02d}.png"
            pix.save(str(dest))
            paths.append(dest)
    finally:
        doc.close()
    return paths
