"""Gate 3 vision judge — tests use frozen fixtures + synthetic PNGs (not live modules)."""

from __future__ import annotations

import json
from pathlib import Path

import fitz
import pytest

from app.gates.gate3_judge import (
    assert_judge_is_blind,
    build_contact_sheet,
    load_rubric,
    median_criterion_scores,
    render_judge_prompt,
    run_gate3,
)
from app.models.blueprint import Blueprint, BlueprintSlide
from app.models.gates import Gate3Result, JudgeCriterionScore
from app.paths import PROMPTS_DIR

FIXTURES = Path(__file__).resolve().parent / "fixtures"

_BAD_DEFECT_NEEDLES = (
    "focal point",
    "colliding",
    "contrast",
    "amateur",
    "unrelated",
    "placeholder",
    "invent the story",
    "illegible",
)


def _gold_png(path: Path, title: str) -> Path:
    """SYNTHETIC EXAMPLE — consulting-clean slide, not the human gold deck."""
    doc = fitz.open()
    page = doc.new_page(width=1920, height=1080)
    page.draw_rect(page.rect, color=(1, 1, 1), fill=(1, 1, 1))
    page.draw_rect(fitz.Rect(0, 0, 1920, 150), color=(0.04, 0.18, 0.26), fill=(0.04, 0.18, 0.26))
    page.insert_text((96, 100), title, fontsize=42, color=(1, 1, 1), fontname="helv")
    page.draw_rect(fitz.Rect(96, 200, 240, 208), color=(0.0, 0.48, 0.54), fill=(0.0, 0.48, 0.54))
    page.insert_text((96, 280), "Primary endpoint met", fontsize=28, color=(0.08, 0.08, 0.08), fontname="helv")
    page.insert_text((96, 360), "HR 0.78  (95% CI 0.68–0.90; p=0.001)", fontsize=22, color=(0.12, 0.12, 0.12), fontname="helv")
    page.insert_text((96, 440), "N=420 randomized 1:1", fontsize=22, color=(0.12, 0.12, 0.12), fontname="helv")
    pix = page.get_pixmap(dpi=100)
    path.parent.mkdir(parents=True, exist_ok=True)
    pix.save(path)
    doc.close()
    return path


def _bad_png(path: Path, variant: int) -> Path:
    """SYNTHETIC EXAMPLE — deliberately broken: no hierarchy, clash, low contrast."""
    doc = fitz.open()
    page = doc.new_page(width=1920, height=1080)
    bg = (0.95, 0.88, 0.2) if variant == 0 else (0.7, 0.4, 0.85)
    page.draw_rect(page.rect, color=bg, fill=bg)
    colors = [
        (1, 0, 0),
        (0, 1, 0),
        (0, 0, 1),
        (1, 0.5, 0),
        (0.2, 0.9, 0.9),
        (0.9, 0.2, 0.9),
    ]
    for i, color in enumerate(colors):
        x0 = 20 + i * 180
        y0 = 20 + (i % 3) * 220
        page.draw_rect(fitz.Rect(x0, y0, x0 + 520, y0 + 340), color=color, fill=color)
    page.insert_text((30, 80), "lorem " * 40, fontsize=8, color=(0.92, 0.86, 0.25), fontname="helv")
    pix = page.get_pixmap(dpi=100)
    path.parent.mkdir(parents=True, exist_ok=True)
    pix.save(path)
    doc.close()
    return path


def _blueprint(n: int = 2) -> Blueprint:
    slides = [
        BlueprintSlide(role="title", requires_visual=False),
        BlueprintSlide(role="primary_endpoint", requires_visual=True),
    ]
    return Blueprint(id="test", name="test", slides=slides[:n])


def test_load_rubric_from_config_not_prompt() -> None:
    rubric = load_rubric()
    assert rubric.total_points == 100
    assert len(rubric.slide_criteria) == 8
    assert len(rubric.deck_criteria) == 2
    prompt = (PROMPTS_DIR / "judge.md").read_text(encoding="utf-8")
    assert "{{anchors}}" in prompt
    assert "No clear focal point" not in prompt
    rendered = render_judge_prompt(rubric, role="title", scope="slide")
    assert "visual_hierarchy" in rendered
    assert "No clear focal point" in rendered


