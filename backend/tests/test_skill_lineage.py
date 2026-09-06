"""Skill loader must find Darwin v1 + sundai-powerpoint from the repo root."""

from __future__ import annotations

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
