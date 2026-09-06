"""PDF parsing — text and asset extraction (PRD §7.1 / Prompt 2)."""

from __future__ import annotations

import logging
import re
from pathlib import Path

import fitz  # pymupdf

from app.models.document import ExtractedAsset, PageText, ParsedDocument

logger = logging.getLogger(__name__)

_CAPTION_RE = re.compile(
    r"(?P<label>(?:Figure|Fig\.?|Table|Tbl\.?)\s+\d+[A-Za-z]?)"
    r"[.\-:—–]?\s*(?P<rest>[^\n]{0,240})",
    re.IGNORECASE,
)
_MIN_IMAGE_PX = 20


def extract_pages(pdf_path: Path | str) -> list[PageText]:
    """Extract full text per page with 1-based page numbers preserved."""
    path = Path(pdf_path)
    if not path.is_file():
        raise FileNotFoundError(f"PDF not found: {path}")

    doc = fitz.open(path)
    try:
        pages: list[PageText] = []
        for index, page in enumerate(doc, start=1):
            pages.append(PageText(page=index, text=page.get_text("text") or ""))
        return pages
    finally:
        doc.close()


def extract_assets(pdf_path: Path | str, output_dir: Path | str) -> list[ExtractedAsset]:
    """Extract embedded figures and tables as PNGs with captions and page numbers."""
    path = Path(pdf_path)
    if not path.is_file():
        raise FileNotFoundError(f"PDF not found: {path}")
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(path)
    assets: list[ExtractedAsset] = []
    fig_n = 0
    tab_n = 0
    try:
        for page_no, page in enumerate(doc, start=1):
            captions = _captions_on_page(page.get_text("text") or "")
            fig_n, tab_n = _extract_images(
                doc, page, page_no, out, captions, assets, fig_n, tab_n
            )
            tab_n = _extract_tables(page, page_no, out, captions, assets, tab_n)
    finally:
        doc.close()
    return assets


def rasterize_pages(
    pdf_path: Path | str,
    output_dir: Path | str,
    *,
    dpi: int = 150,
) -> list[Path]:
    """Render each PDF page to ``page_XX.png`` for Venice vision OCR."""
    path = Path(pdf_path)
    if not path.is_file():
        raise FileNotFoundError(f"PDF not found: {path}")
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(path)
    paths: list[Path] = []
    try:
        for index, page in enumerate(doc, start=1):
            pix = page.get_pixmap(dpi=dpi, alpha=False)
            dest = out / f"page_{index:02d}.png"
            pix.save(dest)
            paths.append(dest)
    finally:
        doc.close()
    return paths


def parse_pdf(pdf_path: Path | str, assets_dir: Path | str, *, paper_id: str) -> ParsedDocument:
    """Run full PDF parse: pages + assets into a single ``ParsedDocument``."""
    pages = extract_pages(pdf_path)
    assets = extract_assets(pdf_path, assets_dir)
    return ParsedDocument(
        paper_id=paper_id,
        page_count=len(pages),
        pages=pages,
        assets=assets,
    )


def _captions_on_page(text: str) -> list[tuple[str, str]]:
    """Return (kind, caption) pairs found on a page."""
    found: list[tuple[str, str]] = []
    for match in _CAPTION_RE.finditer(text):
        label = match.group("label")
        rest = (match.group("rest") or "").strip()
        caption = f"{label} {rest}".strip()
        kind = "table" if label.lower().startswith("t") else "figure"
        found.append((kind, caption))
    return found


def _next_caption(captions: list[tuple[str, str]], kind: str) -> str:
    for i, (cap_kind, caption) in enumerate(captions):
        if cap_kind == kind:
            captions.pop(i)
            return caption
    return ""


def _rel_asset_path(output_dir: Path, filename: str) -> str:
    """Store path as assets/<file> when the folder is named assets."""
    if output_dir.name == "assets":
        return f"assets/{filename}"
    return filename


def _extract_images(
    doc: fitz.Document,
    page: fitz.Page,
    page_no: int,
    output_dir: Path,
    captions: list[tuple[str, str]],
    assets: list[ExtractedAsset],
    fig_n: int,
    tab_n: int,
) -> tuple[int, int]:
    for img_i, img in enumerate(page.get_images(full=True), start=1):
        xref = img[0]
        try:
            pix = fitz.Pixmap(doc, xref)
        except Exception as exc:  # noqa: BLE001 — skip unreadable image objects
            logger.warning("skip image xref=%s page=%s: %s", xref, page_no, exc)
            continue
        if pix.n - pix.alpha > 3:
            pix = fitz.Pixmap(fitz.csRGB, pix)
        if pix.width < _MIN_IMAGE_PX or pix.height < _MIN_IMAGE_PX:
            continue
        fig_n += 1
        filename = f"figure_p{page_no:02d}_{img_i:02d}.png"
        dest = output_dir / filename
        pix.save(dest)
        caption = _next_caption(captions, "figure")
        if caption:
            dest.with_suffix(".caption.txt").write_text(caption + "\n", encoding="utf-8")
        assets.append(
            ExtractedAsset(
                id=f"FIG-{fig_n:03d}",
                kind="figure",
                page=page_no,
                caption=caption,
                path=_rel_asset_path(output_dir, filename),
                width_px=pix.width,
                height_px=pix.height,
            )
        )
    return fig_n, tab_n


def _extract_tables(
    page: fitz.Page,
    page_no: int,
    output_dir: Path,
    captions: list[tuple[str, str]],
    assets: list[ExtractedAsset],
    tab_n: int,
) -> int:
    try:
        finder = page.find_tables()
    except Exception as exc:  # noqa: BLE001 — table finder is best-effort
        logger.info("table find skipped page=%s: %s", page_no, exc)
        return tab_n
    tables = getattr(finder, "tables", None) or []
    for table_i, table in enumerate(tables, start=1):
        bbox = getattr(table, "bbox", None)
        if not bbox:
            continue
        try:
            pix = page.get_pixmap(clip=fitz.Rect(bbox), dpi=150)
        except Exception as exc:  # noqa: BLE001
            logger.warning("skip table page=%s i=%s: %s", page_no, table_i, exc)
            continue
        tab_n += 1
        filename = f"table_p{page_no:02d}_{table_i:02d}.png"
        dest = output_dir / filename
        pix.save(dest)
        caption = _next_caption(captions, "table")
        if caption:
            dest.with_suffix(".caption.txt").write_text(caption + "\n", encoding="utf-8")
        assets.append(
            ExtractedAsset(
                id=f"TAB-{tab_n:03d}",
                kind="table",
                page=page_no,
                caption=caption,
                path=_rel_asset_path(output_dir, filename),
                width_px=pix.width,
                height_px=pix.height,
            )
        )
    return tab_n
