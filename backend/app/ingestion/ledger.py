"""Claim ledger and numbers index builders (PRD §7.1 / Prompt 2)."""

from __future__ import annotations

from pathlib import Path

from app.models.claim import ClaimLedger
from app.models.document import PageText
from app.models.numbers import NumbersIndex


def build_numbers_index(pages: list[PageText], *, paper_id: str) -> NumbersIndex:
    """Deterministically extract every numeral with sentence, unit, and page.

    This index is the ground truth later used by Gate 1 ``number_sweep``.

    Parameters
    ----------
    pages:
        Per-page text from ``pdf_parser.extract_pages``.
    paper_id:
        Paper identifier written onto the artifact.

    Returns
    -------
    NumbersIndex
        Artifact suitable for ``numbers_index.json``.
    """
    raise NotImplementedError


def extract_claims(
    pages: list[PageText],
    numbers_index: NumbersIndex,
    *,
    paper_id: str,
    prompt_path: Path | str | None = None,
) -> ClaimLedger:
    """LLM-assisted claim extraction into ``ClaimLedgerEntry`` records.

    Parameters
    ----------
    pages:
        Per-page source text.
    numbers_index:
        Deterministic number index to ground numeric fields.
    paper_id:
        Paper identifier written onto the ledger.
    prompt_path:
        Optional override for ``prompts/ledger_extract.md``.

    Returns
    -------
    ClaimLedger
        Artifact suitable for ``ledger.json`` (pre-validation).
    """
    raise NotImplementedError


def validate_verbatim(ledger: ClaimLedger, pages: list[PageText]) -> ClaimLedger:
    """Reject entries whose ``verbatim`` is not found in page text (normalized whitespace).

    Failing entries are dropped and must be logged by the caller; they are never
    silently kept.

    Parameters
    ----------
    ledger:
        Candidate ledger from ``extract_claims``.
    pages:
        Source page text used for substring checks.

    Returns
    -------
    ClaimLedger
        Ledger containing only entries that pass verbatim validation.
    """
    raise NotImplementedError


def build_ledger(
    pdf_path: Path | str,
    *,
    paper_id: str,
    assets_dir: Path | str | None = None,
) -> tuple[ClaimLedger, NumbersIndex]:
    """End-to-end ingestion: parse PDF, build numbers index, extract and validate claims.

    Parameters
    ----------
    pdf_path:
        Source research PDF.
    paper_id:
        Stable paper id for artifacts.
    assets_dir:
        Optional directory for figure/table extraction.

    Returns
    -------
    tuple[ClaimLedger, NumbersIndex]
        Validated ledger and numbers index ready to write.
    """
    raise NotImplementedError


def write_ledger_artifacts(
    output_dir: Path | str,
    ledger: ClaimLedger,
    numbers_index: NumbersIndex,
) -> tuple[Path, Path]:
    """Write ``ledger.json`` and ``numbers_index.json`` under ``output_dir``.

    Parameters
    ----------
    output_dir:
        Destination directory (typically ``runs/{run_id}/``).
    ledger:
        Validated claim ledger.
    numbers_index:
        Deterministic numbers index.

    Returns
    -------
    tuple[Path, Path]
        Paths to ``ledger.json`` and ``numbers_index.json``.
    """
    raise NotImplementedError
