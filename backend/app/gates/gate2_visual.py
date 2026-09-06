"""Gate 2 — visual checks against LayoutSpec (inches). No pptx XML, no LLM."""

from __future__ import annotations

from pathlib import Path
import yaml

from app.models.common import CheckLocation
from app.models.gates import Gate2Result, GateCheckResult
from app.models.layout import LayoutElement, LayoutElementKind, LayoutSpec
from app.paths import CONFIG_DIR
from app.rendering.font_check import load_required_fonts
from app.rendering.text_metrics import text_exceeds_box

ALIGN_TOL_IN = 0.1
OVERLAP_MIN_AREA_SQIN = 0.02
BOUNDS_SLACK_IN = 0.02

DEFAULT_PLACEHOLDER_TEXTS = {
    "click to add title",
    "click to add subtitle",
    "click to add text",
    "click to add notes",
    "click to add content",
}

CHECK_NAMES = (
    "shape_bounds",
    "text_overflow",
    "min_font_size",
    "font_family_count",
    "color_count",
    "image_aspect_distortion",
    "contrast_ratio",
    "alignment_discipline",
    "density",
    "empty_placeholders",
    "shape_overlap",
    "text_fit",
    "allowed_fonts",
)


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
    return CheckLocation(
        slide=slide,
        element_id=element_id,
        x=x,
        y=y,
        w=w,
        h=h,
        detail=detail,
    )


def _result(name: str, locations: list[CheckLocation], ok_msg: str, fail_msg: str) -> GateCheckResult:
    passed = not locations
    return GateCheckResult(
        name=name,
        passed=passed,
        message=ok_msg if passed else fail_msg,
        flagged=False,
        locations=locations,
    )


def _loc(slide_n: int, el: LayoutElement, detail: str = "") -> CheckLocation:
    return location(slide_n, el.x, el.y, el.w, el.h, element_id=el.id, detail=detail)


def _require(layout: LayoutSpec | None) -> LayoutSpec:
    if layout is None:
        raise NotImplementedError
    return layout


def _hex_rgb(color: str | None) -> tuple[int, int, int] | None:
    if not color:
        return None
    raw = color.strip().lstrip("#")
    if len(raw) != 6:
        return None
    try:
        return int(raw[0:2], 16), int(raw[2:4], 16), int(raw[4:6], 16)
    except ValueError:
        return None


