"""Ingestion tests — fixtures are frozen inputs; PDFs are built in tmp_path."""

from __future__ import annotations

import json
from pathlib import Path

import fitz
import pytest

from app.cli import main
from app.ingestion.ledger import (
    build_numbers_index,
    extract_claims,
    validate_verbatim,
    write_ledger_artifacts,
)
from app.ingestion.pdf_parser import extract_pages, parse_pdf
from app.models.claim import ClaimLedger, ClaimLedgerEntry, ClaimType, EvidenceClass
from app.models.document import PageText
from app.storage.run_store import RunStore

FIXTURES = Path(__file__).resolve().parent / "fixtures"

# Three synthetic trial-style papers. Ground-truth numerals are listed per paper
# as (value, page). Used to score numbers_index recall — not live module output.
PAPER_SPECS: list[tuple[str, list[str], list[tuple[float, int]]]] = [
    (
        "paper_a_hfref",
        [
            "Methods. A total of N=420 patients were randomized. Mean age was 64.2 years.",
            "Results. The primary endpoint was met (HR 0.78, 95% CI 0.68-0.90; p=0.001).",
            "Safety. Serious adverse events occurred in 18.2% of treated patients.",
        ],
        [(420.0, 1), (64.2, 1), (0.78, 2), (95.0, 2), (0.68, 2), (0.90, 2), (0.001, 2), (18.2, 3)],
    ),
    (
        "paper_b_oncology",
        [
            "Study Design. We enrolled 156 adults across 12 centers for 24 months.",
            "Results. Overall survival hazard ratio was 0.62 (p=0.02). Objective response was 41%.",
        ],
        [(156.0, 1), (12.0, 1), (24.0, 1), (0.62, 2), (0.02, 2), (41.0, 2)],
    ),
    (
        "paper_c_safety",
        [
            "Background. Heart failure affects 6.7 million adults.",
            "Limitations. Follow-up was 8 weeks. Discontinuation occurred in 3.5% of patients.",
        ],
        [(6.7, 1), (8.0, 2), (3.5, 2)],
    ),
]


def _write_pdf(path: Path, pages: list[str]) -> Path:
    doc = fitz.open()
    for text in pages:
        page = doc.new_page()
        page.insert_text((72, 72), text)
    path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(path)
    doc.close()
    return path


def test_fixture_ledger_entries_have_claim_type_and_evidence_class() -> None:
    """Frozen fixture: zero entries have claim_type or evidence_class unset."""
    payload = json.loads((FIXTURES / "ledger.json").read_text(encoding="utf-8"))
    ledger = ClaimLedger.model_validate(payload)
    assert ledger.entries, "fixture ledger must contain entries"
    for entry in ledger.entries:
        assert entry.claim_type in ClaimType
        assert entry.evidence_class in EvidenceClass
        assert entry.claim_type.value
        assert entry.evidence_class.value


def test_heuristic_ledger_caps_claim_explosion() -> None:
    from app.ingestion.ledger import MAX_LEDGER_CLAIMS

    pages = [
        PageText(
            page=1,
            text=" ".join(f"This is a clinical outcome sentence number {i} with effect size." for i in range(80)),
        )
    ]
    index = build_numbers_index(pages, paper_id="boom")
    ledger = extract_claims(pages, index, paper_id="boom", llm_fn=lambda *_: [])
    assert len(ledger.entries) <= MAX_LEDGER_CLAIMS
    assert ledger.entries


def test_extracted_ledger_entries_have_required_enums(tmp_path: Path) -> None:
    """Built ledger: every entry has claim_type and evidence_class set."""
    paper_id, pages, _expected = PAPER_SPECS[0]
    pdf = _write_pdf(tmp_path / f"{paper_id}.pdf", pages)
    page_texts = extract_pages(pdf)
    index = build_numbers_index(page_texts, paper_id=paper_id)
    ledger = extract_claims(page_texts, index, paper_id=paper_id)
    ledger = validate_verbatim(ledger, page_texts)
    assert ledger.entries
    missing = [
        e.id
        for e in ledger.entries
        if e.claim_type is None or e.evidence_class is None
    ]
    assert missing == []
    for entry in ledger.entries:
        assert isinstance(entry.claim_type, ClaimType)
        assert isinstance(entry.evidence_class, EvidenceClass)


