"""Export bundle assembly (PRD §7.11 / Prompt 9)."""

from __future__ import annotations

import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from app.models.claim import ClaimLedger, ClaimLedgerEntry
from app.models.gates import Gate3Result
from app.models.run import ExportBundleResult, MutationRecord, Round, Run
from app.models.slide import CommentsFile, HumanComment, SlideMap, SlideMapEntry
from app.storage.run_store import RunStore

BUNDLE_FILES = (
    "deck.pptx",
    "deck.pdf",
    "provenance.md",
    "scores.json",
    "skill_version.txt",
    "run_log.json",
)


def _round(run: Run, round_n: int) -> Round:
    rnd = next((r for r in run.rounds if r.n == round_n), None)
    if rnd is None:
        raise KeyError(f"round {round_n} not found on run {run.id}")
    return rnd


def _slide_count(rnd: Round, slide_map: SlideMap | None = None) -> int:
    if rnd.slide_images:
        return len(rnd.slide_images)
    if rnd.gate3 is not None and rnd.gate3.slide_scores:
        return max(s.slide for s in rnd.gate3.slide_scores)
    if slide_map is not None and slide_map.entries:
        return max(e.slide for e in slide_map.entries)
    if rnd.locked_slides:
        return max(rnd.locked_slides)
    return 0


def export_allowed(
    run: Run,
    *,
    round_n: int,
    slide_map: SlideMap | None = None,
) -> tuple[bool, str]:
    """Return whether export is allowed and a human-readable blocker message.

    Allowed only when Gate 1 passes, Gate 2 passes, and every slide is locked.
    Enforced server-side.
    """
    try:
        rnd = _round(run, round_n)
    except KeyError as exc:
        return False, str(exc)

    if rnd.gate1 is None:
        return False, "Gate 1 has not been run"
    if not rnd.gate1.passed:
        failed = [c.name for c in rnd.gate1.checks if not c.passed]
        detail = f" ({', '.join(failed)})" if failed else ""
        return False, f"Gate 1 has not passed{detail}"

    if rnd.gate2 is None:
        return False, "Gate 2 has not been run"
    if not rnd.gate2.passed:
        failed = [c.name for c in rnd.gate2.checks if not c.passed]
        detail = f" ({', '.join(failed)})" if failed else ""
        return False, f"Gate 2 has not passed{detail}"

    n_slides = _slide_count(rnd, slide_map)
    if n_slides < 1:
        return False, "Cannot confirm every slide is locked (slide count unknown)"
    missing = [i for i in range(1, n_slides + 1) if i not in set(rnd.locked_slides)]
    if missing:
        return False, "Every slide must be locked before export. Unlocked: " + ", ".join(
            str(i) for i in missing
        )
    return True, ""


def _claim_by_id(ledger: ClaimLedger) -> dict[str, ClaimLedgerEntry]:
    return {entry.id: entry for entry in ledger.entries}


def build_provenance_md(
    run: Run,
    *,
    round_n: int,
    ledger: ClaimLedger | None = None,
    slide_map: SlideMap | None = None,
) -> str:
    """Build human-readable provenance covering every claim on every slide."""
    rnd = _round(run, round_n)
    ledger = ledger or ClaimLedger(paper_id=run.paper_id, entries=[])
    slide_map = slide_map or SlideMap(entries=[])
    claims = _claim_by_id(ledger)

    lines: list[str] = [
        f"# Provenance — run `{run.id}`, round {round_n}",
        "",
        "This is the audit record for the exported deck. It lists **every text",
        "element placed on a slide** and the source-paper claim it came from.",
        "Open the paper to the cited page and find the verbatim snippet — you",
        "do not need to know how this tool works.",
        "",
        f"- **Paper:** {run.paper_id}",
        f"- **Blueprint:** {run.blueprint_id}",
        f"- **Skill version:** {run.skill_version}",
        f"- **Exported round:** {round_n}",
        "",
    ]

    by_slide: dict[int, list[SlideMapEntry]] = {}
    for entry in slide_map.entries:
        by_slide.setdefault(entry.slide, []).append(entry)

    n_slides = _slide_count(rnd, slide_map)
    slide_ids = sorted(set(by_slide) | set(range(1, n_slides + 1)))
    if not slide_ids:
        lines.append("_No slide text was recorded in the slide map._")
        lines.append("")
        return "\n".join(lines)

    gaps = 0
    for slide in slide_ids:
        lines.append(f"## Slide {slide}")
        lines.append("")
        entries = by_slide.get(slide, [])
        if not entries:
            lines.append("_No text elements were mapped on this slide._")
            lines.append("")
            continue
        for entry in entries:
            text = (entry.text or "").strip()
            lines.append(f"### On-slide text")
            lines.append("")
            lines.append(f"> {text or '_(empty)_'}")
            lines.append("")
            lines.append(f"- **Element id:** `{entry.element_id}`")
            if not entry.claim_ids:
                gaps += 1
                lines.append("- **Source:** UNMAPPED — this text has no claim ledger ID.")
                lines.append("")
                continue
            for cid in entry.claim_ids:
                claim = claims.get(cid)
                if claim is None:
                    gaps += 1
                    lines.append(f"- **Claim `{cid}`:** not found in the claim ledger.")
                    continue
                section = f" ({claim.section})" if claim.section else ""
                lines.append(
                    f"- **Claim `{claim.id}`** — {claim.claim_type.value}, "
                    f"{claim.evidence_class.value}"
                )
                lines.append(f"  - **Source page:** {claim.page}{section}")
                lines.append(f"  - **Verbatim from the paper:** {claim.verbatim}")
            lines.append("")

    lines.append("---")
    lines.append("")
    if gaps:
        lines.append(f"**Gaps:** {gaps} text element(s) could not be traced to a ledger claim.")
    else:
        lines.append("**Gaps:** none. Every on-slide text element traces to a source page.")
    lines.append("")
    return "\n".join(lines)


