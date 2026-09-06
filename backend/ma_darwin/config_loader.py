"""Load YAML config from the repo `config/` directory.

Thresholds, weights, blocklists, and rubric anchors must live in YAML —
never as magic numbers in Python modules.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = REPO_ROOT / "config"
BLUEPRINTS_DIR = REPO_ROOT / "blueprints"
SKILLS_DIR = REPO_ROOT / "skills"
PROMPTS_DIR = REPO_ROOT / "prompts"
RUNS_DIR = REPO_ROOT / "runs"


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Config file not found: {path}")
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"Config root must be a mapping: {path}")
    return data


@lru_cache(maxsize=None)
def load_thresholds() -> dict[str, Any]:
    return _read_yaml(CONFIG_DIR / "thresholds.yaml")


@lru_cache(maxsize=None)
def load_compliance() -> dict[str, Any]:
    return _read_yaml(CONFIG_DIR / "compliance.yaml")


@lru_cache(maxsize=None)
def load_gate3_rubric() -> dict[str, Any]:
    return _read_yaml(CONFIG_DIR / "gate3_rubric.yaml")


def load_blueprint(blueprint_id: str) -> dict[str, Any]:
    path = BLUEPRINTS_DIR / f"{blueprint_id}.json"
    if not path.is_file():
        raise FileNotFoundError(f"Blueprint not found: {path}")
    import json

    with path.open(encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"Blueprint root must be a mapping: {path}")
    return data


def load_prompt(name: str) -> str:
    """Load a prompt markdown file from prompts/. Never inline long prompts."""
    path = PROMPTS_DIR / name
    if not path.suffix:
        path = path.with_suffix(".md")
    if not path.is_file():
        raise FileNotFoundError(f"Prompt not found: {path}")
    return path.read_text(encoding="utf-8")


def clear_config_cache() -> None:
    load_thresholds.cache_clear()
    load_compliance.cache_clear()
    load_gate3_rubric.cache_clear()
