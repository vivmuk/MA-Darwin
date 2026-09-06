"""Round orchestrator — generate → render → gates → stop/auto-reiterate (Prompt 6)."""

from __future__ import annotations

import json
import os
import re
import threading
import time
from collections.abc import Callable, Iterator
from datetime import datetime, timezone
from pathlib import Path

import yaml

from app.export import bundle as export_bundle
from app.gates import gate1_content, gate2_visual, gate3_judge
from app.generation import generator, planner
from app.ingestion import ledger as ledger_mod
from app.ingestion import pdf_parser
from app.models.blueprint import Blueprint
from app.models.claim import ClaimLedger
from app.models.document import ExtractedAsset, ParsedDocument
from app.models.gates import Gate3Result
from app.models.numbers import NumbersIndex
from app.models.run import (
    Brief,
    DeckType,
    GenerationResult,
    ProgressEvent,
    ProgressEventType,
    RenderResult,
    Round,
    Run,
    RunStatus,
    StoppingDecision,
    StoppingReason,
)
from app.models.slide import HumanComment, Scope, SlideMap, SlidePlan
from app.paths import BLUEPRINTS_DIR, CONFIG_DIR
from app.rendering import render as render_mod
from app.storage.run_store import RunStore

_FIXTURES = Path(__file__).resolve().parents[1] / "tests" / "fixtures"

_store_lock = threading.Lock()
_store: RunStore | None = None

_event_lock = threading.Lock()
_events: dict[str, list[ProgressEvent]] = {}
_event_cv: dict[str, threading.Condition] = {}
_round_started: dict[str, float] = {}
_tokens: dict[str, int] = {}
_cost: dict[str, float] = {}


def reset_runtime() -> None:
    """Clear process-local event bus (tests)."""
    with _event_lock:
        _events.clear()
        _event_cv.clear()
        _round_started.clear()
        _tokens.clear()
        _cost.clear()


def set_store(store: RunStore) -> None:
    """Inject the run store (API lifespan / tests)."""
    global _store
    with _store_lock:
        _store = store


def get_store() -> RunStore:
    global _store
    with _store_lock:
        if _store is None:
            _store = RunStore()
        return _store


def persist_run(run: Run) -> None:
    """Write run.json + manifest via RunStore (status, brief, best_round_n)."""
    run.updated_at = datetime.now(timezone.utc)
    get_store()._persist_run(run)


def load_blueprint(blueprint_id: str) -> Blueprint:
    path = BLUEPRINTS_DIR / f"{blueprint_id}.json"
    if not path.is_file():
        path = BLUEPRINTS_DIR / f"{blueprint_id}.yaml"
    if not path.is_file():
        raise FileNotFoundError(f"blueprint not found: {blueprint_id}")
    if path.suffix == ".json":
        return Blueprint.model_validate_json(path.read_text(encoding="utf-8"))
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return Blueprint.model_validate(data)


def load_defaults(defaults_config: Path | str | None = None) -> dict[str, object]:
    path = Path(defaults_config) if defaults_config is not None else CONFIG_DIR / "defaults.yaml"
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    if not isinstance(data, dict):
        raise ValueError(f"defaults config must be a mapping: {path}")
    return data


def parse_brief_text(text: str, *, existing: Brief | None = None) -> Brief:
    """Deterministic brief parse. Unspecified fields keep model defaults (user confirms)."""
    base = existing.model_copy() if existing is not None else Brief()
    notes = text.strip()
    slide_count = base.slide_count
    m = re.search(r"(\d+)\s*-?\s*slides?\b", notes, re.IGNORECASE)
    if m:
        slide_count = max(1, int(m.group(1)))
    audience = base.audience
    for token, label in (
        (r"\bkol\b", "KOL"),
        (r"\bpayer", "payer"),
        (r"\bnurse", "nurse"),
        (r"\bpharmacist", "pharmacist"),
        (r"\bphysician|\bmsl\b", "physician"),
    ):
        if re.search(token, notes, re.IGNORECASE):
            audience = label
            break
    purpose = base.purpose
    if re.search(r"advisory", notes, re.IGNORECASE):
        purpose = "advisory board"
    elif re.search(r"train", notes, re.IGNORECASE):
        purpose = "training"
    elif re.search(r"msl|scientific exchange|physician", notes, re.IGNORECASE):
        purpose = "MSL presentation"
    deck_type = base.deck_type
    if re.search(r"msl", notes, re.IGNORECASE):
        deck_type = DeckType.MSL_PHYSICIAN
    return Brief(
        slide_count=slide_count,
        deck_type=deck_type,
        audience=audience,
        purpose=purpose,
        notes=notes or base.notes,
    )


