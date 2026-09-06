"""Render pipeline and font-check tests (no live module outputs)."""

from __future__ import annotations

from pathlib import Path

import pymupdf
import pytest
import yaml

from app.rendering.font_check import check_required_fonts, list_installed_fonts, load_required_fonts
from app.models.layout import FontWeight, LayoutElement, LayoutElementKind, LayoutSlide, LayoutSpec
from app.rendering.render import pdf_to_pngs, render_deck
from app.rendering.svg_renderer import render_slide_svg


def test_load_required_fonts_from_config() -> None:
    names = load_required_fonts()
    assert "Arial" in names
    assert "Calibri" in names


def test_required_fonts_are_installed_or_raise() -> None:
    # Arial + Calibri are required; on this Windows render host they must exist.
    installed = {n.lower() for n in list_installed_fonts()}
    assert any(n.startswith("arial") for n in installed)
    check_required_fonts()


def test_check_required_fonts_raises_loudly(tmp_path: Path) -> None:
    cfg = tmp_path / "fonts.yaml"
    cfg.write_text(
        yaml.safe_dump({"required_fonts": ["DefinitelyMissingFont_MADarwin_XYZ"], "search_paths": []}),
        encoding="utf-8",
    )
    with pytest.raises(RuntimeError, match="DefinitelyMissingFont_MADarwin_XYZ"):
        check_required_fonts(cfg)


def test_render_deck_writes_svg_png_pdf_with_content(tmp_path: Path) -> None:
    spec = LayoutSpec(
        slides=[
            LayoutSlide(
                slide=1,
                elements=[
                    LayoutElement(
                        id="title",
                        kind=LayoutElementKind.TEXT,
                        x=0.5,
                        y=0.4,
                        w=12.0,
                        h=1.0,
                        font_family="Arial",
                        font_size_pt=28,
                        font_weight=FontWeight.BOLD,
                        color="#1B2A4A",
                        text="Primary endpoint met",
                    )
                ],
            )
        ]
    )
    result = render_deck(output_dir=tmp_path, layout_spec=spec, dpi=150)
    svg = Path(result.slide_svgs[0])
    png = Path(result.slide_images[0])
    pdf = Path(result.pdf_path)
    assert svg.is_file() and "Primary endpoint met" in svg.read_text(encoding="utf-8")
    assert png.is_file() and png.stat().st_size > 2000
    pix = pymupdf.Pixmap(str(png))
    assert pix.width >= 1900
    samples = [pix.pixel(x, y) for x, y in ((80, 80), (400, 120), (900, 200))]
    assert not all(c[0] > 250 and c[1] > 250 and c[2] > 250 for c in samples)
    assert pdf.is_file()
    assert "LibreOffice" not in render_slide_svg(spec.slides[0])


def test_pdf_to_pngs_names_and_dpi(tmp_path: Path) -> None:
    pdf_path = tmp_path / "deck.pdf"
    doc = pymupdf.open()
    try:
        doc.new_page(width=612, height=792)
        doc.new_page(width=612, height=792)
        doc.save(pdf_path)
    finally:
        doc.close()

    out = tmp_path / "slides"
    paths = pdf_to_pngs(pdf_path, out, dpi=150)
    assert [p.name for p in paths] == ["slide_01.png", "slide_02.png"]
    assert all(p.is_file() for p in paths)

    pix = pymupdf.Pixmap(str(paths[0]))
    # 612pt page at 150 DPI ≈ 1275 px wide
    assert pix.width >= 1200
    assert pix.height >= 1500


def test_pdf_to_pngs_rejects_low_dpi(tmp_path: Path) -> None:
    pdf_path = tmp_path / "deck.pdf"
    doc = pymupdf.open()
    try:
        doc.new_page()
        doc.save(pdf_path)
    finally:
        doc.close()
    with pytest.raises(ValueError, match="150"):
        pdf_to_pngs(pdf_path, tmp_path / "slides", dpi=72)
