"""Gate 2 visual checks against hand-built clean/broken decks."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.gates.gate2_visual import (
    CHECK_NAMES,
    check_alignment_discipline,
    check_color_count,
    check_contrast_ratio,
    check_density,
    check_empty_placeholders,
    check_font_family_count,
    check_image_aspect_distortion,
    check_min_font_size,
    check_shape_bounds,
    check_shape_overlap,
    check_text_overflow,
    run_gate2,
)
from app.models.gates import Gate2Result

FIXTURES = Path(__file__).resolve().parent / "fixtures"
CLEAN = FIXTURES / "clean_deck.pptx"
BROKEN = FIXTURES / "broken_deck.pptx"

CHECK_FNS = {
    "shape_bounds": lambda p: check_shape_bounds(p),
    "text_overflow": lambda p: check_text_overflow(p),
    "min_font_size": lambda p: check_min_font_size(p, min_font_pt=14),
    "font_family_count": lambda p: check_font_family_count(p, max_families=2),
    "color_count": lambda p: check_color_count(p, max_colors=5),
    "image_aspect_distortion": lambda p: check_image_aspect_distortion(p, tolerance=0.02),
    "contrast_ratio": lambda p: check_contrast_ratio(p, [], min_contrast=4.5),
    "alignment_discipline": lambda p: check_alignment_discipline(p),
    "density": lambda p: check_density(p, max_words_per_slide=80, max_bullets_per_slide=6),
    "empty_placeholders": lambda p: check_empty_placeholders(p),
    "shape_overlap": lambda p: check_shape_overlap(p),
}


@pytest.fixture(scope="module")
def clean_deck() -> Path:
    assert CLEAN.is_file(), f"missing fixture {CLEAN}"
    return CLEAN


@pytest.fixture(scope="module")
def broken_deck() -> Path:
    assert BROKEN.is_file(), f"missing fixture {BROKEN}"
    return BROKEN


@pytest.mark.parametrize("name", list(CHECK_NAMES))
def test_each_check_fails_on_broken_deck(broken_deck: Path, name: str) -> None:
    result = CHECK_FNS[name](broken_deck)
    assert result.name == name
    assert result.passed is False, f"{name} should fail on broken_deck: {result.message}"
    assert result.locations, f"{name} must record slide/(x,y,w,h) pins"
    loc = result.locations[0]
    assert loc.slide >= 1
    assert loc.x is not None and loc.y is not None
    assert loc.w is not None and loc.h is not None


@pytest.mark.parametrize("name", list(CHECK_NAMES))
def test_each_check_passes_on_clean_deck(clean_deck: Path, name: str) -> None:
    result = CHECK_FNS[name](clean_deck)
    assert result.name == name
    assert result.passed is True, f"{name} should pass on clean_deck: {result.message} {result.locations}"
    assert result.locations == []


def test_run_gate2_broken_fails_every_named_check(broken_deck: Path) -> None:
    report = run_gate2(pptx_path=broken_deck, slide_images=[])
    assert isinstance(report, Gate2Result)
    assert report.gate == "gate2"
    assert report.passed is False
    names = [c.name for c in report.checks]
    assert names == list(CHECK_NAMES)
    failed = {c.name for c in report.checks if not c.passed}
    assert failed == set(CHECK_NAMES)


def test_run_gate2_clean_passes(clean_deck: Path) -> None:
    report = run_gate2(pptx_path=clean_deck, slide_images=[])
    assert report.passed is True
    assert all(c.passed for c in report.checks)