@pytest.mark.parametrize("paper_id,page_texts,expected", PAPER_SPECS)
def test_numbers_index_recall_three_papers(
    tmp_path: Path,
    paper_id: str,
    page_texts: list[str],
    expected: list[tuple[float, int]],
) -> None:
    pdf = _write_pdf(tmp_path / f"{paper_id}.pdf", page_texts)
    pages = extract_pages(pdf)
    assert [p.page for p in pages] == list(range(1, len(page_texts) + 1))
    index = build_numbers_index(pages, paper_id=paper_id)
    found = {(round(n.value, 6), n.page) for n in index.numbers}
    hits = [(value, page) for value, page in expected if (round(value, 6), page) in found]
    recall = len(hits) / len(expected)
    assert recall >= 0.95, f"{paper_id} recall={recall:.2%} missing={set(expected) - set(hits)}"
    for value, page in hits:
        matches = [n for n in index.numbers if round(n.value, 6) == round(value, 6) and n.page == page]
        assert matches[0].sentence
        assert matches[0].page == page


def test_verbatim_validation_rejects_and_keeps() -> None:
    pages = [
        PageText(
            page=1,
            text="This was a randomized, double-blind, placebo-controlled trial in adults with HFrEF.",
        )
    ]
    good = ClaimLedgerEntry(
        id="C-001",
        text="Randomized double-blind trial",
        verbatim="This was a randomized, double-blind, placebo-controlled trial in adults with HFrEF.",
        page=1,
        section="Methods",
        claim_type=ClaimType.VERBATIM,
        evidence_class=EvidenceClass.DESIGN,
    )
    bad = ClaimLedgerEntry(
        id="C-002",
        text="Invented claim",
        verbatim="Patients on Mars lived 400 years.",
        page=1,
        section="Results",
        claim_type=ClaimType.SYNTHESIZED,
        evidence_class=EvidenceClass.BACKGROUND,
    )
    ledger = ClaimLedger(paper_id="demo", entries=[good, bad], source_pages=1)
    kept = validate_verbatim(ledger, pages)
    ids = {e.id for e in kept.entries}
    assert "C-001" in ids
    assert "C-002" not in ids


def test_write_artifacts_match_contract_models(tmp_path: Path) -> None:
    fixture_ledger = ClaimLedger.model_validate(
        json.loads((FIXTURES / "ledger.json").read_text(encoding="utf-8"))
    )
    from app.models.numbers import NumbersIndex

    fixture_index = NumbersIndex.model_validate(
        json.loads((FIXTURES / "numbers_index.json").read_text(encoding="utf-8"))
    )
    ledger_path, index_path = write_ledger_artifacts(tmp_path, fixture_ledger, fixture_index)
    assert ledger_path.name == "ledger.json"
    assert index_path.name == "numbers_index.json"
    ClaimLedger.model_validate_json(ledger_path.read_text(encoding="utf-8"))
    NumbersIndex.model_validate_json(index_path.read_text(encoding="utf-8"))


def test_cli_extract_writes_ledger_and_index(tmp_path: Path) -> None:
    paper_id, pages, _ = PAPER_SPECS[0]
    pdf = _write_pdf(tmp_path / f"{paper_id}.pdf", pages)
    store = RunStore(root=tmp_path / "runs", db_path=tmp_path / "runs" / "t.sqlite3")
    run = store.create_run(paper_path=pdf, brief="8 slide MSL deck", paper_id=paper_id)
    code = main(["extract", "--run-id", run.id, "--runs-dir", str(tmp_path / "runs")])
    assert code == 0
    run_dir = store.run_dir(run.id)
    ledger = ClaimLedger.model_validate_json((run_dir / "ledger.json").read_text(encoding="utf-8"))
    assert (run_dir / "numbers_index.json").is_file()
    assert ledger.entries
    for entry in ledger.entries:
        assert entry.claim_type is not None
        assert entry.evidence_class is not None


def test_parse_pdf_extracts_pages_and_optional_figure(tmp_path: Path) -> None:
    pdf = tmp_path / "fig_paper.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Figure 1. Study design schematic. N=50 patients.")
    pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 80, 80), False)
    pix.clear_with(180)
    page.insert_image(fitz.Rect(72, 120, 200, 200), pixmap=pix)
    doc.save(pdf)
    doc.close()

    parsed = parse_pdf(pdf, tmp_path / "assets", paper_id="fig_paper")
    assert parsed.page_count == 1
    assert parsed.pages[0].page == 1
    assert "N=50" in parsed.pages[0].text
