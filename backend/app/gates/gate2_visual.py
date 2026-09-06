"""Gate 2 — visual auto-checks (PRD §7.7 / Prompt 3)."""

from __future__ import annotations

from pathlib import Path

from app.models.common import CheckLocation
from app.models.gates import Gate2Result, GateCheckResult


def check_shape_bounds(pptx_path: Path | str) -> GateCheckResult:
    """No shape extends past slide edges."""
    raise NotImplementedError


def check_text_overflow(pptx_path: Path | str) -> GateCheckResult:
    """Estimated rendered text height must fit the text box height."""
    raise NotImplementedError


def check_min_font_size(pptx_path: Path | str, *, min_font_pt: float) -> GateCheckResult:
    """No text run below configured minimum body size."""
    raise NotImplementedError


def check_font_family_count(pptx_path: Path | str, *, max_families: int = 2) -> GateCheckResult:
    """Distinct font family count must be ≤ ``max_families``."""
    raise NotImplementedError


def check_color_count(pptx_path: Path | str, *, max_colors: int = 5) -> GateCheckResult:
    """Distinct colour count must be ≤ ``max_colors``."""
    raise NotImplementedError


def check_image_aspect_distortion(
    pptx_path: Path | str,
    *,
    tolerance: float = 0.02,
) -> GateCheckResult:
    """Placed image w/h vs native ratio within tolerance (default 2%)."""
    raise NotImplementedError


def check_contrast_ratio(
    pptx_path: Path | str,
    slide_images: list[Path | str],
    *,
    min_contrast: float,
) -> GateCheckResult:
    """Text vs background fill contrast must be ≥ configured WCAG ratio."""
    raise NotImplementedError


def check_alignment_discipline(pptx_path: Path | str) -> GateCheckResult:
    """Left edges must cluster to ≤ 4 distinct x values per slide."""
    raise NotImplementedError


def check_density(
    pptx_path: Path | str,
    *,
    max_words_per_slide: int,
    max_bullets_per_slide: int,
) -> GateCheckResult:
    """Word and bullet counts per slide vs skill-defined limits."""
    raise NotImplementedError


def check_empty_placeholders(pptx_path: Path | str) -> GateCheckResult:
    """Fail on empty or default-text placeholder elements."""
    raise NotImplementedError


def check_shape_overlap(pptx_path: Path | str) -> GateCheckResult:
    """Bounding-box intersection between non-nested / non-intentional shapes."""
    raise NotImplementedError


def run_gate2(
    *,
    pptx_path: Path | str,
    slide_images: list[Path | str],
    defaults_config: Path | str | None = None,
) -> Gate2Result:
    """Run all Gate 2 checks. No LLM calls. Failures block Gate 3.

    Each failure records slide number and ``(x, y, w, h)`` for UI pins.

    Parameters
    ----------
    pptx_path:
        Generated deck.
    slide_images:
        Rendered PNGs corresponding to each slide.
    defaults_config:
        Optional path to ``defaults.yaml`` for thresholds.

    Returns
    -------
    Gate2Result
        Artifact suitable for ``gate2.json``.
    """
    raise NotImplementedError


def location(
    slide: int,
    x: float,
    y: float,
    w: float,
    h: float,
    *,
    element_id: str | None = None,
    detail: str = "",
) -> CheckLocation:
    """Build a typed Gate 2 failure location."""
    raise NotImplementedError
