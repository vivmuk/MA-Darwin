"""Load Darwin ``skills/{version}`` plus ``skills/sundai-powerpoint`` for a run.

On Railway the working directory is the repo root (``/app``), so ``SKILLS_DIR``
resolves to ``/app/skills`` via ``paths.REPO_ROOT`` — not ``/backend/skills``.
Reads never require writing ``lineage/``; mutations still copy into lineage.
"""

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from app.paths import SKILLS_DIR

SKILL_ROOT = SKILLS_DIR / "sundai-powerpoint"
LINEAGE_DIR = SKILL_ROOT / "lineage"
ACTIVE_FILE = SKILL_ROOT / "ACTIVE"
_CONTENT = ("SKILL.md", "house-rules")

# Libraries / scripts the loaded skill will actually invoke during a run.
SKILL_TOOLS = (
    "pymupdf",
    "Venice /augment/text-parser",
    "Venice vision OCR",
    "Venice chat planner",
    "python-pptx",
    "add_editable_chart.py",
    "soffice",
    "cairosvg",
)


@dataclass(frozen=True)
class SkillBundle:
    """Both skills the orchestrator applies, plus metadata for SSE."""

    version: str
    name: str
    powerpoint_version: str
    text: str
    tools: tuple[str, ...] = SKILL_TOOLS
    darwin_path: str = ""
    powerpoint_path: str = ""
    loaded: bool = False

    def display_name(self) -> str:
        return f"{self.name} + sundai-powerpoint {self.powerpoint_version}"


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
    """PowerPoint skill dir. Prefer lineage; fall back to live SKILL.md (no write)."""
    name = version or read_active()
    lineage = LINEAGE_DIR / name
    if lineage.is_dir() and (lineage / "SKILL.md").is_file():
        return lineage
    if (SKILL_ROOT / "SKILL.md").is_file():
        return SKILL_ROOT
    ensure_lineage(version=name)
    return LINEAGE_DIR / name


def resolve_darwin_dir(version: str | None = None) -> Path | None:
    """``skills/v1`` (or ``skills/{version}``) Darwin generation skill."""
    name = version or read_active()
    candidate = SKILLS_DIR / name
    if candidate.is_dir() and (candidate / "SKILL.md").is_file():
        return candidate
    fallback = SKILLS_DIR / "v1"
    if fallback.is_dir() and (fallback / "SKILL.md").is_file():
        return fallback
    return None


def _read_dir_skill(root: Path) -> str:
    parts: list[str] = []
    skill_md = root / "SKILL.md"
    if skill_md.is_file():
        parts.append(skill_md.read_text(encoding="utf-8"))
    for name in ("house_rules.md", "style_rules.md"):
        path = root / name
        if path.is_file():
            parts.append(f"\n\n# {path.stem}\n\n{path.read_text(encoding='utf-8')}")
    rules = root / "house-rules"
    if rules.is_dir():
        for path in sorted(rules.glob("*.md")):
            if path.name.lower() == "readme.md":
                continue
            parts.append(f"\n\n# House rule: {path.stem}\n\n{path.read_text(encoding='utf-8')}")
    return "\n".join(parts)


def _frontmatter_field(text: str, key: str, default: str = "") -> str:
    fence = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not fence:
        return default
    block = fence.group(1)
    match = re.search(rf"(?:^|\n){re.escape(key)}:\s*[\"']?([^\n\"']+)", block)
    return (match.group(1).strip() if match else default) or default


def load_skill_bundle(version: str | None = None) -> SkillBundle:
    """Load Darwin + sundai-powerpoint skill text for planning and SSE."""
    name = version or read_active()
    darwin = resolve_darwin_dir(name)
    powerpoint = resolve_skill_dir(name)
    chunks: list[str] = []
    darwin_path = ""
    if darwin is not None:
        darwin_path = str(darwin)
        chunks.append(_read_dir_skill(darwin))
    ppt_text = _read_dir_skill(powerpoint) if powerpoint.is_dir() else ""
    if ppt_text:
        chunks.append(ppt_text)
    ppt_version = "3.2.0-darwin"
    meta_ver = re.search(r'version:\s*["\']([^"\']+)["\']', ppt_text)
    if meta_ver:
        ppt_version = meta_ver.group(1)
    darwin_name = "MA-Darwin"
    if darwin is not None:
        head = (darwin / "SKILL.md").read_text(encoding="utf-8")[:200]
        title = re.search(r"^#\s+(.+)$", head, re.MULTILINE)
        if title:
            darwin_name = title.group(1).strip()
    text = "\n\n".join(chunk for chunk in chunks if chunk.strip())
    return SkillBundle(
        version=name,
        name=darwin_name,
        powerpoint_version=ppt_version or "3.2.0-darwin",
        text=text,
        darwin_path=darwin_path,
        powerpoint_path=str(powerpoint) if powerpoint.is_dir() else "",
        loaded=bool(text.strip()),
    )


def load_skill_text(version: str | None = None) -> str:
    """SKILL.md + house-rules for the Venice planner system prompt."""
    return load_skill_bundle(version).text


def list_versions() -> list[str]:
    found: set[str] = set()
    if LINEAGE_DIR.is_dir():
        found.update(
            p.name
            for p in LINEAGE_DIR.iterdir()
            if p.is_dir() and re.fullmatch(r"v\d+", p.name) and (p / "SKILL.md").is_file()
        )
    if (SKILLS_DIR / "v1" / "SKILL.md").is_file():
        found.add("v1")
    return sorted(found) or ["v1"]


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
