"""Stubs exist with public signatures and raise NotImplementedError."""

from __future__ import annotations

import pytest

from app.evolution import credit, feedback_router, promotion, regression
from app.export import bundle
from app.gates import gate1_content, gate2_visual, gate3_judge
from app.generation import generator, planner
from app.ingestion import ledger, pdf_parser
from app import orchestrator
from app.rendering import font_check, render


@pytest.mark.parametrize(
    ("fn", "kwargs"),
    [
        (pdf_parser.extract_pages, {"pdf_path": "x.pdf"}),
        (ledger.build_numbers_index, {"pages": [], "paper_id": "p"}),
        (render.render_deck, {"pptx_path": "d.pptx", "output_dir": "."}),
        (font_check.check_required_fonts, {}),
        (
            planner.plan_slides,
            {
                "blueprint": None,
                "ledger": None,
                "brief": None,
                "skill_version": "v1",
            },
        ),
        (gate1_content.check_claim_mapping, {"slide_map": None}),
        (gate2_visual.check_shape_bounds, {"pptx_path": "d.pptx"}),
        (
            gate3_judge.load_rubric,
            {},
        ),
        (
            feedback_router.route_comment,
            {"comment": None, "run_id": "run_abcdef012345", "round_n": 1},
        ),
        (promotion.is_measurable_rule, {"text": "max 5 bullets"}),
        (
            credit.update_credits,
            {"active_rules": [], "previous_gate3": None, "current_gate3": None},
        ),
        (regression.load_regression_set, {"regression_dir": "."}),
        (bundle.export_allowed, {"run": None, "round_n": 1}),
        (orchestrator.run_round, {"run_id": "run_abcdef012345"}),
        (
            generator.generate_deck,
            {
                "blueprint": None,
                "ledger": None,
                "brief": None,
                "skill_version": "v1",
                "slide_plan": None,
                "output_dir": ".",
            },
        ),
    ],
)
def test_stubs_raise_not_implemented(fn, kwargs) -> None:
    with pytest.raises(NotImplementedError):
        fn(**kwargs)
