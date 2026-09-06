"""pptx → PDF → PNG render pipeline (PRD §7.5 / Prompt 3)."""

from __future__ import annotations

from pathlib import Path

from app.models.run import RenderResult


def pptx_to_pdf(pptx_path: Path | str, output_pdf: Path | str) -> Path:
    """Convert a deck to PDF via headless LibreOffice.

    Parameters
    ----------
    pptx_path:
        Input ``.pptx`` path.
    output_pdf:
        Destination ``.pdf`` path.

    Returns
    -------
    Path
        Path to the written PDF.
    """
    raise NotImplementedError


def pdf_to_pngs(pdf_path: Path | str, output_dir: Path | str, *, dpi: int = 150) -> list[Path]:
    """Rasterize each PDF page to ``slide_01.png`` … at the given DPI.

    Parameters
    ----------
    pdf_path:
        Input PDF (typically from ``pptx_to_pdf``).
    output_dir:
        Directory for PNG outputs (typically ``round_n/slides/``).
    dpi:
        Render resolution; minimum 150 per PRD.

    Returns
    -------
    list[Path]
        Ordered paths to written slide PNGs.
    """
    raise NotImplementedError


def render_deck(
    pptx_path: Path | str,
    output_dir: Path | str,
    *,
    dpi: int = 150,
) -> RenderResult:
    """Full render: pptx → PDF → per-slide PNGs under ``output_dir``.

    Writes ``deck.pdf`` and ``slides/slide_XX.png`` beside each other.

    Parameters
    ----------
    pptx_path:
        Generated deck path.
    output_dir:
        Round output directory ``runs/{run_id}/round_{n}/``.
    dpi:
        Raster DPI (default 150).

    Returns
    -------
    RenderResult
        PDF path, slide image paths, and DPI used.
    """
    raise NotImplementedError
