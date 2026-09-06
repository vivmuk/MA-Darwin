"""Deterministic text measurement shared by SVG wrap and the text-fit check."""

from __future__ import annotations

from app.models.layout import FontWeight, LayoutElement

# Average glyph width as a fraction of em (Arial-like Latin). Bold is slightly wider.
_WIDTH_NORMAL = 0.55
_WIDTH_BOLD = 0.62
LINE_HEIGHT = 1.2


def char_width_factor(weight: FontWeight | str) -> float:
    value = weight.value if isinstance(weight, FontWeight) else str(weight)
    return _WIDTH_BOLD if value == FontWeight.BOLD.value else _WIDTH_NORMAL


def text_width_in(text: str, font_size_pt: float, weight: FontWeight | str) -> float:
    """Estimated advance width of ``text`` in inches (72 pt = 1 in)."""
    if not text:
        return 0.0
    return (len(text) * char_width_factor(weight) * float(font_size_pt)) / 72.0


def wrap_lines(text: str, font_size_pt: float, weight: FontWeight | str, box_w_in: float) -> list[str]:
    """Greedy word wrap using the same width estimator as the text-fit check."""
    raw = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    paragraphs = raw.split("\n") if raw else [""]
    lines: list[str] = []
    for para in paragraphs:
        words = para.split()
        if not words:
            lines.append("")
            continue
        current = words[0]
        for word in words[1:]:
            trial = f"{current} {word}"
            if text_width_in(trial, font_size_pt, weight) <= box_w_in or not current:
                current = trial
            else:
                lines.append(current)
                current = word
        lines.append(current)
    return lines or [""]


def text_block_size(element: LayoutElement) -> tuple[float, float, list[str]]:
    """Return (width_in, height_in, lines) for a text element's content."""
    lines = wrap_lines(element.text, element.font_size_pt, element.font_weight, element.w)
    width = max((text_width_in(line, element.font_size_pt, element.font_weight) for line in lines), default=0.0)
    height = (len(lines) * element.font_size_pt * LINE_HEIGHT) / 72.0
    return width, height, lines


def text_exceeds_box(element: LayoutElement, *, slack_in: float = 0.02) -> str | None:
    """Return a failure detail if estimated text does not fit the explicit box."""
    if element.kind.value != "text" and not element.text:
        return None
    if not (element.text or "").strip():
        return None
    width, height, lines = text_block_size(element)
    single = max((text_width_in(line, element.font_size_pt, element.font_weight) for line in lines), default=0.0)
    if single > element.w + slack_in:
        return f"text width {single:.3f}in exceeds box {element.w:.3f}in"
    if height > element.h + slack_in:
        return f"text height {height:.3f}in exceeds box {element.h:.3f}in"
    return None