def _rel_luminance(rgb: tuple[int, int, int]) -> float:
    def chan(c: int) -> float:
        x = c / 255.0
        return x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4

    r, g, b = (chan(v) for v in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _contrast(fg: tuple[int, int, int], bg: tuple[int, int, int]) -> float:
    l1, l2 = _rel_luminance(fg), _rel_luminance(bg)
    lighter, darker = (l1, l2) if l1 >= l2 else (l2, l1)
    return (lighter + 0.05) / (darker + 0.05)


def check_shape_bounds(layout: LayoutSpec | None = None, *, pptx_path: Path | str | None = None) -> GateCheckResult:
    del pptx_path
    spec = _require(layout)
    locations: list[CheckLocation] = []
    for slide in spec.slides:
        for el in slide.elements:
            if (
                el.x < -BOUNDS_SLACK_IN
                or el.y < -BOUNDS_SLACK_IN
                or el.x + el.w > slide.width + BOUNDS_SLACK_IN
                or el.y + el.h > slide.height + BOUNDS_SLACK_IN
            ):
                locations.append(_loc(slide.slide, el, "extends past slide edge"))
    return _result("shape_bounds", locations, "All elements stay on the canvas", f"{len(locations)} element(s) past slide edge")


def check_text_overflow(layout: LayoutSpec | None = None, *, pptx_path: Path | str | None = None) -> GateCheckResult:
    del pptx_path
    spec = _require(layout)
    locations: list[CheckLocation] = []
    for slide in spec.slides:
        for el in slide.elements:
            if el.kind != LayoutElementKind.TEXT:
                continue
            detail = text_exceeds_box(el)
            if detail:
                locations.append(_loc(slide.slide, el, detail))
    return _result("text_overflow", locations, "All text fits its box", f"{len(locations)} text element(s) overflow")


def check_text_fit(layout: LayoutSpec | None = None) -> GateCheckResult:
    """Fidelity guard: estimated glyph width vs explicit box (SVG vs PowerPoint)."""
    result = check_text_overflow(layout)
    return result.model_copy(update={"name": "text_fit"})


def check_min_font_size(
    layout: LayoutSpec | None = None,
    *,
    min_font_pt: float = 14,
    pptx_path: Path | str | None = None,
) -> GateCheckResult:
    del pptx_path
    spec = _require(layout)
    locations: list[CheckLocation] = []
    for slide in spec.slides:
        for el in slide.elements:
            if el.kind != LayoutElementKind.TEXT:
                continue
            if not (el.text or "").strip():
                continue
            if el.font_size_pt + 1e-6 < float(min_font_pt):
                locations.append(_loc(slide.slide, el, f"{el.font_size_pt:g}pt < {min_font_pt:g}pt"))
    return _result(
        "min_font_size",
        locations,
        f"All text runs are ≥ {min_font_pt:g}pt",
        f"Text below {min_font_pt:g}pt on {len(locations)} element(s)",
    )


def check_font_family_count(
    layout: LayoutSpec | None = None,
    *,
    max_families: int = 2,
    pptx_path: Path | str | None = None,
) -> GateCheckResult:
    del pptx_path
    spec = _require(layout)
    families = sorted(
        {
            el.font_family
            for slide in spec.slides
            for el in slide.elements
            if el.kind == LayoutElementKind.TEXT and (el.text or "").strip()
        }
    )
    extra = families[max_families:]
    locations: list[CheckLocation] = []
    if extra:
        for slide in spec.slides:
            for el in slide.elements:
                if el.font_family in extra:
                    locations.append(_loc(slide.slide, el, el.font_family))
                    break
    return _result(
        "font_family_count",
        locations,
        f"{len(families)} font family(ies) ≤ {max_families}",
        f"{len(families)} font families ({', '.join(families)}) exceed max {max_families}",
    )


def check_allowed_fonts(layout: LayoutSpec | None = None) -> GateCheckResult:
    spec = _require(layout)
    allowed = {n.lower() for n in load_required_fonts()}
    locations: list[CheckLocation] = []
    for slide in spec.slides:
        for el in slide.elements:
            if el.kind != LayoutElementKind.TEXT:
                continue
            if el.font_family.lower() not in allowed:
                locations.append(_loc(slide.slide, el, f"font {el.font_family} not in fonts.yaml"))
    return _result(
        "allowed_fonts",
        locations,
        "All fonts are listed in fonts.yaml",
        f"{len(locations)} element(s) use a font not in fonts.yaml",
    )


def check_color_count(
    layout: LayoutSpec | None = None,
    *,
    max_colors: int = 5,
    pptx_path: Path | str | None = None,
) -> GateCheckResult:
    del pptx_path
    spec = _require(layout)
    colors: set[str] = set()
    for slide in spec.slides:
        for el in slide.elements:
            if el.color:
                colors.add(el.color.lower())
            if el.fill:
                colors.add(el.fill.lower())
    locations: list[CheckLocation] = []
    if len(colors) > max_colors:
        for slide in spec.slides:
            for el in slide.elements:
                locations.append(_loc(slide.slide, el, f"{len(colors)} colors"))
                break
            if locations:
                break
    return _result(
        "color_count",
        locations,
        f"{len(colors)} color(s) ≤ {max_colors}",
        f"{len(colors)} colors exceed max {max_colors}",
    )


def check_image_aspect_distortion(
    layout: LayoutSpec | None = None,
    *,
    tolerance: float = 0.02,
    pptx_path: Path | str | None = None,
) -> GateCheckResult:
    del pptx_path
    spec = _require(layout)
    locations: list[CheckLocation] = []
    for slide in spec.slides:
        for el in slide.elements:
            if el.kind != LayoutElementKind.IMAGE:
                continue
            if el.w <= 0 or el.h <= 0:
                continue
            placed = el.w / el.h
            intrinsic = _intrinsic_aspect(el.image_path)
            if intrinsic is None:
                continue
            if abs(placed - intrinsic) / intrinsic > tolerance:
                locations.append(_loc(slide.slide, el, f"placed {placed:.3f} vs source {intrinsic:.3f}"))
    return _result(
        "image_aspect_distortion",
        locations,
        "Image aspect matches source",
        f"{len(locations)} distorted image(s)",
    )


def _intrinsic_aspect(path: str | None) -> float | None:
    if not path:
        return None
    src = Path(path)
    if not src.is_file():
        return None
    try:
        import pymupdf

        pix = pymupdf.Pixmap(str(src))
        if pix.height <= 0:
            return None
        return pix.width / pix.height
    except Exception:
        return None


def check_contrast_ratio(
    layout: LayoutSpec | None = None,
    slide_images: list | None = None,
    *,
    min_contrast: float = 4.5,
    pptx_path: Path | str | None = None,
) -> GateCheckResult:
    del pptx_path, slide_images
    spec = _require(layout)
    locations: list[CheckLocation] = []
    for slide in spec.slides:
        bg = _hex_rgb(slide.background) or (255, 255, 255)
        for el in slide.elements:
            if el.kind != LayoutElementKind.TEXT or not (el.text or "").strip():
                continue
            fg = _hex_rgb(el.color)
            if fg is None:
                continue
            ratio = _contrast(fg, bg)
            if ratio + 1e-6 < float(min_contrast):
                locations.append(_loc(slide.slide, el, f"contrast {ratio:.2f} < {min_contrast}"))
    return _result(
        "contrast_ratio",
        locations,
        f"Text contrast ≥ {min_contrast}",
        f"{len(locations)} low-contrast text element(s)",
    )


def check_alignment_discipline(
    layout: LayoutSpec | None = None,
    *,
    max_clusters: int = 4,
    pptx_path: Path | str | None = None,
) -> GateCheckResult:
    del pptx_path
    spec = _require(layout)
    locations: list[CheckLocation] = []
    for slide in spec.slides:
        xs = [el.x for el in slide.elements]
        clusters = _cluster_count(xs, ALIGN_TOL_IN)
        if clusters > max_clusters and slide.elements:
            locations.append(_loc(slide.slide, slide.elements[0], f"{clusters} left-edge clusters"))
    return _result(
        "alignment_discipline",
        locations,
        f"Left edges snap to ≤ {max_clusters} x-values per slide",
        f"{len(locations)} slide(s) have more than {max_clusters} left-edge clusters",
    )


def _cluster_count(values: list[float], tol: float) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    count = 1
    current = ordered[0]
    for item in ordered[1:]:
        if item - current > tol:
            count += 1
            current = item
    return count


def check_density(
    layout: LayoutSpec | None = None,
    *,
    max_words_per_slide: int = 80,
    max_bullets_per_slide: int = 6,
    pptx_path: Path | str | None = None,
) -> GateCheckResult:
    del pptx_path
    spec = _require(layout)
    locations: list[CheckLocation] = []
    for slide in spec.slides:
        texts = [el.text for el in slide.elements if el.kind == LayoutElementKind.TEXT]
        words = sum(len((t or "").split()) for t in texts)
        bullets = sum(1 for el in slide.elements if el.id.endswith(tuple(f"_body_{i}" for i in range(20))) or "_body_" in el.id)
        if bullets == 0:
            bullets = max(0, len([t for t in texts if t.strip()]) - 1)
        if words > max_words_per_slide or bullets > max_bullets_per_slide:
            el = slide.elements[0] if slide.elements else LayoutElement(id="slide", x=0, y=0, w=1, h=1)
            locations.append(_loc(slide.slide, el, f"{words} words / {bullets} bullets"))
    return _result(
        "density",
        locations,
        "Word and bullet counts within limits",
        f"{len(locations)} overcrowded slide(s)",
    )


def check_empty_placeholders(
    layout: LayoutSpec | None = None, *, pptx_path: Path | str | None = None
) -> GateCheckResult:
    del pptx_path
    spec = _require(layout)
    locations: list[CheckLocation] = []
    for slide in spec.slides:
        for el in slide.elements:
            if el.kind != LayoutElementKind.TEXT:
                continue
            text = (el.text or "").strip()
            if not text:
                locations.append(_loc(slide.slide, el, "empty placeholder"))
            elif text.lower() in DEFAULT_PLACEHOLDER_TEXTS:
                locations.append(_loc(slide.slide, el, "default placeholder text"))
    return _result(
        "empty_placeholders",
        locations,
        "No empty or default-text placeholders",
        f"{len(locations)} empty or placeholder-looking element(s)",
    )


def check_shape_overlap(
    layout: LayoutSpec | None = None, *, pptx_path: Path | str | None = None
) -> GateCheckResult:
    del pptx_path
    spec = _require(layout)
    locations: list[CheckLocation] = []
    for slide in spec.slides:
        boxes = [(el, (el.x, el.y, el.w, el.h)) for el in slide.elements if el.w > 0.08 and el.h > 0.08]
        for i, (el_a, a) in enumerate(boxes):
            for el_b, b in boxes[i + 1 :]:
                if _contains(a, b) or _contains(b, a):
                    continue
                area = _intersection(a, b)
                if area > OVERLAP_MIN_AREA_SQIN:
                    locations.append(_loc(slide.slide, el_a, f"overlaps {el_b.id} ({area:.3f} sq in)"))
                    break
    return _result(
        "shape_overlap",
        locations,
        "No unintentional shape overlaps",
        f"{len(locations)} unintentional overlapping shape pair(s)",
    )


def _contains(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> bool:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return ax <= bx and ay <= by and ax + aw >= bx + bw and ay + ah >= by + bh


def _intersection(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> float:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    x1, y1 = max(ax, bx), max(ay, by)
    x2, y2 = min(ax + aw, bx + bw), min(ay + ah, by + bh)
    if x2 <= x1 or y2 <= y1:
        return 0.0
    return (x2 - x1) * (y2 - y1)


def _load_defaults(defaults_config: Path | str | None) -> dict[str, object]:
    path = Path(defaults_config) if defaults_config is not None else CONFIG_DIR / "defaults.yaml"
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    if not isinstance(data, dict):
        raise ValueError(f"defaults config must be a mapping: {path}")
    return data


def run_gate2(
    *,
    layout_spec: LayoutSpec | None = None,
    pptx_path: Path | str | None = None,
    slide_images: list[Path | str] | None = None,
    defaults_config: Path | str | None = None,
) -> Gate2Result:
    """Run all Gate 2 checks against the layout spec. Failures block Gate 3."""
    del pptx_path
    spec = _require(layout_spec)
    cfg = _load_defaults(defaults_config)
    checks = [
        check_shape_bounds(spec),
        check_text_overflow(spec),
        check_min_font_size(spec, min_font_pt=float(cfg["min_font_pt"])),
        check_font_family_count(spec, max_families=int(cfg["max_font_families"])),
        check_color_count(spec, max_colors=int(cfg["max_colors"])),
        check_image_aspect_distortion(spec, tolerance=float(cfg.get("image_aspect_tolerance", 0.02))),
        check_contrast_ratio(spec, slide_images or [], min_contrast=float(cfg["min_contrast"])),
        check_alignment_discipline(spec, max_clusters=int(cfg.get("alignment_max_x_clusters", 4))),
        check_density(
            spec,
            max_words_per_slide=int(cfg["max_words_per_slide"]),
            max_bullets_per_slide=int(cfg["max_bullets_per_slide"]),
        ),
        check_empty_placeholders(spec),
        check_shape_overlap(spec),
        check_text_fit(spec),
        check_allowed_fonts(spec),
    ]
    return Gate2Result(gate="gate2", passed=all(c.passed for c in checks), checks=checks)
