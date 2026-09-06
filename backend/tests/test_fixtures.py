"""Validate frozen fixture artifacts against Pydantic models."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.models import (
    ClaimLedger,
    CommentsFile,
    Gate1Result,
    Gate2Result,
    Gate3Result,
    NumbersIndex,
    RunManifest,
    SkillRule,
    SlideMap,
    SlidePlan,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures"

CASES: list[tuple[str, type]] = [
    ("ledger.json", ClaimLedger),
    ("numbers_index.json", NumbersIndex),
    ("slide_plan.json", SlidePlan),
    ("slide_map.json", SlideMap),
    ("gate1.json", Gate1Result),
    ("gate2.json", Gate2Result),
    ("gate3.json", Gate3Result),
    ("comments.json", CommentsFile),
    ("skill_rule.json", SkillRule),
    ("manifest.json", RunManifest),
]


@pytest.mark.parametrize(("filename", "model"), CASES, ids=[c[0] for c in CASES])
def test_fixture_validates(filename: str, model: type) -> None:
    path = FIXTURES / filename
    assert path.is_file(), f"missing fixture: {path}"
    payload = json.loads(path.read_text(encoding="utf-8"))
    parsed = model.model_validate(payload)
    # Round-trip keeps the contract stable for parallel agents.
    again = model.model_validate(json.loads(parsed.model_dump_json()))
    assert again == parsed


def test_all_artifact_fixtures_present() -> None:
    expected = {name for name, _ in CASES}
    found = {p.name for p in FIXTURES.glob("*.json")}
    assert expected <= found
