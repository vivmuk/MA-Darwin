"""Orchestrator stopping conditions and gate short-circuit (fixture-backed)."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.models.gates import Gate1Result, Gate2Result, Gate3Result, GateCheckResult
from app.models.run import Brief, Round, Run, RunStatus, StoppingReason
from app.orchestrator import check_stopping_conditions, should_auto_reiterate
from app.storage.run_store import RunStore


def _run(*rounds: Round, status: RunStatus = RunStatus.RUNNING, budget: float = 25.0) -> Run:
    return Run(
        id="run_abcdef012345",
        paper_id="demo",
        brief=Brief(),
        rounds=list(rounds),
        status=status,
        budget_usd=budget,
        auto_rounds_used=0,
    )


def _g3(score: float) -> Gate3Result:
    return Gate3Result(deck_score=score, worst_slide_score=score, passed=score >= 75)


def test_success_when_gates_pass_and_all_slides_locked() -> None:
    rnd = Round(
        n=1,
        slide_images=["s1.png", "s2.png"],
        gate1=Gate1Result(passed=True),
        gate2=Gate2Result(passed=True),
        gate3=_g3(80),
        locked_slides=[1, 2],
    )
    decision = check_stopping_conditions(_run(rnd))
    assert decision.halt is True
    assert decision.reason == StoppingReason.SUCCESS


def test_max_rounds_and_budget_and_plateau() -> None:
    rounds = [
        Round(n=i, gate3=_g3(70.0), gate1=Gate1Result(passed=True), gate2=Gate2Result(passed=True))
        for i in range(1, 7)
    ]
    assert check_stopping_conditions(_run(*rounds)).reason == StoppingReason.MAX_ROUNDS

    spent = Round(n=1, cost_usd=30.0, gate1=Gate1Result(passed=True), gate2=Gate2Result(passed=True))
    assert check_stopping_conditions(_run(spent, budget=25.0)).reason == StoppingReason.BUDGET

    plateau = [
        Round(n=1, gate3=_g3(80.0), gate1=Gate1Result(passed=True), gate2=Gate2Result(passed=True)),
        Round(n=2, gate3=_g3(80.2), gate1=Gate1Result(passed=True), gate2=Gate2Result(passed=True)),
        Round(n=3, gate3=_g3(80.4), gate1=Gate1Result(passed=True), gate2=Gate2Result(passed=True)),
    ]
    decision = check_stopping_conditions(_run(*plateau))
    assert decision.halt is True
    assert decision.reason == StoppingReason.PLATEAU


def test_auto_reiterate_only_below_threshold_with_budget() -> None:
    rnd = Round(
        n=1,
        gate1=Gate1Result(passed=True),
        gate2=Gate2Result(passed=True),
        gate3=_g3(60.0),
    )
    run = _run(rnd)
    assert should_auto_reiterate(run, rnd) is True
    assert should_auto_reiterate(run, rnd, judge_threshold=50) is False
    run.auto_rounds_used = 2
    assert should_auto_reiterate(run, rnd, max_auto_rounds=2) is False
    failed = Round(n=1, gate1=Gate1Result(passed=False, checks=[GateCheckResult(name="x", passed=False)]))
    assert should_auto_reiterate(_run(failed), failed) is False


def test_run_round_short_circuits_before_gate3(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.models.blueprint import Blueprint, BlueprintSlide
    from app.models.claim import ClaimLedger, ClaimType, EvidenceClass, ClaimLedgerEntry
    from app.models.document import ParsedDocument
    from app.models.numbers import NumbersIndex
    from app.models.run import GenerationResult
    from app.models.slide import SlideMap, SlidePlan
    from app import orchestrator

    pdf = tmp_path / "paper.pdf"
    pdf.write_bytes(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n")
    store = RunStore(root=tmp_path / "runs", db_path=tmp_path / "t.sqlite3")
    created = store.create_run(paper_path=pdf, brief="Create an 8 slide MSL deck")
    orchestrator.set_store(store)
    orchestrator.reset_runtime()

    monkeypatch.setattr(
        orchestrator,
        "load_blueprint",
        lambda _id: Blueprint(id="msl_physician_8", name="t", slides=[BlueprintSlide(role="title")]),
    )
    monkeypatch.setattr(
        orchestrator.pdf_parser,
        "parse_pdf",
        lambda *a, **k: ParsedDocument(paper_id="p", page_count=2, pages=[], assets=[]),
    )
    monkeypatch.setattr(
        orchestrator.ledger_mod,
        "build_ledger",
        lambda *a, **k: (
            ClaimLedger(
                paper_id="p",
                entries=[
                    ClaimLedgerEntry(
                        id="C-001",
                        text="t",
                        verbatim="t",
                        page=1,
                        claim_type=ClaimType.VERBATIM,
                        evidence_class=EvidenceClass.DESIGN,
                    )
                ],
            ),
            NumbersIndex(paper_id="p", numbers=[]),
        ),
    )
    monkeypatch.setattr(
        orchestrator.ledger_mod,
        "write_ledger_artifacts",
        lambda *a, **k: (tmp_path / "l.json", tmp_path / "n.json"),
    )
    monkeypatch.setattr(
        orchestrator.planner,
        "plan_slides",
        lambda **k: SlidePlan(blueprint_id="msl_physician_8", slides=[]),
    )
    monkeypatch.setattr(
        orchestrator.generator,
        "generate_deck",
        lambda **k: GenerationResult(
            deck_path=str(tmp_path / "d.pptx"),
            slide_map_path=str(tmp_path / "m.json"),
            slide_plan_path=str(tmp_path / "p.json"),
            slide_map=SlideMap(entries=[]),
        ),
    )
    monkeypatch.setattr(
        orchestrator.render_mod,
        "render_deck",
        lambda *a, **k: type("R", (), {"slide_images": ["s1.png"]})(),
    )
    monkeypatch.setattr(
        orchestrator.gate1_content,
        "run_gate1",
        lambda **k: Gate1Result(passed=False, checks=[GateCheckResult(name="claim_mapping", passed=False)]),
    )

    called = {"g2": False, "g3": False}

    def _g2(**k):
        called["g2"] = True
        return Gate2Result(passed=True)

    def _g3(**k):
        called["g3"] = True
        return Gate3Result(deck_score=80, worst_slide_score=80, passed=True)

    monkeypatch.setattr(orchestrator.gate2_visual, "run_gate2", _g2)
    monkeypatch.setattr(orchestrator.gate3_judge, "run_gate3", _g3)

    rnd = orchestrator.run_round(created.id, round_n=1)
    assert rnd.gate1 is not None and rnd.gate1.passed is False
    assert rnd.gate2 is None
    assert rnd.gate3 is None
    assert called["g2"] is False
    assert called["g3"] is False


def test_start_run_auto_false_sets_awaiting_review(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.models.blueprint import Blueprint, BlueprintSlide
    from app.models.claim import ClaimLedger, ClaimLedgerEntry, ClaimType, EvidenceClass
    from app.models.document import ParsedDocument
    from app.models.numbers import NumbersIndex
    from app.models.run import GenerationResult, RunStatus
    from app.models.slide import SlideMap, SlidePlan
    from app import orchestrator

    pdf = tmp_path / "paper.pdf"
    pdf.write_bytes(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n")
    store = RunStore(root=tmp_path / "runs", db_path=tmp_path / "t.sqlite3")
    created = store.create_run(paper_path=pdf, brief="Create an 8 slide MSL deck")
    orchestrator.set_store(store)
    orchestrator.reset_runtime()

    monkeypatch.setattr(
        orchestrator,
        "load_blueprint",
        lambda _id: Blueprint(id="msl_physician_8", name="t", slides=[BlueprintSlide(role="title")]),
    )
    monkeypatch.setattr(
        orchestrator.pdf_parser,
        "parse_pdf",
        lambda *a, **k: ParsedDocument(paper_id="p", page_count=2, pages=[], assets=[]),
    )
    monkeypatch.setattr(
        orchestrator.ledger_mod,
        "build_ledger",
        lambda *a, **k: (
            ClaimLedger(
                paper_id="p",
                entries=[
                    ClaimLedgerEntry(
                        id="C-001",
                        text="t",
                        verbatim="t",
                        page=1,
                        claim_type=ClaimType.VERBATIM,
                        evidence_class=EvidenceClass.DESIGN,
                    )
                ],
            ),
            NumbersIndex(paper_id="p", numbers=[]),
        ),
    )
    monkeypatch.setattr(
        orchestrator.ledger_mod,
        "write_ledger_artifacts",
        lambda *a, **k: (tmp_path / "l.json", tmp_path / "n.json"),
    )
    monkeypatch.setattr(
        orchestrator.planner,
        "plan_slides",
        lambda **k: SlidePlan(blueprint_id="msl_physician_8", slides=[]),
    )
    monkeypatch.setattr(
        orchestrator.generator,
        "generate_deck",
        lambda **k: GenerationResult(
            deck_path=str(tmp_path / "d.pptx"),
            slide_map_path=str(tmp_path / "m.json"),
            slide_plan_path=str(tmp_path / "p.json"),
            slide_map=SlideMap(entries=[]),
        ),
    )
    monkeypatch.setattr(
        orchestrator.render_mod,
        "render_deck",
        lambda *a, **k: type("R", (), {"slide_images": ["s1.png"]})(),
    )
    monkeypatch.setattr(
        orchestrator.gate1_content,
        "run_gate1",
        lambda **k: Gate1Result(passed=False, checks=[GateCheckResult(name="references_complete", passed=False)]),
    )

    created.status = RunStatus.RUNNING
    store._persist_run(created)
    orchestrator.start_run(created.id, auto=False)
    assert store.get_run(created.id).status == RunStatus.AWAITING_REVIEW


def test_run_round_does_not_write_placeholder_pngs_when_render_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.models.blueprint import Blueprint, BlueprintSlide
    from app.models.claim import ClaimLedger, ClaimLedgerEntry, ClaimType, EvidenceClass
    from app.models.document import ParsedDocument
    from app.models.numbers import NumbersIndex
    from app.models.run import GenerationResult, RunStatus
    from app.models.slide import SlideMap, SlidePlan
    from app import orchestrator

    assert not hasattr(orchestrator, "_placeholder_pngs")

    pdf = tmp_path / "paper.pdf"
    pdf.write_bytes(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n")
    store = RunStore(root=tmp_path / "runs", db_path=tmp_path / "t.sqlite3")
    created = store.create_run(paper_path=pdf, brief="Create an 8 slide MSL deck")
    orchestrator.set_store(store)
    orchestrator.reset_runtime()

    monkeypatch.setattr(
        orchestrator,
        "load_blueprint",
        lambda _id: Blueprint(id="msl_physician_8", name="t", slides=[BlueprintSlide(role="title")]),
    )
    monkeypatch.setattr(
        orchestrator.pdf_parser,
        "parse_pdf",
        lambda *a, **k: ParsedDocument(paper_id="p", page_count=2, pages=[], assets=[]),
    )
    monkeypatch.setattr(
        orchestrator.ledger_mod,
        "build_ledger",
        lambda *a, **k: (
            ClaimLedger(
                paper_id="p",
                entries=[
                    ClaimLedgerEntry(
                        id="C-001",
                        text="t",
                        verbatim="t",
                        page=1,
                        claim_type=ClaimType.VERBATIM,
                        evidence_class=EvidenceClass.DESIGN,
                    )
                ],
            ),
            NumbersIndex(paper_id="p", numbers=[]),
        ),
    )
    monkeypatch.setattr(
        orchestrator.ledger_mod,
        "write_ledger_artifacts",
        lambda *a, **k: (tmp_path / "l.json", tmp_path / "n.json"),
    )
    monkeypatch.setattr(
        orchestrator.planner,
        "plan_slides",
        lambda **k: SlidePlan(blueprint_id="msl_physician_8", slides=[]),
    )
    monkeypatch.setattr(
        orchestrator.generator,
        "generate_deck",
        lambda **k: GenerationResult(
            deck_path=str(tmp_path / "d.pptx"),
            slide_map_path=str(tmp_path / "m.json"),
            slide_plan_path=str(tmp_path / "p.json"),
            slide_map=SlideMap(entries=[]),
        ),
    )
    monkeypatch.setattr(
        orchestrator.render_mod,
        "render_deck",
        lambda *a, **k: (_ for _ in ()).throw(
            RuntimeError("LibreOffice (soffice) is not installed or not on PATH.")
        ),
    )

    with pytest.raises(RuntimeError, match="LibreOffice"):
        orchestrator.run_round(created.id, round_n=1)

    failed = store.get_run(created.id)
    assert failed.status == RunStatus.FAILED
    slides = store.round_dir(created.id, 1) / "slides"
    assert not slides.exists() or not list(slides.glob("*.png"))
