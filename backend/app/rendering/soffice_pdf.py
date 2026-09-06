"""LibreOffice ``soffice`` pptx → PDF for in-browser preview."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


def soffice_binary() -> str | None:
    return shutil.which("soffice") or shutil.which("soffice.exe")


def convert_pptx_to_pdf(pptx_path: Path | str, dest: Path | str) -> Path | None:
    """Convert ``deck.pptx`` with LibreOffice. Returns dest or None if skipped."""
    src = Path(pptx_path)
    out = Path(dest)
    exe = soffice_binary()
    if exe is None:
        logger.info("soffice not on PATH — skipping pptx→pdf preview")
        return None
    if not src.is_file():
        logger.warning("pptx missing for soffice convert: %s", src)
        return None
    env = os.environ.copy()
    env["SAL_USE_VCLPLUGIN"] = "svp"
    try:
        with tempfile.TemporaryDirectory(prefix="lo_profile_") as profile:
            with tempfile.TemporaryDirectory(prefix="lo_out_") as tmp:
                args = [
                    exe,
                    f"-env:UserInstallation={Path(profile).as_uri()}",
                    "--headless",
                    "--nologo",
                    "--nofirststartwizard",
                    "--convert-to",
                    "pdf",
                    "--outdir",
                    tmp,
                    str(src),
                ]
                subprocess.run(args, env=env, capture_output=True, timeout=180, check=False)
                produced = Path(tmp) / f"{src.stem}.pdf"
                if not produced.is_file():
                    logger.warning("soffice did not write %s", produced)
                    return None
                out.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(produced, out)
                return out
    except Exception as exc:  # noqa: BLE001
        logger.warning("soffice convert failed: %s", exc)
        return None
