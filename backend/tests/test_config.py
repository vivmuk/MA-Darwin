# Config key presence tests for all frozen YAML contracts.

from __future__ import annotations

from pathlib import Path

import yaml

from app.config import load_defaults
from app.paths import CONFIG_DIR

REQUIRED_DEFAULTS = {
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
    for key, expected in REQUIRED_DEFAULTS.items():
        assert key in cfg, f"missing threshold {key}"
        assert cfg[key] == expected, f"{key}: {cfg[key]!r} != {expected!r}"


def test_rubric_yaml_has_criteria() -> None:
    data = yaml.safe_load((CONFIG_DIR / "rubric.yaml").read_text(encoding="utf-8"))
    assert data["total_points"] == 100
    assert len(data["slide_criteria"]) >= 8
    assert len(data["deck_criteria"]) >= 2
    for criterion in data["slide_criteria"] + data["deck_criteria"]:
        assert "id" in criterion and "weight" in criterion and "anchors" in criterion


def test_compliance_yaml_has_blocklist() -> None:
    data = yaml.safe_load((CONFIG_DIR / "compliance.yaml").read_text(encoding="utf-8"))
    assert "proven" in data["promotional_blocklist"]
    assert "secondary_endpoint" in data["endpoint_labels"]
    assert "relative_tolerance" in data["number_sweep"]


def test_fonts_yaml_lists_required_fonts() -> None:
    data = yaml.safe_load((CONFIG_DIR / "fonts.yaml").read_text(encoding="utf-8"))
    assert isinstance(data["required_fonts"], list)
    assert len(data["required_fonts"]) >= 1
