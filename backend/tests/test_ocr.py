"""OCR merge helpers — no live Venice calls."""

from __future__ import annotations

from app.ingestion.ocr import merge_page_text


def test_merge_prefers_digital_when_ocr_is_subset() -> None:
    digital = "Primary endpoint HR 0.78 (95% CI 0.68-0.90)."
    assert merge_page_text(digital, "HR 0.78") == digital


def test_merge_uses_ocr_when_digital_empty() -> None:
    assert merge_page_text("  ", "Figure 1 Kaplan-Meier") == "Figure 1 Kaplan-Meier"


def test_merge_appends_ocr_when_it_adds_content() -> None:
    digital = "Abstract. Background only."
    ocr = "Table 1. N=420 randomized. Mean age 64.2 years. SAE 18.2%."
    merged = merge_page_text(digital, ocr)
    assert digital in merged
    assert "[OCR]" in merged
    assert "N=420" in merged
