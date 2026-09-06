"""Repository path helpers."""

from __future__ import annotations

from pathlib import Path

# backend/app/paths.py → repo root is parents[2]
REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
CONFIG_DIR = BACKEND_DIR / "config"
PROMPTS_DIR = BACKEND_DIR / "prompts"
RUNS_DIR = REPO_ROOT / "runs"
BLUEPRINTS_DIR = REPO_ROOT / "blueprints"
SKILLS_DIR = REPO_ROOT / "skills"
