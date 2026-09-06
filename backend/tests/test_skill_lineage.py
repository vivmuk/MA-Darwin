"""Skill loader must find Darwin v1 + sundai-powerpoint from the repo root."""

from __future__ import annotations

from pathlib import Path

from app.generation.skill_lineage import load_skill_bundle, load_skill_text
from app.paths import REPO_ROOT, SKILLS_DIR


def test_skill_bundle_loads_both_skills() -> None:
    bundle = load_skill_bundle("v1")
    assert bundle.loaded is True
    assert (SKILLS_DIR / "v1" / "SKILL.md").is_file()
    assert (SKILLS_DIR / "sundai-powerpoint" / "SKILL.md").is_file()
    text = bundle.text
    assert "Every text run on a slide MUST map" in text
    assert "sundai-powerpoint" in text.lower() or "editable" in text.lower()
    assert "python-pptx" in bundle.tools
    assert "soffice" in bundle.tools
    assert bundle.darwin_path.endswith("v1") or "skills" in bundle.darwin_path.replace("\\", "/")
    # Railway copies /app/skills from repo root, not /backend/skills.
    assert SKILLS_DIR == REPO_ROOT / "skills"


def test_load_skill_text_is_nonempty() -> None:
    assert len(load_skill_text("v1")) > 500


def test_propose_skill_version_does_not_overwrite_v1(tmp_path: Path) -> None:
    from app.generation.skill_lineage import propose_skill_version, read_active

    v1 = (SKILLS_DIR / "v1" / "SKILL.md").read_text(encoding="utf-8")
    active_before = read_active()
    version = propose_skill_version(
        ["Require an editable OOXML chart on every quantitative slide."],
        from_version="v1",
        run_dir=tmp_path / "run",
    )
    assert version != "v1"
    assert (SKILLS_DIR / "v1" / "SKILL.md").read_text(encoding="utf-8") == v1
    assert read_active() == active_before
    proposal = tmp_path / "run" / "skill_proposals" / version / "SKILL.md"
    assert proposal.is_file()
    mutations = (tmp_path / "run" / "skill_proposals" / version / "darwin-mutations.md").read_text(
        encoding="utf-8"
    )
    assert "editable OOXML chart" in mutations
