"""Versioned copies of ``skills/sundai-powerpoint`` used by the Darwin loop."""

from __future__ import annotations

import re
import shutil
from pathlib import Path

from app.paths import SKILLS_DIR

SKILL_ROOT = SKILLS_DIR / "sundai-powerpoint"
LINEAGE_DIR = SKILL_ROOT / "lineage"
ACTIVE_FILE = SKILL_ROOT / "ACTIVE"
_CONTENT = ("SKILL.md", "house-rules")


def ensure_lineage(*, version: str = "v1") -> Path:
    """Guarantee ``lineage/{version}`` exists with SKILL.md + house-rules."""
    dest = LINEAGE_DIR / version
    if dest.is_dir() and (dest / "SKILL.md").is_file():
        _write_active(version)
        return dest
    dest.mkdir(parents=True, exist_ok=True)
    skill_md = SKILL_ROOT / "SKILL.md"
    if skill_md.is_file():
        shutil.copy2(skill_md, dest / "SKILL.md")
    rules = SKILL_ROOT / "house-rules"
    if rules.is_dir():
        target = dest / "house-rules"
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(rules, target)
    _write_active(version)
    return dest


def set_active(version: str) -> str:
    _write_active(version)
    return version


def read_active() -> str:
    if ACTIVE_FILE.is_file():
        value = ACTIVE_FILE.read_text(encoding="utf-8").strip()
        if value:
            return value
    return "v1"


def _write_active(version: str) -> None:
    ACTIVE_FILE.parent.mkdir(parents=True, exist_ok=True)
    ACTIVE_FILE.write_text(version + "\n", encoding="utf-8")


def resolve_skill_dir(version: str | None = None) -> Path:
    """Directory whose SKILL.md is the Darwin source of truth."""
    name = version or read_active()
    lineage = LINEAGE_DIR / name
    if lineage.is_dir() and (lineage / "SKILL.md").is_file():
        return lineage
    ensure_lineage(version=name)
    return LINEAGE_DIR / name


def load_skill_text(version: str | None = None) -> str:
    """SKILL.md + house-rules for the Venice planner system prompt."""
    root = resolve_skill_dir(version)
    parts: list[str] = []
    skill_md = root / "SKILL.md"
    if skill_md.is_file():
        parts.append(skill_md.read_text(encoding="utf-8"))
    rules = root / "house-rules"
    if rules.is_dir():
        for path in sorted(rules.glob("*.md")):
            if path.name.lower() == "readme.md":
                continue
            parts.append(f"\n\n# House rule: {path.stem}\n\n{path.read_text(encoding='utf-8')}")
    return "\n".join(parts) if parts else ""


def list_versions() -> list[str]:
    if not LINEAGE_DIR.is_dir():
        return ["v1"]
    found = sorted(
        p.name
        for p in LINEAGE_DIR.iterdir()
        if p.is_dir() and re.fullmatch(r"v\d+", p.name) and (p / "SKILL.md").is_file()
    )
    return found or ["v1"]


def next_version() -> str:
    nums = [int(name[1:]) for name in list_versions() if name[1:].isdigit()]
    return f"v{(max(nums) if nums else 0) + 1}"


def apply_mutations(suggestions: list[str], *, from_version: str | None = None) -> str:
    """Copy the active skill, append Darwin mutations, make the copy current."""
    source_name = from_version or read_active()
    source = resolve_skill_dir(source_name)
    dest_name = next_version()
    dest = LINEAGE_DIR / dest_name
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True, exist_ok=True)
    skill_md = source / "SKILL.md"
    if skill_md.is_file():
        shutil.copy2(skill_md, dest / "SKILL.md")
    rules_src = source / "house-rules"
    rules_dest = dest / "house-rules"
    if rules_src.is_dir():
        shutil.copytree(rules_src, rules_dest)
    else:
        rules_dest.mkdir(parents=True, exist_ok=True)
    mutations = rules_dest / "darwin-mutations.md"
    existing = mutations.read_text(encoding="utf-8") if mutations.is_file() else "# Darwin mutations\n"
    block = "\n".join(f"- {item.strip()}" for item in suggestions if item.strip())
    mutations.write_text(
        existing.rstrip() + f"\n\n## {dest_name}\n\n{block}\n",
        encoding="utf-8",
    )
    _write_active(dest_name)
    return dest_name


def scripts_dir() -> Path:
    return SKILL_ROOT / "scripts"