def parse_brief(run_id: str, brief_text: str | None = None) -> Run:
    """Parse freeform brief into structured fields for user confirmation."""
    store = get_store()
    run = store.get_run(run_id)
    text = brief_text if brief_text is not None else run.brief_text
    run.brief = parse_brief_text(text, existing=run.brief)
    if brief_text is not None:
        run.brief_text = brief_text
    persist_run(run)
    return run


def _cv(run_id: str) -> threading.Condition:
    with _event_lock:
        if run_id not in _event_cv:
            _event_cv[run_id] = threading.Condition()
        _events.setdefault(run_id, [])
        return _event_cv[run_id]


def _elapsed_ms(run_id: str) -> int:
    start = _round_started.get(run_id, time.monotonic())
    return int((time.monotonic() - start) * 1000)


def emit(
    run_id: str,
    event: ProgressEventType,
    message: str,
    *,
    round_n: int | None = None,
    **fields: object,
) -> ProgressEvent:
    """Append a real milestone to the in-memory bus and ``events.jsonl``."""
    payload = ProgressEvent(
        event=event,
        run_id=run_id,
        round_n=round_n,
        message=message,
        timestamp=datetime.now(timezone.utc),
        elapsed_ms=_elapsed_ms(run_id),
        token_count=_tokens.get(run_id, 0),
        cost_usd=_cost.get(run_id, 0.0),
        **{k: v for k, v in fields.items() if v is not None},
    )
    with _event_lock:
        _events.setdefault(run_id, []).append(payload)
    try:
        log = get_store().run_dir(run_id) / "events.jsonl"
        log.parent.mkdir(parents=True, exist_ok=True)
        with log.open("a", encoding="utf-8") as fh:
            fh.write(payload.model_dump_json() + "\n")
    except (ValueError, OSError):
        pass
    cv = _cv(run_id)
    with cv:
        cv.notify_all()
    return payload


def _load_jsonl_events(run_id: str) -> list[ProgressEvent]:
    path = get_store().run_dir(run_id) / "events.jsonl"
    if not path.is_file():
        return []
    out: list[ProgressEvent] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            out.append(ProgressEvent.model_validate_json(line))
    return out


def iter_progress_events(run_id: str) -> Iterator[ProgressEvent]:
    """Yield real progress milestones for the SSE ``/runs/{id}/events`` stream."""
    get_store().get_run(run_id)  # 404 if missing
    seen = 0
    terminal = {
        ProgressEventType.AWAITING_REVIEW,
        ProgressEventType.PLATEAU,
        ProgressEventType.ERROR,
    }
    idle_rounds = 0
    while True:
        with _event_lock:
            buf = list(_events.get(run_id, []))
        if not buf:
            buf = _load_jsonl_events(run_id)
            with _event_lock:
                if run_id not in _events or not _events[run_id]:
                    _events[run_id] = buf
        new = buf[seen:]
        for ev in new:
            yield ev
            seen += 1
            if ev.event in terminal:
                return
        if new:
            idle_rounds = 0
            continue
        idle_rounds += 1
        if idle_rounds > 200:
            return
        cv = _cv(run_id)
        with cv:
            cv.wait(timeout=0.1)


def _fixture(name: str, model: type):
    override = os.environ.get("MA_DARWIN_FIXTURE_DIR")
    root = Path(override) if override else _FIXTURES
    path = root / name
    if not path.is_file():
        raise FileNotFoundError(f"frozen fixture missing: {path}")
    return model.model_validate_json(path.read_text(encoding="utf-8"))


