"""Load YAML config from backend/config/."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from app.paths import CONFIG_DIR


@lru_cache(maxsize=4)
def load_defaults(path: Path | None = None) -> dict[str, Any]:
    cfg_path = Path(path) if path is not None else CONFIG_DIR / "defaults.yaml"
    with cfg_path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    if not isinstance(data, dict):
        raise ValueError(f"defaults config must be a mapping: {cfg_path}")
    return data


def get_threshold(name: str, default: Any = None) -> Any:
    return load_defaults().get(name, default)
