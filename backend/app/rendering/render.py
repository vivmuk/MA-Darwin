"""pptx → PDF → PNG render pipeline (PRD §7.5 / Prompt 3)."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pymupdf

from app.models.run import RenderResult

_SOFFICE_CANDIDATES = (
    Path(r"C:\Program Files\LibreOffice\program\soffice.exe"),
    Path(r"C:\Program Files (x86)\LibreOffice\program\soffice.exe"),
    Path("/usr/bin/soffice"),
    Path("/usr/bin/libreoffice"),
    Path("/usr/lib/libreoffice/program/soffice"),
    Path("/Applications/LibreOffice.app/Contents/MacOS/soffice"),
)


def _find_soffice() -> Path:
    env = os.environ.get("LIBREOFFICE_BIN") or os.environ.get("SOFFICE_BIN")
    if env:
        path = Path(env)
        if path.is_file():
            return path
    for name in ("soffice", "soffice.exe", "libreoffice"):
        found = shutil.which(name)
        if found:
            return Path(found)
    for candidate in _SOFFICE_CANDIDATES:
        if candidate.is_file():
            return candidate
    raise RuntimeError(
        "LibreOffice (soffice) is not installed or not on PATH. "
        "The render pipeline requires headless LibreOffice to convert pptx → PDF. "
        "Set LIBREOFFICE_BIN to the soffice executable if it lives outside PATH."
    )


def pptx_to_pdf(pptx_path: Path | str, output_pdf: Path | str) -> Path:
    """Convert a deck to PDF via headless LibreOffice."""
    pptx = Path(pptx_path)
    if not pptx.is_file():
        raise FileNotFoundError(f"pptx not found: {pptx}")
    dest = Path(output_pdf)
    dest.parent.mkdir(parents=True, exist_ok=True)

    soffice = _find_soffice()
    # LibreOffice writes {stem}.pdf into --outdir; convert in dest.parent then rename.
    work_dir = dest.parent
    cmd = [
        str(soffice),
        "--headless",
        "--norestore",
        "--nolockcheck",
        "--nodefault",
        "--convert-to",
        "pdf",
        "--outdir",
        str(work_dir),
        str(pptx.resolve()),
    ]
    completed = subprocess.run(
        cmd,
        check=False,
        capture_output=True,
        text=True,
        timeout=180,
    )
    produced = work_dir / f"{pptx.stem}.pdf"
    if completed.returncode != 0 or not produced.is_file():
        raise RuntimeError(
            "LibreOffice failed to convert pptx to PDF.\n"
            f"command: {cmd}\n"
            f"exit: {completed.returncode}\n"
            f"stdout: {completed.stdout}\n"
            f"stderr: {completed.stderr}"
        )
    if produced.resolve() != dest.resolve():
        if dest.exists():
            dest.unlink()
        shutil.move(str(produced), str(dest))
    return dest


def pdf_to_pngs(pdf_path: Path | str, output_dir: Path | str, *, dpi: int = 150) -> list[Path]:
    """Rasterize each PDF page to ``slide_01.png`` … at the given DPI."""
    pdf = Path(pdf_path)
    if not pdf.is_file():
        raise FileNotFoundError(f"pdf not found: {pdf}")
    if dpi < 150:
        raise ValueError(f"dpi must be >= 150 (PRD §7.5), got {dpi}")
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    doc = pymupdf.open(pdf)
    paths: list[Path] = []
    try:
        if doc.page_count < 1:
            raise RuntimeError(f"PDF has no pages: {pdf}")
        for index in range(doc.page_count):
            page = doc.load_page(index)
            pix = page.get_pixmap(dpi=dpi)
            dest = out_dir / f"slide_{index + 1:02d}.png"
            pix.save(str(dest))
            paths.append(dest)
    finally:
        doc.close()
    return paths


def render_deck(
    pptx_path: Path | str,
    output_dir: Path | str,
    *,
    dpi: int = 150,
) -> RenderResult:
    """Full render: pptx → PDF → per-slide PNGs under ``output_dir``.

    Writes ``deck.pdf`` and ``slides/slide_XX.png`` beside each other.
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    pdf_path = pptx_to_pdf(pptx_path, out / "deck.pdf")
    images = pdf_to_pngs(pdf_path, out / "slides", dpi=dpi)
    return RenderResult(
        pdf_path=str(pdf_path),
        slide_images=[str(p) for p in images],
        dpi=dpi,
    )