def _call(fn: Callable, fallback: Callable | None, *args: object, **kwargs: object):
    try:
        return fn(*args, **kwargs)
    except NotImplementedError:
        if fallback is None:
            raise
        return fallback()


def _find_paper(run_id: str) -> Path:
    run_dir = get_store().run_dir(run_id)
    paper_dir = run_dir / "paper"
    if paper_dir.is_dir():
        pdfs = sorted(paper_dir.glob("*.pdf")) + sorted(paper_dir.glob("*.PDF"))
        if pdfs:
            return pdfs[0]
    raise FileNotFoundError(f"paper PDF missing for {run_id}")


def _load_assets(run_id: str) -> list[ExtractedAsset]:
    assets_dir = get_store().run_dir(run_id) / "assets"
    if not assets_dir.is_dir():
        return []
    out: list[ExtractedAsset] = []
    for i, path in enumerate(sorted(assets_dir.glob("*.png")), start=1):
        out.append(
            ExtractedAsset(
                id=path.stem,
                kind="figure",
                page=1,
                caption=path.stem,
                path=str(path),
            )
        )
    return out


def _write_round_json(run_id: str, rnd: Round) -> None:
    path = get_store().round_dir(run_id, rnd.n) / "round.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(rnd.model_dump_json(indent=2) + "\n", encoding="utf-8")


