"""Export bundle tests against frozen fixtures only."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from app.export.bundle import (
    BUNDLE_FILES,
    build_provenance_md,
    build_run_log,
    create_bundle,
    export_allowed,
)
from app.models.claim import ClaimLedger
from app.models.gates import Gate1Result, Gate2Result, Gate3Result, GateCheckResult
from app.models.run import Brief, MutationKind, MutationRecord, Round, Run, RunStatus
from app.models.slide import CommentsFile, SlideMap
from app.storage.run_store import RunStore

FIXTURES = Path(__file__).resolve().parent / "fixtures"
MIN_PDF = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"


def _load(name: str, model):
    return model.model_validate_json((FIXTURES / name).read_text(encoding="utf-8"))


def _exportable_round() -> Round:
    comments = _load("comments.json", CommentsFile).comments
    return Round(
        n=1,
        deck_path="round_1/deck.pptx",
        slide_images=[
            "slides/slide_01.png",
            "slides/slide_02.png",
            "slides/slide_03.png",
            "slides/slide_04.png",
        ],
        gate1=_load("gate1.json", Gate1Result),
        gate2=Gate2Result(passed=True, checks=[GateCheckResult(name="shape_bounds", passed=True)]),
        gate3=_load("gate3.json", Gate3Result),
        locked_slides=[1, 2, 3, 4],
        comments=comments,
        mutations=[
            MutationRecord(
                id="mut_1",
                kind=MutationKind.ONE_OFF,
                text="Tighten primary-result bullets",
                origin_comment_id="hc_1",
            )
        ],
    )


def _run_from_fixtures(rnd: Round | None = None) -> Run:
    rnd = rnd or _exportable_round()
    return Run(
        id="run_abcdef012345",
        paper_id="demo_trial_2024",
        brief=Brief(notes="Create an 8 slide MSL physician deck"),
        brief_text="Create an 8 slide MSL physician deck",
        skill_version="v1",
        blueprint_id="msl_physician_8",
        rounds=[rnd],
        status=RunStatus.AWAITING_REVIEW,
        best_round_n=1,
    )


def test_export_blocked_until_gates_pass_and_all_slides_locked() -> None:
    run = _run_from_fixtures()
    ok, _ = export_allowed(run, round_n=1)
    assert ok is True

    run.rounds[0].gate1 = Gate1Result(
        passed=False, checks=[GateCheckResult(name="claim_mapping", passed=False)]
    )
    ok, msg = export_allowed(run, round_n=1)
    assert ok is False
    assert "Gate 1" in msg

    run = _run_from_fixtures()
    run.rounds[0].gate2 = Gate2Result(
        passed=False, checks=[GateCheckResult(name="min_font_size", passed=False)]
    )
    ok, msg = export_allowed(run, round_n=1)
    assert ok is False
    assert "Gate 2" in msg

    run = _run_from_fixtures()
    run.rounds[0].locked_slides = [1, 2]
    ok, msg = export_allowed(run, round_n=1)
    assert ok is False
    assert "locked" in msg.lower()
    assert "3" in msg and "4" in msg


def test_provenance_covers_every_slide_map_text_from_fixtures() -> None:
    run = _run_from_fixtures()
    ledger = _load("ledger.json", ClaimLedger)
    slide_map = _load("slide_map.json", SlideMap)
    md = build_provenance_md(run, round_n=1, ledger=ledger, slide_map=slide_map)

    for entry in slide_map.entries:
        assert entry.text in md
        for cid in entry.claim_ids:
            assert cid in md
            claim = next(c for c in ledger.entries if c.id == cid)
            assert claim.verbatim in md
            assert f"Source page:** {claim.page}" in md or f"page:** {claim.page}" in md
            assert claim.claim_type.value in md

    assert "Gaps:** none" in md
    assert "UNMAPPED" not in md


def test_run_log_includes_rounds_mutations_comments() -> None:
    run = _run_from_fixtures()
    raw = build_run_log(run)
    payload = json.loads(raw)
    assert payload["run_id"] == run.id
    assert payload["skill_version"] == "v1"
    assert payload["created_at"]
    assert len(payload["rounds"]) == 1
    rnd = payload["rounds"][0]
    assert rnd["mutations"][0]["origin_comment_id"] == "hc_1"
    assert rnd["mutations"][0]["timestamp"]
    assert {c["id"] for c in rnd["comments"]} == {"hc_1", "hc_2"}


def test_create_bundle_zips_required_files(tmp_path: Path) -> None:
    pdf = tmp_path / "paper.pdf"
    pdf.write_bytes(MIN_PDF)
    store = RunStore(root=tmp_path / "runs", db_path=tmp_path / "t.sqlite3")
    created = store.create_run(paper_path=pdf, brief="Create an 8 slide MSL deck", run_id="run_abcdef012345")
    rnd = _exportable_round()
    created.rounds = [rnd]
    created.best_round_n = 1
    created.skill_version = "v1"
    store._persist_run(created)
    store.save_round(created.id, rnd)

    rdir = store.round_dir(created.id, 1)
    (store.run_dir(created.id) / "ledger.json").write_text(
        (FIXTURES / "ledger.json").read_text(encoding="utf-8"), encoding="utf-8"
    )
    (rdir / "slide_map.json").write_text(
        (FIXTURES / "slide_map.json").read_text(encoding="utf-8"), encoding="utf-8"
    )
    (rdir / "comments.json").write_text(
        (FIXTURES / "comments.json").read_text(encoding="utf-8"), encoding="utf-8"
    )
    (rdir / "deck.pptx").write_bytes(b"PK\x03\x04dummy-pptx")
    (rdir / "deck.pdf").write_bytes(MIN_PDF)
    rnd.deck_path = str(rdir / "deck.pptx")
    store._persist_run(store.get_run(created.id))

    result = create_bundle(created.id, round_n=1, store=store)
    zpath = Path(result.path)
    assert zpath.is_file()
    assert set(result.contents) == set(BUNDLE_FILES)

    with zipfile.ZipFile(zpath) as zf:
        names = set(zf.namelist())
        assert names == set(BUNDLE_FILES)
        for name in BUNDLE_FILES:
            info = zf.getinfo(name)
            assert info.file_size > 0
        provenance = zf.read("provenance.md").decode("utf-8")
        scores = json.loads(zf.read("scores.json"))
        skill = zf.read("skill_version.txt").decode("utf-8").strip()
        log = json.loads(zf.read("run_log.json"))

    slide_map = _load("slide_map.json", SlideMap)
    ledger = _load("ledger.json", ClaimLedger)
    for entry in slide_map.entries:
        assert entry.text in provenance
        for cid in entry.claim_ids:
            claim = next(c for c in ledger.entries if c.id == cid)
            assert claim.verbatim in provenance
            assert str(claim.page) in provenance
    assert scores["deck_score"] == 82.0
    assert skill == "v1"
    assert log["rounds"][0]["comments"]


def test_create_bundle_raises_when_blocked(tmp_path: Path) -> None:
    pdf = tmp_path / "paper.pdf"
    pdf.write_bytes(MIN_PDF)
    store = RunStore(root=tmp_path / "runs", db_path=tmp_path / "t.sqlite3")
    created = store.create_run(paper_path=pdf, brief="brief", run_id="run_abcdef012345")
    rnd = _exportable_round()
    rnd.locked_slides = []
    store.save_round(created.id, rnd)
    with pytest.raises(PermissionError, match="locked"):
        create_bundle(created.id, round_n=1, store=store)