def build_run_log(run: Run) -> str:
    """Serialize every round, mutation, and human comment with timestamps."""

    def _iso(dt: datetime | None) -> str | None:
        if dt is None:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat()

    def _mutation(m: MutationRecord) -> dict[str, object]:
        return {
            "id": m.id,
            "kind": m.kind.value,
            "text": m.text,
            "origin_comment_id": m.origin_comment_id,
            "rule_id": m.rule_id,
            "timestamp": _iso(m.timestamp),
        }

    def _comment(c: HumanComment) -> dict[str, object]:
        return {
            "id": c.id,
            "slide": c.slide,
            "x": c.x,
            "y": c.y,
            "text": c.text,
            "severity": c.severity.value,
            "criterion_tag": c.criterion_tag,
            "scope": c.scope.value,
        }

    payload = {
        "run_id": run.id,
        "paper_id": run.paper_id,
        "skill_version": run.skill_version,
        "blueprint_id": run.blueprint_id,
        "status": run.status.value,
        "created_at": _iso(run.created_at),
        "updated_at": _iso(run.updated_at),
        "best_round_n": run.best_round_n,
        "rounds": [
            {
                "n": rnd.n,
                "deck_path": rnd.deck_path,
                "token_count": rnd.token_count,
                "cost_usd": rnd.cost_usd,
                "locked_slides": rnd.locked_slides,
                "gate1_passed": None if rnd.gate1 is None else rnd.gate1.passed,
                "gate2_passed": None if rnd.gate2 is None else rnd.gate2.passed,
                "deck_score": None if rnd.gate3 is None else rnd.gate3.deck_score,
                "mutations": [_mutation(m) for m in rnd.mutations],
                "comments": [_comment(c) for c in rnd.comments],
            }
            for rnd in run.rounds
        ],
    }
    return json.dumps(payload, indent=2) + "\n"


def _load_json_model(path: Path, model):
    if not path.is_file():
        return None
    return model.model_validate_json(path.read_text(encoding="utf-8"))


def _copy_into_zip(zf: zipfile.ZipFile, src: Path, arcname: str) -> None:
    zf.write(src, arcname=arcname)


def create_bundle(
    run_id: str,
    *,
    round_n: int | None = None,
    output_path: Path | str | None = None,
    store: RunStore | None = None,
) -> ExportBundleResult:
    """Zip deck.pptx, deck.pdf, provenance.md, scores.json, skill_version.txt, run_log.json.

    Raises
    ------
    PermissionError
        If export preconditions are not met.
    """
    run_store = store or RunStore()
    run = run_store.get_run(run_id)
    n = round_n or run.best_round_n or (run.rounds[-1].n if run.rounds else None)
    if n is None:
        raise PermissionError("no round available to export")

    rdir = run_store.round_dir(run_id, n)
    run_dir = run_store.run_dir(run_id)
    slide_map = _load_json_model(rdir / "slide_map.json", SlideMap) or SlideMap()
    ledger = _load_json_model(run_dir / "ledger.json", ClaimLedger) or ClaimLedger(
        paper_id=run.paper_id
    )
    comments_file = _load_json_model(rdir / "comments.json", CommentsFile)
    if comments_file is not None:
        rnd = _round(run, n)
        if not rnd.comments:
            rnd.comments = list(comments_file.comments)

    allowed, message = export_allowed(run, round_n=n, slide_map=slide_map)
    if not allowed:
        raise PermissionError(message)

    rnd = _round(run, n)
    pptx = Path(rnd.deck_path) if rnd.deck_path else rdir / "deck.pptx"
    if not pptx.is_file():
        pptx = rdir / "deck.pptx"
    pdf = rdir / "deck.pdf"
    if not pptx.is_file() or not pdf.is_file():
        raise FileNotFoundError(
            f"export requires deck.pptx and deck.pdf in {rdir} "
            f"(pptx={pptx.is_file()}, pdf={pdf.is_file()})"
        )

    scores: Gate3Result | None = rnd.gate3
    if scores is None:
        scores = _load_json_model(rdir / "gate3.json", Gate3Result)

    dest = Path(output_path) if output_path is not None else run_dir / f"export_round_{n}.zip"
    dest.parent.mkdir(parents=True, exist_ok=True)

    provenance = build_provenance_md(run, round_n=n, ledger=ledger, slide_map=slide_map)
    run_log = build_run_log(run)
    scores_json = (
        scores.model_dump_json(indent=2) + "\n"
        if scores is not None
        else json.dumps({"gate": "gate3", "note": "No Gate 3 report for this round"}, indent=2)
        + "\n"
    )

    with zipfile.ZipFile(dest, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        _copy_into_zip(zf, pptx, "deck.pptx")
        _copy_into_zip(zf, pdf, "deck.pdf")
        zf.writestr("provenance.md", provenance)
        zf.writestr("scores.json", scores_json)
        zf.writestr("skill_version.txt", f"{run.skill_version}\n")
        zf.writestr("run_log.json", run_log)

    return ExportBundleResult(
        path=str(dest),
        run_id=run_id,
        round_n=n,
        contents=list(BUNDLE_FILES),
    )