def _save_artifact(run_id: str, round_n: int, name: str, model: object) -> None:
    path = get_store().round_dir(run_id, round_n) / (name if name.endswith(".json") else f"{name}.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return
    if hasattr(model, "model_dump_json"):
        path.write_text(model.model_dump_json(indent=2) + "\n", encoding="utf-8")


def _prior_deck(run: Run, round_n: int) -> Path | None:
    if round_n <= 1:
        return None
    prev = get_store().round_dir(run.id, round_n - 1) / "deck.pptx"
    return prev if prev.is_file() else None


def _locked_from_previous(run: Run, round_n: int) -> list[int]:
    prev = next((r for r in run.rounds if r.n == round_n - 1), None)
    return list(prev.locked_slides) if prev else []


def _one_off_comments(run: Run) -> list[HumanComment]:
    prev = run.rounds[-1] if run.rounds else None
    if prev is None:
        return []
    return [c for c in prev.comments if c.scope == Scope.THIS_DECK_ONLY]


def _update_best(run: Run, rnd: Round) -> None:
    if rnd.gate3 is None:
        return
    score = rnd.gate3.deck_score
    if run.best_round_n is None:
        run.best_round_n = rnd.n
        return
    best = next((r for r in run.rounds if r.n == run.best_round_n), None)
    if best is None or best.gate3 is None or score > best.gate3.deck_score:
        run.best_round_n = rnd.n


def _slide_count(rnd: Round, blueprint: Blueprint) -> int:
    if rnd.slide_images:
        return len(rnd.slide_images)
    if rnd.locked_slides:
        return max(rnd.locked_slides)
    return max(len(blueprint.slides), 1)


def _all_locked(rnd: Round, blueprint: Blueprint) -> bool:
    n = _slide_count(rnd, blueprint)
    return n > 0 and set(range(1, n + 1)).issubset(set(rnd.locked_slides))


def _scores(run: Run) -> list[float]:
    return [r.gate3.deck_score for r in run.rounds if r.gate3 is not None]


def check_stopping_conditions(
    run: Run,
    *,
    defaults_config: Path | str | None = None,
) -> StoppingDecision:
    """Evaluate PRD §10 stopping conditions (success, max rounds, budget, plateau)."""
    cfg = load_defaults(defaults_config)
    max_rounds = int(cfg["max_rounds"])
    min_improve = float(cfg.get("plateau_min_improvement", 1.0))
    plateau_n = int(cfg.get("plateau_consecutive_rounds", 2))
    try:
        blueprint = load_blueprint(run.blueprint_id)
    except FileNotFoundError:
        blueprint = Blueprint(id=run.blueprint_id, name=run.blueprint_id, slides=[])

    if run.rounds:
        latest = run.rounds[-1]
        gates_ok = (
            latest.gate1 is not None
            and latest.gate1.passed
            and latest.gate2 is not None
            and latest.gate2.passed
        )
        if gates_ok and _all_locked(latest, blueprint):
            return StoppingDecision(
                halt=True,
                reason=StoppingReason.SUCCESS,
                message="All slides locked and all gates pass",
            )

    spent = sum(r.cost_usd for r in run.rounds)
    if spent > run.budget_usd:
        return StoppingDecision(
            halt=True,
            reason=StoppingReason.BUDGET,
            message=f"Cost ${spent:.2f} exceeded budget ${run.budget_usd:.2f}",
        )

    if len(run.rounds) >= max_rounds:
        return StoppingDecision(
            halt=True,
            reason=StoppingReason.MAX_ROUNDS,
            message=f"max_rounds ({max_rounds}) reached",
        )

    scores = _scores(run)
    if len(scores) >= plateau_n + 1:
        delta = scores[-1] - scores[-(plateau_n + 1)]
        if delta < min_improve:
            return StoppingDecision(
                halt=True,
                reason=StoppingReason.PLATEAU,
                message=(
                    f"Deck score has not improved by ≥ {min_improve:g} point "
                    f"over {plateau_n} consecutive rounds (Δ {delta:.1f})"
                ),
            )

    return StoppingDecision(halt=False, reason=StoppingReason.CONTINUE, message="")


def should_auto_reiterate(
    run: Run,
    round_obj: Round,
    *,
    judge_threshold: float | None = None,
    max_auto_rounds: int | None = None,
) -> bool:
    """True when Gate 3 is below threshold and auto-round budget remains."""
    cfg = load_defaults()
    threshold = float(judge_threshold if judge_threshold is not None else cfg["judge_threshold"])
    max_auto = int(max_auto_rounds if max_auto_rounds is not None else cfg["max_auto_rounds"])
    if round_obj.gate1 is None or not round_obj.gate1.passed:
        return False
    if round_obj.gate2 is None or not round_obj.gate2.passed:
        return False
    if round_obj.gate3 is None:
        return False
    if round_obj.gate3.deck_score >= threshold:
        return False
    if run.auto_rounds_used >= max_auto:
        return False
    stop = check_stopping_conditions(run)
    if stop.halt:
        return False
    return True


def _apply_status(run: Run, decision: StoppingDecision) -> None:
    if decision.reason == StoppingReason.SUCCESS:
        run.status = RunStatus.COMPLETE
    elif decision.reason == StoppingReason.PLATEAU:
        run.status = RunStatus.PLATEAU
    elif decision.reason == StoppingReason.FAILED:
        run.status = RunStatus.FAILED
    else:
        run.status = RunStatus.AWAITING_REVIEW


def run_round(run_id: str, *, round_n: int | None = None) -> Round:
    """Execute one full round: generate → render → gate1 → gate2 → gate3."""
    store = get_store()
    run = store.get_run(run_id)
    n = round_n if round_n is not None else (len(run.rounds) + 1)
    if n < 1:
        raise ValueError("round_n must be >= 1")
    _round_started[run_id] = time.monotonic()
    _tokens.setdefault(run_id, 0)
    _cost.setdefault(run_id, 0.0)

    run.status = RunStatus.RUNNING
    persist_run(run)

    rdir = store.round_dir(run_id, n)
    rdir.mkdir(parents=True, exist_ok=True)
    run_dir = store.run_dir(run_id)
    paper = _find_paper(run_id)
    blueprint = load_blueprint(run.blueprint_id)
    locked = _locked_from_previous(run, n)
    prior = _prior_deck(run, n)
    one_offs = _one_off_comments(run)

    rnd = Round(n=n, locked_slides=list(locked))

    try:
        assets_dir = run_dir / "assets"
        parsed: ParsedDocument = pdf_parser.parse_pdf(paper, assets_dir, paper_id=run.paper_id)
        emit(
            run_id,
            ProgressEventType.PAGES_PARSED,
            f"Parsed {parsed.page_count} pages",
            round_n=n,
            pages=parsed.page_count,
        )
        emit(
            run_id,
            ProgressEventType.FIGURES_EXTRACTED,
            f"Extracted {len(parsed.assets)} figures",
            round_n=n,
            figures=len(parsed.assets),
        )

        built = _call(
            ledger_mod.build_ledger,
            lambda: (_fixture("ledger.json", ClaimLedger), _fixture("numbers_index.json", NumbersIndex)),
            paper,
            paper_id=run.paper_id,
            assets_dir=assets_dir,
        )
        claim_ledger, numbers_index = built
        ledger_mod.write_ledger_artifacts(run_dir, claim_ledger, numbers_index)
        emit(
            run_id,
            ProgressEventType.CLAIMS_EXTRACTED,
            f"Extracted {len(claim_ledger.entries)} claims",
            round_n=n,
            claims=len(claim_ledger.entries),
        )

        slide_plan: SlidePlan = _call(
            planner.plan_slides,
            lambda: _fixture("slide_plan.json", SlidePlan),
            blueprint=blueprint,
            ledger=claim_ledger,
            brief=run.brief,
            skill_version=run.skill_version,
            one_off_comments=one_offs,
        )
        slot_total = max(len(slide_plan.slides), 1)
        for planned in slide_plan.slides:
            emit(
                run_id,
                ProgressEventType.BLUEPRINT_SLOT_FILLED,
                f"Filling blueprint {planned.slide}/{slot_total}",
                round_n=n,
                slot=planned.slide,
                slot_total=slot_total,
            )

        gen: GenerationResult = generator.generate_deck(
            blueprint=blueprint,
            ledger=claim_ledger,
            brief=run.brief,
            skill_version=run.skill_version,
            slide_plan=slide_plan,
            output_dir=rdir,
            locked_slides=locked,
            prior_deck_path=prior,
            assets=_load_assets(run_id) or parsed.assets,
        )
        rnd.deck_path = gen.deck_path
        rnd.layout_spec_path = gen.layout_spec_path or str(rdir / "layout_spec.json")
        slide_map: SlideMap = gen.slide_map
        layout_spec = gen.layout_spec
        if layout_spec is None and gen.layout_spec_path:
            from app.generation.layout import load_layout_spec

            layout_spec = load_layout_spec(gen.layout_spec_path)

        emit(run_id, ProgressEventType.RENDERING, "Rendering", round_n=n)
        rendered: RenderResult = render_mod.render_deck(
            output_dir=rdir,
            layout_spec=layout_spec,
            dpi=int(load_defaults().get("render_dpi", 150)),
        )
        rnd.slide_images = list(rendered.slide_images)
        rnd.slide_svgs = list(getattr(rendered, "slide_svgs", None) or [])

        gate1 = gate1_content.run_gate1(
            pptx_path=gen.deck_path,
            slide_map=slide_map,
            ledger=claim_ledger,
            numbers_index=numbers_index,
            blueprint_roles=[s.role for s in blueprint.slides],
        )
        rnd.gate1 = gate1
        _save_artifact(run_id, n, "gate1", gate1)
        flags = sum(1 for c in gate1.checks if not c.passed)
        emit(
            run_id,
            ProgressEventType.GATE1_COMPLETE,
            f"Gate 1: {flags} flags",
            round_n=n,
            gate_flags=flags,
        )
        if not gate1.passed:
            return _finish_round(run_id, run, rnd, skip_reason="gate1")

        gate2 = gate2_visual.run_gate2(layout_spec=layout_spec, slide_images=rnd.slide_images)
        rnd.gate2 = gate2
        _save_artifact(run_id, n, "gate2", gate2)
        flags2 = sum(1 for c in gate2.checks if not c.passed)
        emit(
            run_id,
            ProgressEventType.GATE2_COMPLETE,
            f"Gate 2: {flags2} flags",
            round_n=n,
            gate_flags=flags2,
        )
        if not gate2.passed:
            return _finish_round(run_id, run, rnd, skip_reason="gate2")

        slide_total = len(rnd.slide_images) or 1
        for i in range(1, slide_total + 1):
            emit(
                run_id,
                ProgressEventType.JUDGING_SLIDE,
                f"Judging slide {i}/{slide_total}",
                round_n=n,
                slide=i,
                slide_total=slide_total,
            )

        gate3: Gate3Result = _call(
            gate3_judge.run_gate3,
            lambda: _fixture("gate3.json", Gate3Result),
            slide_images=rnd.slide_images,
            blueprint=blueprint,
        )
        rnd.gate3 = gate3
        _save_artifact(run_id, n, "gate3", gate3)
        return _finish_round(run_id, run, rnd, skip_reason=None)
    except Exception as exc:
        emit(run_id, ProgressEventType.ERROR, str(exc), round_n=n)
        run = store.get_run(run_id)
        run.status = RunStatus.FAILED
        persist_run(run)
        raise


def _finish_round(run_id: str, run: Run, rnd: Round, *, skip_reason: str | None) -> Round:
    store = get_store()
    run = store.get_run(run_id)
    rnd.token_count = _tokens.get(run_id, 0)
    rnd.cost_usd = 0.0
    existing = [r for r in run.rounds if r.n != rnd.n]
    run.rounds = sorted(existing + [rnd], key=lambda r: r.n)
    _update_best(run, rnd)
    persist_run(run)
    try:
        store.save_round(run_id, rnd)
    except FileExistsError:
        _write_round_json(run_id, rnd)
        persist_run(get_store().get_run(run_id))

    emit(
        run_id,
        ProgressEventType.ROUND_COMPLETE,
        f"Round {rnd.n} complete" + (f" (short-circuit {skip_reason})" if skip_reason else ""),
        round_n=rnd.n,
    )
    return rnd


def _auto_loop(run_id: str, rnd: Round) -> Round:
    run = get_store().get_run(run_id)
    while should_auto_reiterate(run, rnd):
        run.auto_rounds_used += 1
        persist_run(run)
        rnd = run_round(run_id)
        run = get_store().get_run(run_id)
    decision = check_stopping_conditions(run)
    _apply_status(run, decision)
    persist_run(run)
    if decision.reason == StoppingReason.PLATEAU:
        emit(run_id, ProgressEventType.PLATEAU, decision.message, round_n=rnd.n)
    elif run.status != RunStatus.FAILED:
        emit(
            run_id,
            ProgressEventType.AWAITING_REVIEW,
            decision.message or "Awaiting human review",
            round_n=rnd.n,
        )
    return rnd


def start_run(run_id: str) -> Round:
    """Kick off round 1 for a run (API ``POST /runs/{id}/start``)."""
    run = get_store().get_run(run_id)
    if run.rounds:
        raise RuntimeError("run already has rounds")
    if run.status not in (RunStatus.CREATED,):
        raise RuntimeError(f"cannot start run in status {run.status.value}")
    rnd = run_round(run_id, round_n=1)
    return _auto_loop(run_id, rnd)


def reiterate(run_id: str) -> Round:
    """Start the next round after human review (API ``POST /runs/{id}/reiterate``)."""
    run = get_store().get_run(run_id)
    if run.status not in (RunStatus.AWAITING_REVIEW, RunStatus.PLATEAU):
        raise RuntimeError(f"cannot reiterate from status {run.status.value}")
    decision = check_stopping_conditions(run)
    if decision.halt and decision.reason in {
        StoppingReason.MAX_ROUNDS,
        StoppingReason.BUDGET,
        StoppingReason.SUCCESS,
    }:
        raise RuntimeError(decision.message)
    rnd = run_round(run_id)
    return _auto_loop(run_id, rnd)


def export_blockers(run: Run, *, round_n: int) -> str:
    """Server-side export gate (PRD §7.11). Uses export module when implemented."""
    try:
        allowed, message = export_bundle.export_allowed(run, round_n=round_n)
        return "" if allowed else message
    except NotImplementedError:
        rnd = next((r for r in run.rounds if r.n == round_n), None)
        if rnd is None:
            return f"round {round_n} not found"
        if rnd.gate1 is None or not rnd.gate1.passed:
            return "Gate 1 has not passed"
        if rnd.gate2 is None or not rnd.gate2.passed:
            return "Gate 2 has not passed"
        try:
            blueprint = load_blueprint(run.blueprint_id)
        except FileNotFoundError:
            blueprint = Blueprint(id=run.blueprint_id, name=run.blueprint_id)
        if not _all_locked(rnd, blueprint):
            return "Every slide must be locked before export"
        return ""
