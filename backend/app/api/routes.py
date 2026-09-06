"""HTTP routes matching openapi.yaml (Prompt 6)."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import threading
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from app.capabilities import deck_capabilities
from app.evolution import darwin, regression
from app.export import bundle as export_bundle
from app.generation.skill_lineage import list_versions, read_active, resolve_skill_dir, set_active
from app.models.run import Brief, ProgressEventType, Run, RunStatus, ScoreOverride
from app.models.slide import CommentsFile, HumanComment
from app.orchestrator import (
    emit,
    export_blockers,
    get_store,
    iter_progress_events,
    parse_brief,
    persist_run,
    reiterate,
    start_run,
)

router = APIRouter()


class ParseBriefRequest(BaseModel):
    brief: str | None = None


class AddCommentsRequest(BaseModel):
    comments: list[HumanComment]


class LockSlidesRequest(BaseModel):
    slides: list[int] = Field(..., min_length=1)
    locked: bool


class LockSlidesResponse(BaseModel):
    locked_slides: list[int]


class LockEvaluationRequest(BaseModel):
    locked: bool = True


class ApplySkillRequest(BaseModel):
    suggestions: list[str] = Field(default_factory=list)


class DecideRequest(BaseModel):
    winner_round_n: int
    activate_skill_version: str | None = None


def _store(request: Request):
    store = getattr(request.app.state, "store", None)
    if store is not None:
        return store
    return get_store()


def _run_or_404(request: Request, run_id: str) -> Run:
    try:
        return _store(request).get_run(run_id)
    except (KeyError, ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=404, detail=f"run not found: {run_id}") from exc


def _round_or_404(run: Run, round_n: int):
    rnd = next((r for r in run.rounds if r.n == round_n), None)
    if rnd is None:
        store = get_store()
        try:
            rnd = store.load_round(run.id, round_n)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=f"round {round_n} not found") from exc
    return rnd


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/capabilities")
def health_capabilities() -> dict[str, object]:
    return {"status": "ok", "capabilities": deck_capabilities()}


@router.get("/skills/active")
def skill_active() -> dict[str, object]:
    version = read_active()
    return {
        "version": version,
        "path": str(resolve_skill_dir(version)),
        "versions": list_versions(),
    }


@router.post("/runs", status_code=201)
async def create_run(
    request: Request,
    pdf: UploadFile = File(...),
    brief: str = Form(...),
    blueprint_id: str = Form("msl_physician_8"),
    skill_version: str = Form("v1"),
    budget_usd: float = Form(25.0),
) -> dict[str, str | None]:
    if not pdf.filename or not pdf.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="pdf must be a .pdf file")
    store = _store(request)
    tmp = Path(tempfile.mkdtemp(prefix="ma-darwin-upload-"))
    try:
        dest = tmp / (pdf.filename or "paper.pdf")
        dest.write_bytes(await pdf.read())
        run = store.create_run(
            paper_path=dest,
            brief=brief,
            blueprint_id=blueprint_id,
            skill_version=skill_version,
        )
    except FileExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    run.budget_usd = budget_usd
    run.brief_text = brief
    persist_run(parse_brief(run.id, brief))
    run = store.get_run(run.id)
    return {
        "id": run.id,
        "status": run.status.value,
        "paper_id": run.paper_id,
        "blueprint_id": run.blueprint_id,
        "skill_version": run.skill_version,
    }


@router.get("/runs/{run_id}")
def get_run(request: Request, run_id: str) -> dict[str, object]:
    run = _run_or_404(request, run_id)
    summaries = []
    for rnd in run.rounds:
        summaries.append(
            {
                "n": rnd.n,
                "deck_score": rnd.gate3.deck_score if rnd.gate3 else None,
                "gate1_passed": rnd.gate1.passed if rnd.gate1 else None,
                "gate2_passed": rnd.gate2.passed if rnd.gate2 else None,
                "locked_slides": rnd.locked_slides,
            }
        )
    payload = json.loads(run.model_dump_json())
    payload["rounds"] = summaries
    return payload


@router.post("/runs/{run_id}/parse-brief")
def parse_brief_route(request: Request, run_id: str, body: ParseBriefRequest | None = None) -> Brief:
    _run_or_404(request, run_id)
    text = body.brief if body is not None else None
    return parse_brief(run_id, text).brief


@router.put("/runs/{run_id}/brief")
def update_brief(request: Request, run_id: str, brief: Brief) -> Brief:
    run = _run_or_404(request, run_id)
    if run.status not in (RunStatus.CREATED,):
        raise HTTPException(status_code=409, detail="brief can only be edited before start")
    run.brief = brief
    persist_run(run)
    return brief


@router.post("/runs/{run_id}/start", status_code=202)
def start_run_route(request: Request, run_id: str) -> dict[str, object]:
    run = _run_or_404(request, run_id)
    if run.rounds or run.status != RunStatus.CREATED:
        raise HTTPException(status_code=409, detail="run already started")
    if os.environ.get("PYTEST_CURRENT_TEST") or os.environ.get("MA_DARWIN_SYNC_JOBS") == "1":
        rnd = start_run(run_id, auto=False)
        status = get_store().get_run(run_id).status.value
        return {
            "run_id": run_id,
            "round_n": rnd.n,
            "status": status,
            "events_url": f"/runs/{run_id}/events",
        }

    run.status = RunStatus.RUNNING
    persist_run(run)

    def _job() -> None:
        try:
            start_run(run_id, auto=False)
        except Exception as exc:
            emit(run_id, ProgressEventType.ERROR, str(exc), round_n=1)

    threading.Thread(target=_job, daemon=True).start()
    return {
        "run_id": run_id,
        "round_n": 1,
        "status": RunStatus.RUNNING.value,
        "events_url": f"/runs/{run_id}/events",
    }


@router.get("/runs/{run_id}/events")
def stream_events(request: Request, run_id: str) -> StreamingResponse:
    _run_or_404(request, run_id)

    def _gen():
        for ev in iter_progress_events(run_id):
            yield f"event: {ev.event.value}\ndata: {ev.model_dump_json()}\n\n"

    return StreamingResponse(_gen(), media_type="text/event-stream")


@router.get("/runs/{run_id}/rounds/{round_n}")
def get_round(request: Request, run_id: str, round_n: int) -> dict[str, object]:
    run = _run_or_404(request, run_id)
    rnd = _round_or_404(run, round_n)
    images = []
    for path in rnd.slide_images:
        name = Path(path).name
        images.append(f"/runs/{run_id}/rounds/{round_n}/slides/{name}")
    svgs = []
    for path in rnd.slide_svgs or []:
        name = Path(path).name
        svgs.append(f"/runs/{run_id}/rounds/{round_n}/slides/{name}")
    if not svgs:
        rdir = _store(request).round_dir(run_id, round_n) / "slides"
        if rdir.is_dir():
            svgs = [f"/runs/{run_id}/rounds/{round_n}/slides/{p.name}" for p in sorted(rdir.glob("slide_*.svg"))]
    slide_map = None
    map_path = _store(request).round_dir(run_id, round_n) / "slide_map.json"
    if map_path.is_file():
        from app.models.slide import SlideMap

        slide_map = json.loads(SlideMap.model_validate_json(map_path.read_text(encoding="utf-8")).model_dump_json())
    layout_spec = None
    spec_path = Path(rnd.layout_spec_path) if rnd.layout_spec_path else _store(request).round_dir(run_id, round_n) / "layout_spec.json"
    if spec_path.is_file():
        from app.models.layout import LayoutSpec

        layout_spec = json.loads(LayoutSpec.model_validate_json(spec_path.read_text(encoding="utf-8")).model_dump_json())
    preview_pdf = f"/runs/{run_id}/rounds/{round_n}/deck.pdf"
    pdf_url = preview_pdf if _round_preview_pdf(_store(request), run_id, round_n) else None
    return {
        "n": rnd.n,
        "deck_path": rnd.deck_path,
        "pdf_url": pdf_url,
        "slide_images": images,
        "slide_svgs": svgs,
        "layout_spec": layout_spec,
        "gate1": json.loads(rnd.gate1.model_dump_json()) if rnd.gate1 else None,
        "gate2": json.loads(rnd.gate2.model_dump_json()) if rnd.gate2 else None,
        "gate3": json.loads(rnd.gate3.model_dump_json()) if rnd.gate3 else None,
        "human": json.loads(rnd.human.model_dump_json()),
        "mutations": [json.loads(m.model_dump_json()) for m in rnd.mutations],
        "locked_slides": rnd.locked_slides,
        "comments": [json.loads(c.model_dump_json()) for c in rnd.comments],
        "cost_usd": rnd.cost_usd,
        "token_count": rnd.token_count,
        "slide_map": slide_map,
        "preview_pdf_url": preview_pdf,
    }


def _round_preview_pdf(store, run_id: str, round_n: int) -> Path | None:
    rdir = store.round_dir(run_id, round_n)
    for name in ("deck_from_pptx.pdf", "deck.pdf"):
        path = rdir / name
        if path.is_file():
            return path
    return None


@router.get("/runs/{run_id}/rounds/{round_n}/deck.pdf")
def get_deck_pdf(request: Request, run_id: str, round_n: int) -> FileResponse:
    """In-browser PDF preview (soffice pptx→pdf preferred; LayoutSpec PDF fallback)."""
    run = _run_or_404(request, run_id)
    _round_or_404(run, round_n)
    path = _round_preview_pdf(_store(request), run_id, round_n)
    if path is None:
        raise HTTPException(status_code=404, detail="deck PDF not ready")
    return FileResponse(
        path,
        media_type="application/pdf",
        filename="deck.pdf",
        headers={"Content-Disposition": "inline; filename=deck.pdf"},
    )


@router.get("/runs/{run_id}/rounds/{round_n}/slides/{name}")
def get_slide_image(request: Request, run_id: str, round_n: int, name: str) -> FileResponse:
    _run_or_404(request, run_id)
    if "/" in name or "\\" in name or name in (".", ".."):
        raise HTTPException(status_code=400, detail="invalid slide name")
    path = _store(request).round_dir(run_id, round_n) / "slides" / name
    if not path.is_file():
        raise HTTPException(status_code=404, detail="slide image not found")
    media = "image/svg+xml" if path.suffix.lower() == ".svg" else "image/png"
    return FileResponse(path, media_type=media)


@router.post("/runs/{run_id}/rounds/{round_n}/comments")
def add_comments(request: Request, run_id: str, round_n: int, body: AddCommentsRequest) -> CommentsFile:
    run = _run_or_404(request, run_id)
    rnd = _round_or_404(run, round_n)
    existing = {c.id: c for c in rnd.comments}
    for comment in body.comments:
        existing[comment.id] = comment
    rnd.comments = list(existing.values())
    run.rounds = [rnd if r.n == rnd.n else r for r in run.rounds]
    persist_run(run)
    rdir = _store(request).round_dir(run_id, round_n)
    rdir.mkdir(parents=True, exist_ok=True)
    artifact = CommentsFile(run_id=run_id, round_n=round_n, comments=rnd.comments)
    (rdir / "comments.json").write_text(artifact.model_dump_json(indent=2) + "\n", encoding="utf-8")
    (rdir / "round.json").write_text(rnd.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return artifact


@router.post("/runs/{run_id}/rounds/{round_n}/lock")
def lock_slides(request: Request, run_id: str, round_n: int, body: LockSlidesRequest) -> LockSlidesResponse:
    run = _run_or_404(request, run_id)
    rnd = _round_or_404(run, round_n)
    locked = set(rnd.locked_slides)
    if body.locked:
        locked.update(body.slides)
    else:
        locked.difference_update(body.slides)
    rnd.locked_slides = sorted(locked)
    run.rounds = [rnd if r.n == rnd.n else r for r in run.rounds]
    persist_run(run)
    rdir = _store(request).round_dir(run_id, round_n)
    if rdir.is_dir():
        (rdir / "round.json").write_text(rnd.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return LockSlidesResponse(locked_slides=rnd.locked_slides)


@router.post("/runs/{run_id}/rounds/{round_n}/overrides")
def override_score(request: Request, run_id: str, round_n: int, body: ScoreOverride) -> ScoreOverride:
    run = _run_or_404(request, run_id)
    rnd = _round_or_404(run, round_n)
    rnd.human.score_overrides = [
        o for o in rnd.human.score_overrides if not (o.criterion == body.criterion and o.slide == body.slide)
    ] + [body]
    run.rounds = [rnd if r.n == rnd.n else r for r in run.rounds]
    persist_run(run)
    return body


def _start_next_round(request: Request, run_id: str, *, force: bool = False) -> dict[str, object]:
    run = _run_or_404(request, run_id)
    if run.status not in (RunStatus.AWAITING_REVIEW, RunStatus.PLATEAU):
        raise HTTPException(status_code=409, detail=f"cannot reiterate from status {run.status.value}")
    next_n = (run.rounds[-1].n + 1) if run.rounds else 1
    if os.environ.get("PYTEST_CURRENT_TEST") or os.environ.get("MA_DARWIN_SYNC_JOBS") == "1":
        rnd = reiterate(run_id, auto=False, force=force)
        status = get_store().get_run(run_id).status.value
        return {
            "run_id": run_id,
            "round_n": rnd.n,
            "status": status,
            "events_url": f"/runs/{run_id}/events",
        }

    run.status = RunStatus.RUNNING
    persist_run(run)

    def _job() -> None:
        try:
            reiterate(run_id, auto=False, force=force)
        except Exception as exc:
            emit(run_id, ProgressEventType.ERROR, str(exc), round_n=next_n)

    threading.Thread(target=_job, daemon=True).start()
    return {
        "run_id": run_id,
        "round_n": next_n,
        "status": RunStatus.RUNNING.value,
        "events_url": f"/runs/{run_id}/events",
    }


@router.post("/runs/{run_id}/reiterate", status_code=202)
def reiterate_route(request: Request, run_id: str) -> dict[str, object]:
    return _start_next_round(request, run_id, force=False)


@router.get("/runs/{run_id}/export")
def export_run(
    request: Request,
    run_id: str,
    round_n: int | None = None,
    bundle: bool = False,
    mode: str | None = None,
):
    """Download the generated PowerPoint.

    Default is the actual ``.pptx`` (draft if gates fail). Pass ``bundle=1`` or
    ``mode=compliant`` for the gated zip. Never return a JSON error body as the
    download file.
    """
    run = _run_or_404(request, run_id)
    n = round_n or run.best_round_n or (run.rounds[-1].n if run.rounds else None)
    if n is None:
        raise HTTPException(status_code=404, detail="no round to export")
    _round_or_404(run, n)
    store = _store(request)
    blocker = export_blockers(run, round_n=n)
    want_bundle = bundle or (mode or "").lower() == "compliant"
    if want_bundle:
        if blocker:
            raise HTTPException(status_code=409, detail=blocker)
        try:
            result = export_bundle.create_bundle(run_id, round_n=n, store=store)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except PermissionError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        path = Path(result.path)
        if not path.is_file():
            raise HTTPException(status_code=500, detail="export bundle missing on disk")
        return FileResponse(path, media_type="application/zip", filename=path.name)

    pptx = export_bundle.find_round_pptx(run, round_n=n, store=store)
    if pptx is None or not pptx.is_file():
        raise HTTPException(status_code=404, detail="deck.pptx is not ready yet")
    kind = "draft" if blocker else "compliant"
    filename = f"Round_{n}_M2M_{kind}.pptx"
    return FileResponse(
        pptx,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        filename=filename,
        headers={
            "X-Darwin-Export": kind,
            "X-Darwin-Export-Reason": blocker or "",
            "Access-Control-Expose-Headers": "Content-Disposition, X-Darwin-Export, X-Darwin-Export-Reason",
        },
    )


@router.post("/runs/{run_id}/rounds/{round_n}/lock-evaluation")
def lock_evaluation(request: Request, run_id: str, round_n: int, body: LockEvaluationRequest) -> dict[str, object]:
    run = _run_or_404(request, run_id)
    rnd = _round_or_404(run, round_n)
    rnd.human.evaluation_locked = body.locked
    run.rounds = [rnd if r.n == rnd.n else r for r in run.rounds]
    persist_run(run)
    return {"evaluation_locked": rnd.human.evaluation_locked}


def _heal_review_status(run: Run) -> Run:
    """A finished round is reviewable even if start used auto=False and left RUNNING."""
    if run.status == RunStatus.RUNNING and run.rounds:
        run.status = RunStatus.AWAITING_REVIEW
        persist_run(run)
    elif run.status == RunStatus.COMPLETE:
        run.status = RunStatus.AWAITING_REVIEW
        persist_run(run)
    return run


@router.post("/runs/{run_id}/rounds/{round_n}/suggest-skill")
def suggest_skill(request: Request, run_id: str, round_n: int) -> dict[str, object]:
    run = _heal_review_status(_run_or_404(request, run_id))
    rnd = _round_or_404(run, round_n)
    if not rnd.human.evaluation_locked:
        rnd.human.evaluation_locked = True
        run.rounds = [rnd if r.n == rnd.n else r for r in run.rounds]
        persist_run(run)
    rdir = _store(request).round_dir(run_id, round_n)
    artifact = darwin.suggest_skill_changes(run, rnd, output_path=rdir / "suggestions.json")
    return json.loads(artifact.model_dump_json())


@router.post("/runs/{run_id}/apply-skill", status_code=202)
def apply_skill(request: Request, run_id: str, body: ApplySkillRequest) -> dict[str, object]:
    run = _heal_review_status(_run_or_404(request, run_id))
    if run.status not in (RunStatus.AWAITING_REVIEW, RunStatus.PLATEAU):
        raise HTTPException(status_code=409, detail=f"cannot apply skill from status {run.status.value}")
    texts = [t.strip() for t in body.suggestions if t.strip()]
    if not texts:
        raise HTTPException(status_code=400, detail="no skill suggestions to apply")
    rnd = run.rounds[-1] if run.rounds else None
    if rnd is not None and not rnd.human.evaluation_locked:
        rnd.human.evaluation_locked = True
        run.rounds = [rnd if r.n == rnd.n else r for r in run.rounds]
        persist_run(run)
    store = _store(request)
    version = darwin.apply_skill_suggestions(
        texts,
        from_version=run.skill_version,
        run_dir=store.run_dir(run_id),
    )
    run.skill_version = version
    persist_run(run)
    return _start_next_round(request, run_id, force=True)


@router.post("/runs/{run_id}/decide")
def decide_winner(request: Request, run_id: str, body: DecideRequest) -> dict[str, object]:
    run = _run_or_404(request, run_id)
    _round_or_404(run, body.winner_round_n)
    run.best_round_n = body.winner_round_n
    if body.activate_skill_version:
        set_active(body.activate_skill_version)
        run.skill_version = body.activate_skill_version
    persist_run(run)
    return {"best_round_n": run.best_round_n, "skill_version": run.skill_version}


@router.post("/skills/{version}/activate")
def activate_skill(version: str) -> dict[str, str]:
    try:
        path = regression.activate_skill_version(version)
    except NotImplementedError:
        return JSONResponse(status_code=501, content={"detail": "skill rollback is not implemented yet"})
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"version": version, "path": str(path)}
