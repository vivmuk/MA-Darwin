"""Tests for config_loader — thresholds and blueprints load from disk."""

from __future__ import annotations

import pytest

from ma_darwin.config_loader import (
    load_blueprint,
    load_compliance,
    load_gate3_rubric,
    load_thresholds,
)


def test_thresholds_contain_gate3_pass_threshold() -> None:
    thresholds = load_thresholds()
    assert thresholds["gate3"]["pass_threshold"] == 75
    assert thresholds["rounds"]["max_rounds"] == 6
    assert thresholds["render"]["dpi"] == 150


def test_compliance_blocklist_non_empty() -> None:
    compliance = load_compliance()
    blocklist = compliance["promotional_blocklist"]
    assert "proven" in blocklist
    assert "breakthrough" in blocklist
    assert "primary_endpoint" in compliance["evidence_classes"]


def test_gate3_rubric_weights_sum_expected() -> None:
    rubric = load_gate3_rubric()
    slide_weights = sum(c["weight"] for c in rubric["slide_criteria"])
    deck_weights = sum(c["weight"] for c in rubric["deck_criteria"])
    # 15+15+10+10+15+10+8+5 = 88 slide; +7+5 deck = 100
    assert slide_weights + deck_weights == rubric["total_points"]


def test_msl_physician_8_blueprint_roles() -> None:
    bp = load_blueprint("msl_physician_8")
    assert bp["id"] == "msl_physician_8"
    assert bp["slide_count"] == 8
    roles = [s["role"] for s in bp["slides"]]
    assert roles[0] == "title"
    assert roles[-1] == "references"
    refs = bp["slides"][-1]
    assert refs.get("counts_against_slide_count") is False


def test_missing_blueprint_raises() -> None:
    with pytest.raises(FileNotFoundError):
        load_blueprint("does_not_exist")
