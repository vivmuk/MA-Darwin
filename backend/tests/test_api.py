"""API + SSE against frozen fixtures (no other module live output)."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.app import create_app
from app.models.gates import Gate1Result, Gate2Result, Gate3Result, GateCheckResult
from app.models.run import GenerationResult, RenderResult
from app.models.slide import SlideMap, SlidePlan
from app.orchestrator import reset_runtime, set_store
from app.storage.run_store import RunStore

FIXTURES = Path(__file__).resolve().parent / "fixtures"
MIN_PDF = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"


def test_startup_runs_font_check(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import importlib

    app_mod = importlib.import_module("app.api.app")
    called = {"fonts": False}
    monkeypatch.setattr(app_mod, "check_required_fonts", lambda: called.__setitem__("fonts", True))
    store = RunStore(root=tmp_path / "runs", db_path=tmp_path / "t.sqlite3")
    application = app_mod.create_app(store=store, check_fonts=True)
    with TestClient(application):
        pass
    assert called["fonts"] is True
    assert not hasattr(app_mod, "check_libreoffice")


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    store = RunStore(root=tmp_path / "runs", db_path=tmp_path / "t.sqlite3")
    set_store(store)
    reset_runtime()
    app = create_app(store=store, check_fonts=False)

    from app import orchestrator
    from app.models.claim import ClaimLedger
    from app.models.document import ParsedDocument
    from app.models.numbers import NumbersIndex

    monkeypatch.setattr(
        orchestrator.pdf_parser,
        "parse_pdf",
        lambda *a, **k: ParsedDocument(paper_id="demo", page_count=14, pages=[], assets=[]),
    )
    monkeypatch.setattr(
        orchestrator.ledger_mod,
        "build_ledger",
        lambda *a, **k: (
            ClaimLedger.model_validate_json((FIXTURES / "ledger.json").read_text(encoding="utf-8")),
            NumbersIndex.model_validate_json((FIXTURES / "numbers_index.json").read_text(encoding="utf-8")),
        ),
    )
    monkeypatch.setattr(
        orchestrator.ledger_mod,
        "write_ledger_artifacts",
        lambda *a, **k: (tmp_path / "ledger.json", tmp_path / "numbers.json"),
    )
    monkeypatch.setattr(
        orchestrator.planner,
        "plan_slides",
        lambda **k: SlidePlan.model_validate_json((FIXTURES / "slide_plan.json").read_text(encoding="utf-8")),
    )
    monkeypatch.setattr(
        orchestrator.generator,
        "generate_deck",
        lambda **k: GenerationResult(
            deck_path=str(tmp_path / "deck.pptx"),
            slide_map_path=str(tmp_path / "slide_map.json"),
            slide_plan_path=str(tmp_path / "slide_plan.json"),
            slide_map=SlideMap.model_validate_json((FIXTURES / "slide_map.json").read_text(encoding="utf-8")),
        ),
    )
    monkeypatch.setattr(
        orchestrator.render_mod,
        "render_deck",
        lambda *a, **k: RenderResult(pdf_path=str(tmp_path / "deck.pdf"), slide_images=["slide_01.png"], dpi=150),
    )
    monkeypatch.setattr(
        orchestrator.gate1_content,
        "run_gate1",
        lambda **k: Gate1Result.model_validate_json((FIXTURES / "gate1.json").read_text(encoding="utf-8")),
    )
    monkeypatch.setattr(
        orchestrator.gate2_visual,
        "run_gate2",
        lambda **k: Gate2Result(passed=True, checks=[GateCheckResult(name="shape_bounds", passed=True)]),
    )
    monkeypatch.setattr(
        orchestrator.gate3_judge,
        "run_gate3",
        lambda **k: Gate3Result.model_validate_json((FIXTURES / "gate3.json").read_text(encoding="utf-8")),
    )

    with TestClient(app) as tc:
        yield tc


def test_health(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok"}


def test_create_parse_start_events_round_comments_lock(client: TestClient) -> None:
    created = client.post(
        "/runs",
        files={"pdf": ("paper.pdf", MIN_PDF, "application/pdf")},
        data={"brief": "Create an 8 slide MSL deck for a physician"},
    )
    assert created.status_code == 201, created.text
    run_id = created.json()["id"]
    assert run_id.startswith("run_")

    parsed = client.post(f"/runs/{run_id}/parse-brief")
    assert parsed.status_code == 200
    assert parsed.json()["slide_count"] == 8
    assert parsed.json()["audience"] == "physician"

    started = client.post(f"/runs/{run_id}/start")
    assert started.status_code == 202, started.text
    assert started.json()["events_url"] == f"/runs/{run_id}/events"

    stream = client.get(f"/runs/{run_id}/events")
    assert stream.status_code == 200
    body = stream.text
    assert "pages_parsed" in body
    assert "Parsed 14 pages" in body
    assert "Extracted 3 claims" in body or "claims_extracted" in body
    assert "Filling blueprint" in body
    assert "Rendering" in body
    assert "Gate 1:" in body
    assert "Judging slide" in body
    assert "round_complete" in body

    detail = client.get(f"/runs/{run_id}/rounds/1")
    assert detail.status_code == 200
    payload = detail.json()
    assert payload["n"] == 1
    assert payload["slide_images"][0].startswith(f"/runs/{run_id}/rounds/1/slides/")
    assert payload["gate3"]["deck_score"] == 82.0

    comments = client.post(
        f"/runs/{run_id}/rounds/1/comments",
        json={
            "comments": [
                {
                    "id": "hc_1",
                    "slide": 1,
                    "x": 0.2,
                    "y": 0.3,
                    "text": "Tighten title",
                    "severity": "must-fix",
                    "criterion_tag": "visual_hierarchy",
                    "scope": "this-deck-only",
                }
            ]
        },
    )
    assert comments.status_code == 200
    assert comments.json()["comments"][0]["id"] == "hc_1"

    locked = client.post(
        f"/runs/{run_id}/rounds/1/lock",
        json={"slides": [1], "locked": True},
    )
    assert locked.status_code == 200
    assert locked.json()["locked_slides"] == [1]

    exported = client.get(f"/runs/{run_id}/export")
    assert exported.status_code in (200, 403, 501)
