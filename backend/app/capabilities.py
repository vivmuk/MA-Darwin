"""Runtime capability report for deck generation (local + Railway)."""

from __future__ import annotations

import importlib
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
    return {
        "packages": packages,
        "soffice": bool(soffice),
        "soffice_path": soffice,
        "chart_path": "editable-ooxml-first",
        "llm_brain": "venice claude-opus-4-8",
    }


def _mod(name: str) -> bool:
    try:
        importlib.import_module(name)
        return True
    except Exception:
        return False
