"""Extract the publication first: rasterize pages, Venice text-parser, vision OCR.

Scanned PDFs have no digital text layer. Venice ``/augment/text-parser`` does
not OCR; those pages go through Venice vision (``image_url``) on pymupdf rasters.
"""

from __future__ import annotations

import base64
import logging
from collections.abc import Callable
from pathlib import Path

from app.ingestion.pdf_parser import rasterize_pages
from app.llm_env import chat_text, llm_configured, venice_parse_document, vision_model
from app.models.document import PageText, ParsedDocument

logger = logging.getLogger(__name__)

SPARSE_CHARS = 80
MAX_OCR_PAGES = 40
_OCR_SYSTEM = (
    "You OCR one page of a scientific publication. Extract ALL visible text "
    "in reading order: headings, body, table cells, figure captions, footnotes, "
    "axis labels. Preserve numbers, units, CIs, and p-values exactly. "
    "Return plain text only. If the page is blank, return an empty string."
)


ProgressFn = Callable[[str, str, dict], None]


def merge_page_text(digital: str, ocr: str) -> str:
    """Keep the digital layer; append OCR when it adds unread content."""
    digital = (digital or "").strip()
    ocr = (ocr or "").strip()
    if not digital:
        return ocr
    if not ocr:
        return digital
    if ocr.lower() in digital.lower():
        return digital
    if len(ocr) < max(40, int(len(digital) * 0.35)):
        return digital
    return f"{digital}\n\n[OCR]\n{ocr}"


def ocr_page_image(image_path: Path | str, *, model: str | None = None) -> str:
    """Send one rasterized page to Venice vision and return extracted text."""
    path = Path(image_path)
    if not path.is_file():
        return ""
    raw = path.read_bytes()
    if not raw:
        return ""
    b64 = base64.b64encode(raw).decode("ascii")
    mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    user = [
        {"type": "text", "text": f"OCR this publication page ({path.name})."},
        {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
    ]
    return (chat_text(system=_OCR_SYSTEM, user=user, max_tokens=4096, temperature=0, model=model) or "").strip()


def enrich_document(
    pdf_path: Path | str,
    parsed: ParsedDocument,
    pages_dir: Path | str,
    *,
    on_progress: ProgressFn | None = None,
) -> ParsedDocument:
    """Rasterize pages, optionally OCR via Venice, merge into ``ParsedDocument``."""
    pdf = Path(pdf_path)
    out = Path(pages_dir)
    rasters: list[Path] = []
    try:
        rasters = rasterize_pages(pdf, out)
        if on_progress:
            on_progress("library_call", f"calling pymupdf to rasterize {len(rasters)} pages", {"tool": "pymupdf", "pages": len(rasters)})
    except Exception as exc:  # noqa: BLE001 — ingest must continue
        logger.warning("page rasterize failed: %s", exc)
        if on_progress:
            on_progress("ocr_started", f"Page rasterize failed ({exc}); using digital text only", {"pages": parsed.page_count})

    if on_progress:
        on_progress("ocr_started", "OCR in progress — Venice text-parser + vision", {"pages": parsed.page_count or len(rasters)})

    extra = ""
    if llm_configured() and pdf.is_file():
        if on_progress:
            on_progress("library_call", "calling Venice /augment/text-parser", {"tool": "Venice /augment/text-parser"})
        try:
            extra = venice_parse_document(pdf)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Venice text-parser failed: %s", exc)
            extra = ""

    by_page = {p.page: p.text for p in parsed.pages}
    page_count = max(parsed.page_count, len(rasters), max(by_page) if by_page else 0)
    merged: list[PageText] = []
    ocr_used = 0
    for index in range(1, page_count + 1):
        digital = by_page.get(index, "")
        ocr_text = ""
        raster = next((p for p in rasters if p.stem.endswith(f"{index:02d}") or p.stem.endswith(f"_{index:02d}")), None)
        if raster is None and index <= len(rasters):
            raster = rasters[index - 1]
        need_ocr = len(digital.strip()) < SPARSE_CHARS
        if llm_configured() and raster is not None and index <= MAX_OCR_PAGES:
            # Always OCR sparse pages; also OCR denser pages so figures/captions land.
            if on_progress:
                on_progress(
                    "ocr_page",
                    f"OCR page {index}/{page_count} via Venice vision",
                    {"slide": index, "slide_total": page_count, "pages": page_count, "tool": "Venice vision OCR"},
                )
            try:
                ocr_text = ocr_page_image(raster, model=vision_model())
                if ocr_text:
                    ocr_used += 1
            except Exception as exc:  # noqa: BLE001
                logger.warning("OCR page %s failed: %s", index, exc)
        elif on_progress:
            reason = "VENICE_API_KEY not set" if not llm_configured() else "no raster"
            on_progress(
                "ocr_page",
                f"Page {index}/{page_count}: digital text only ({reason})",
                {"slide": index, "slide_total": page_count, "pages": page_count},
            )
        text = merge_page_text(digital, ocr_text)
        if index == 1 and extra and extra not in text:
            text = merge_page_text(text, extra)
        merged.append(PageText(page=index, text=text))

    return parsed.model_copy(
        update={
            "page_count": len(merged),
            "pages": merged,
        }
    )
