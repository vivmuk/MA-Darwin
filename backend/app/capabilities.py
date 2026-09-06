"""Runtime capability report for deck generation (local + Railway)."""

from __future__ import annotations

import importlib
import os
import shutil
from typing import Any


def deck_capabilities() -> dict[str, Any]:
    packages = {
        "python-pptx": _mod("pptx"),
        "numpy": _mod("numpy"),
        "pillow": _mod("PIL"),
        "matplotlib": _mod("matplotlib"),
        "pymupdf": _mod("fitz"),
        "pypdf": _mod("pypdf"),
        "pdfplumber": _mod("pdfplumber"),
        "cairosvg": _mod("cairosvg"),
        "reportlab": _mod("reportlab"),
        "lxml": _mod("lxml"),
        "httpx": _mod("httpx"),
    }
    soffice = shutil.which("soffice") or shutil.which("soffice.exe")
    from app.generation.skill_lineage import load_skill_bundle
    from app.llm_env import get_llm_settings

    bundle = load_skill_bundle("v1")
    llm = get_llm_settings()
    return {
        "packages": packages,
        "soffice": bool(soffice),
        "soffice_path": soffice,
        "chart_path": "editable-ooxml-first",
        "llm_brain": (llm.model if llm else "unconfigured"),
        "llm_provider": (llm.provider if llm else None),
        "skill_loaded": bundle.loaded,
        "skill_name": bundle.display_name(),
        "skill_version": bundle.version,
        "skill_tools": list(bundle.tools),
        "darwin_path": bundle.darwin_path,
        "powerpoint_path": bundle.powerpoint_path,
        "runs_dir": os.environ.get("MA_DARWIN_RUNS_DIR") or "runs",
    }


def _mod(name: str) -> bool:
    try:
        importlib.import_module(name)
        return True
    except Exception:
        return False
