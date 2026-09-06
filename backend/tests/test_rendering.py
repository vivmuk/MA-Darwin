"""Render pipeline and font-check tests (no live module outputs)."""

from __future__ import annotations

from pathlib import Path

import pymupdf
import pytest
import yaml

from app.rendering.font_check import check_required_fonts, list_installed_fonts, load_required_fonts
from app.rendering.render import pdf_to_pngs


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