def test_judge_payload_is_blind() -> None:
    assert_judge_is_blind({"role": "title", "scope": "slide"})
    with pytest.raises(AssertionError, match="not blind"):
        assert_judge_is_blind({"role": "title", "previous_score": 80, "round_n": 2})


def test_median_per_criterion() -> None:
    def run(scores: list[float]) -> list[JudgeCriterionScore]:
        return [
            JudgeCriterionScore(criterion="visual_hierarchy", weight=15, score=s, rationale="x")
            for s in scores
        ]

    # one criterion, three runs
    merged = median_criterion_scores(
        [
            [JudgeCriterionScore(criterion="visual_hierarchy", weight=15, score=10, rationale="a")],
            [JudgeCriterionScore(criterion="visual_hierarchy", weight=15, score=12, rationale="b")],
            [JudgeCriterionScore(criterion="visual_hierarchy", weight=15, score=11, rationale="c")],
        ]
    )
    assert merged[0].score == 11


def test_charts_na_when_no_visual(tmp_path: Path) -> None:
    gold = _gold_png(tmp_path / "title.png", "Study title")
    result = run_gate3(
        slide_images=[gold],
        blueprint=_blueprint(1),
        judge_runs=3,
        temperature=0.0,
        backend="heuristic",
        output_dir=tmp_path / "out",
    )
    charts = [c for c in result.slide_results[0].criteria if c.criterion == "charts_data_visualization"]
    assert charts and charts[0].score is None
    assert (tmp_path / "out" / "gate3.json").is_file()
    Gate3Result.model_validate_json((tmp_path / "out" / "gate3.json").read_text(encoding="utf-8"))


def test_gold_beats_bad_by_at_least_20(tmp_path: Path) -> None:
    """Acceptance: gold > bad by >= 20; bad rationales name real defects.

    Human gold/bad pptx are not in frozen fixtures (see CONTRACTS). These PNGs
    are labelled SYNTHETIC EXAMPLE. If fixtures/gold_deck.pptx appears later,
    render it outside this folder and pass the PNGs into run_gate3.
    """
    gold_images = [
        _gold_png(tmp_path / "gold" / "s1.png", "HFrEF outcomes"),
        _gold_png(tmp_path / "gold" / "s2.png", "Primary endpoint"),
    ]
    bad_images = [
        _bad_png(tmp_path / "bad" / "s1.png", 0),
        _bad_png(tmp_path / "bad" / "s2.png", 1),
    ]
    gold = run_gate3(
        slide_images=gold_images,
        blueprint=_blueprint(2),
        judge_runs=3,
        temperature=0.0,
        backend="heuristic",
    )
    bad = run_gate3(
        slide_images=bad_images,
        blueprint=_blueprint(2),
        judge_runs=3,
        temperature=0.0,
        backend="heuristic",
    )
    assert gold.deck_score - bad.deck_score >= 20, (gold.deck_score, bad.deck_score)
    blob = " ".join(c.rationale.lower() for c in bad.criteria)
    hits = [n for n in _BAD_DEFECT_NEEDLES if n in blob]
    assert hits, f"bad-deck rationales did not name defects: {blob!r}"


def test_score_variance_over_five_runs(tmp_path: Path) -> None:
    images = [
        _gold_png(tmp_path / "g1.png", "Title"),
        _gold_png(tmp_path / "g2.png", "Primary endpoint"),
    ]
    scores = [
        run_gate3(
            slide_images=images,
            blueprint=_blueprint(2),
            judge_runs=3,
            temperature=0.0,
            backend="heuristic",
        ).deck_score
        for _ in range(5)
    ]
    assert max(scores) - min(scores) <= 3, scores


def test_contact_sheet_and_fixture_gate3_schema(tmp_path: Path) -> None:
    a = _gold_png(tmp_path / "a.png", "A")
    b = _gold_png(tmp_path / "b.png", "B")
    sheet = build_contact_sheet([a, b], tmp_path / "sheet.png")
    assert sheet.is_file()
    frozen = json.loads((FIXTURES / "gate3.json").read_text(encoding="utf-8"))
    Gate3Result.model_validate(frozen)
