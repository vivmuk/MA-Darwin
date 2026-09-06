"""PDF parsing — text and asset extraction (PRD §7.1 / Prompt 2)."""

from __future__ import annotations

from pathlib import Path

from app.models.document import ExtractedAsset, PageText, ParsedDocument


def extract_pages(pdf_path: Path | str) -> list[PageText]:
    """Extract full text per page with 1-based page numbers preserved.

    Parameters
    ----------
    pdf_path:
        Path to the source research PDF.

    Returns
    -------
    list[PageText]
        One entry per page, in document order.
    """
    raise NotImplementedError


def extract_assets(pdf_path: Path | str, output_dir: Path | str) -> list[ExtractedAsset]:
    """Extract embedded figures and tables as PNGs with captions and page numbers.

    Assets are written under ``output_dir`` (typically ``runs/{run_id}/assets/``).

    Parameters
    ----------
    pdf_path:
        Path to the source research PDF.
    output_dir:
        Directory that will receive PNG files and caption sidecars.

    Returns
    -------
    list[ExtractedAsset]
        Metadata for each written asset, including relative ``path``.
    """
    raise NotImplementedError


def parse_pdf(pdf_path: Path | str, assets_dir: Path | str, *, paper_id: str) -> ParsedDocument:
    """Run full PDF parse: pages + assets into a single ``ParsedDocument``.

    Parameters
    ----------
    pdf_path:
        Path to the source research PDF.
    assets_dir:
        Directory for extracted figure/table PNGs.
    paper_id:
        Stable paper identifier stored on the result.

    Returns
    -------
    ParsedDocument
        Combined page text and asset inventory.
    """
    raise NotImplementedError
