"""Gate 2 visual checks against LayoutSpec (inches)."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.gates.gate2_visual import (
    CHECK_NAMES,
    check_alignment_discipline,
    check_allowed_fonts,
    check_color_count,
    check_contrast_ratio,
    check_density,
    check_empty_placeholders,
    check_font_family_count,
    check_image_aspect_distortion,
    check_min_font_size,
    check_shape_bounds,
    check_shape_overlap,
    check_text_fit,
    check_text_overflow,
    run_gate2,
)
from app.models.gates import Gate2Result
from app.models.layout import FontWeight, LayoutElement, LayoutElementKind, LayoutSlide, LayoutSpec


def _png(path: Path, width: int = 100, height: int = 100) -> Path:
    import struct
    import zlib

    raw = b"".join(b"\x00" + (bytes((30, 90, 150)) * width) for _ in range(height))

    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )
    return path


def _el(**kwargs) -> LayoutElement:
    defaults = dict(id="el", kind=LayoutElementKind.TEXT, x=0.6, y=0.5, w=12.0, h=0.7, font_family="Arial", font_size_pt=16, color="#000000", text="Hello")
    defaults.update(kwargs)
    return LayoutElement.model_validate(defaults)


def clean_spec(png: Path) -> LayoutSpec:
    return LayoutSpec(
        slides=[
            LayoutSlide(
                slide=1,
                role="title",
                elements=[
                    _el(id="bar", kind=LayoutElementKind.SHAPE, x=0.6, y=0.22, w=12.0, h=0.06, fill="#003366", color="#003366", text=""),
                    _el(id="title", x=0.6, y=0.45, w=12.0, h=0.7, font_size_pt=28, font_weight=FontWeight.BOLD, text="Demo Trial — HFrEF outcomes"),
                    _el(id="s1_body_0", x=0.6, y=1.4, w=12.0, h=0.5, text="Randomized, double-blind design in adults with HFrEF."),
                    _el(id="s1_body_1", x=0.6, y=1.95, w=12.0, h=0.5, text="Primary endpoint met — HR 0.78 (95% CI 0.68–0.90)."),
                    _el(id="s1_body_2", x=0.6, y=2.5, w=12.0, h=0.5, text="Serious adverse events in 18.2% of treated patients."),
                    _el(
                        id="fig",
                        kind=LayoutElementKind.IMAGE,
                        x=0.6,
                        y=5.0,
                        w=1.5,
                        h=1.5,
                        image_path=str(png),
                        text="",
                    ),
                ],
            )
        ]
    )


def broken_spec(png: Path) -> LayoutSpec:
    overflow = (
        "Primary endpoint results require far more copy than this box can hold "
        "and the estimated rendered height will exceed the text frame."
    )
    dense = [
        "First extra bullet about secondary findings that should not crowd this slide at all.",
        "Second extra bullet listing exploratory analyses without a clear takeaway sentence.",
        "Third extra bullet repeating safety numbers that belong on a dedicated safety slide.",
        "Fourth extra bullet with population notes that overfill the density budget badly.",
        "Fifth extra bullet describing limitations that make the word count blow past eighty.",
        "Sixth extra bullet adding baseline characteristics nobody can scan in this layout.",
        "Seventh extra bullet guaranteeing this slide exceeds both word and bullet limits.",
        "Eighth extra bullet so Gate 2 density must fail on this deliberately broken deck.",
    ]
    elements = [
        _el(id="overflow", x=0.25, y=0.2, w=1.7, h=0.28, font_size_pt=18, text=overflow),
        _el(id="tiny", x=2.2, y=0.2, w=2.2, h=0.7, font_family="Times New Roman", font_size_pt=10, color="#BEBEBE", text="Tiny gray caption"),
        _el(id="georgia", x=4.6, y=0.2, w=2.0, h=0.5, font_family="Georgia", color="#800080", text="Georgia accent"),
        _el(id="calibri", x=6.9, y=0.2, w=2.0, h=0.5, font_family="Calibri", color="#008080", text="Calibri accent"),
        _el(id="distorted", kind=LayoutElementKind.IMAGE, x=9.1, y=0.15, w=3.2, h=1.0, image_path=str(png), text=""),
        _el(id="past_edge", kind=LayoutElementKind.SHAPE, x=12.4, y=1.4, w=2.0, h=0.8, fill="#FF0000", color="#FF0000", text=""),
        _el(id="overlap_a", kind=LayoutElementKind.SHAPE, x=0.3, y=1.6, w=2.6, h=1.6, fill="#00A000", color="#00A000", text=""),
        _el(id="overlap_b", kind=LayoutElementKind.SHAPE, x=1.4, y=2.2, w=2.6, h=1.6, fill="#FF8000", color="#FF8000", text=""),
        _el(id="ph", x=8.9, y=1.6, w=3.0, h=0.6, font_size_pt=18, text="Click to add title"),
        _el(id="empty", x=8.9, y=2.4, w=3.0, h=0.5, text=""),
    ]
    for i, line in enumerate(dense):
        elements.append(
            _el(id=f"s1_body_{i}", x=4.2, y=1.5 + 0.4 * i, w=4.4, h=0.38, font_family="Comic Sans MS", font_size_pt=14, color="#0000B4", text=line)
        )
    return LayoutSpec(slides=[LayoutSlide(slide=1, role="broken", elements=elements)])


CHECK_FNS = {
    "shape_bounds": lambda s: check_shape_bounds(s),
    "text_overflow": lambda s: check_text_overflow(s),
    "min_font_size": lambda s: check_min_font_size(s, min_font_pt=14),
    "font_family_count": lambda s: check_font_family_count(s, max_families=2),
    "color_count": lambda s: check_color_count(s, max_colors=5),
    "image_aspect_distortion": lambda s: check_image_aspect_distortion(s, tolerance=0.02),
    "contrast_ratio": lambda s: check_contrast_ratio(s, min_contrast=4.5),
    "alignment_discipline": lambda s: check_alignment_discipline(s),
    "density": lambda s: check_density(s, max_words_per_slide=80, max_bullets_per_slide=6),
    "empty_placeholders": lambda s: check_empty_placeholders(s),
    "shape_overlap": lambda s: check_shape_overlap(s),
    "text_fit": lambda s: check_text_fit(s),
    "allowed_fonts": lambda s: check_allowed_fonts(s),
}


@pytest.fixture()
def pixel(tmp_path: Path) -> Path:
    return _png(tmp_path / "pixel.png")


@pytest.mark.parametrize("name", list(CHECK_NAMES))
def test_each_check_fails_on_broken_spec(pixel: Path, name: str) -> None:
    result = CHECK_FNS[name](broken_spec(pixel))
    assert result.name == name
    assert result.passed is False, f"{name} should fail: {result.message}"
    assert result.locations, f"{name} must record slide/(x,y,w,h) pins"
    loc = result.locations[0]
    assert loc.slide >= 1
    assert loc.x is not None and loc.y is not None
    assert loc.w is not None and loc.h is not None


@pytest.mark.parametrize("name", list(CHECK_NAMES))
def test_each_check_passes_on_clean_spec(pixel: Path, name: str) -> None:
    result = CHECK_FNS[name](clean_spec(pixel))
    assert result.name == name
    assert result.passed is True, f"{name} should pass: {result.message} {result.locations}"
    assert result.locations == []


def test_run_gate2_broken_fails(pixel: Path) -> None:
    report = run_gate2(layout_spec=broken_spec(pixel), slide_images=[])
    assert isinstance(report, Gate2Result)
    assert report.gate == "gate2"
    assert report.passed is False
    names = {c.name for c in report.checks}
    assert set(CHECK_NAMES) <= names
