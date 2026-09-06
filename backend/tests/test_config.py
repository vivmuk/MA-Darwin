"""Tests for defaults.yaml thresholds named in the PRD."""

from __future__ import annotations

from app.config import load_defaults

REQUIRED = {
    "promotion_threshold": 3,
    "max_rounds": 6,
    "max_auto_rounds": 2,
    "judge_threshold": 75,
    "regression_tolerance": 2,
    "max_mutations_per_round": 2,
    "min_font_pt": 14,
    "min_contrast": 4.5,
}


def test_defaults_yaml_has_prd_thresholds() -> None:
    cfg = load_defaults()
    for key, expected in REQUIRED.items():
        assert key in cfg, f"missing threshold {key}"
        assert cfg[key] == expected, f"{key}: {cfg[key]!r} != {expected!r}"
