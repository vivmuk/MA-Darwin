"""Gate 3 — vision judge (PRD §7.8 / Prompt 5)."""

from __future__ import annotations

import json
import logging
import math
import os
import re
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable, Optional

import fitz
import yaml

from app.config import get_threshold
from app.models.blueprint import Blueprint
from app.models.common import IssueCoordinates
from app.models.gates import (
    Gate3Result,
    JudgeCriterionScore,
    SlideJudgeResult,
    SlideScoreSummary,
)
from app.models.rubric import Rubric, RubricCriterion
from app.paths import CONFIG_DIR, PROMPTS_DIR

logger = logging.getLogger(__name__)

DEFAULT_RUBRIC = CONFIG_DIR / "rubric.yaml"
DEFAULT_PROMPT = PROMPTS_DIR / "judge.md"

# Tokens the judge must never receive (PRD §7.8 — blind to history).
_BLIND_FORBIDDEN = frozenset(
    {
        "round",
        "round_n",
        "round_number",
        "previous",
        "previous_score",
        "prior_score",
        "prior_scores",
        "last_score",
        "history",
        "generator",
        "generator_reasoning",
        "reasoning",
        "mutations",
        "mutation",
        "skill_diff",
        "best_round_n",
    }
)

_CHART_ROLES = frozenset({"primary_endpoint", "key_secondary"})
_ANCHOR_PLACEHOLDER = "{{anchors}}"


def load_rubric(rubric_path: Path | str | None = None) -> Rubric:
    """Load criterion weights and score-band anchors from ``config/rubric.yaml``."""
    path = Path(rubric_path) if rubric_path is not None else DEFAULT_RUBRIC
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    if not isinstance(data, dict):
        raise ValueError(f"rubric must be a mapping: {path}")
    return Rubric.model_validate(data)


def render_judge_prompt(
    rubric: Rubric,
    *,
    role: str,
    scope: str,
    prompt_path: Path | str | None = None,
) -> str:
    """Fill ``prompts/judge.md`` with anchors from config (never inline in the file)."""
    path = Path(prompt_path) if prompt_path is not None else DEFAULT_PROMPT
    template = path.read_text(encoding="utf-8")
    if "0:" in template and "No clear focal point" in template:
        raise AssertionError("anchors must not be inlined in the judge prompt file")
    criteria = rubric.deck_criteria if scope == "deck" else rubric.slide_criteria
    rendered = template.replace(_ANCHOR_PLACEHOLDER, _format_anchors(criteria))
    rendered = rendered.replace("{{role}}", role)
    rendered = rendered.replace("{{scope}}", scope)
    return rendered


def assert_judge_is_blind(payload: Any) -> None:
    """Assert the judge context contains no round, history, or generator reasoning."""
    leaked = _forbidden_keys(payload)
    if leaked:
        raise AssertionError(f"judge payload is not blind; leaked keys: {sorted(leaked)}")


def build_contact_sheet(slide_images: list[Path | str], output_path: Path | str) -> Path:
    """Compose all slide PNGs into one contact-sheet image for deck-level criteria."""
    paths = [Path(p) for p in slide_images]
    if not paths:
        raise ValueError("contact sheet requires at least one slide image")
    pixmaps = [fitz.Pixmap(str(p)) for p in paths]
    cols = min(3, len(pixmaps))
    rows = math.ceil(len(pixmaps) / cols)
    cell_w = max(p.width for p in pixmaps)
    cell_h = max(p.height for p in pixmaps)
    gap = 16
    page_w = cols * cell_w + gap * (cols + 1)
    page_h = rows * cell_h + gap * (rows + 1)
    doc = fitz.open()
    page = doc.new_page(width=page_w, height=page_h)
    page.draw_rect(page.rect, color=(0.94, 0.94, 0.94), fill=(0.94, 0.94, 0.94))
    for i, src in enumerate(paths):
        r, c = divmod(i, cols)
        rect = fitz.Rect(
            gap + c * cell_w,
            gap + r * cell_h,
            gap + c * cell_w + pixmaps[i].width,
            gap + r * cell_h + pixmaps[i].height,
        )
        page.insert_image(rect, filename=str(src))
    dest = Path(output_path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    page.get_pixmap(dpi=100).save(dest)
    doc.close()
    return dest


def judge_slide(
    image_path: Path | str,
    *,
    role: str,
    rubric: Rubric,
    prompt_path: Path | str | None = None,
    has_data_visual: bool | None = None,
    backend: str | None = None,
) -> SlideJudgeResult:
    """Score one slide image against per-slide rubric criteria."""
    prompt = render_judge_prompt(rubric, role=role, scope="slide", prompt_path=prompt_path)
    payload = _blind_payload(role=role, scope="slide", rubric=rubric)
    assert_judge_is_blind(payload)
    assert_judge_is_blind(prompt)

    chart_applicable = _chart_applicable(role, has_data_visual)
    scores = _invoke_judge(
        image_path,
        rubric.slide_criteria,
        prompt,
        payload,
        backend=backend,
        chart_applicable=chart_applicable,
        scope="slide",
        role=role,
    )
    slide_no = 1
    for item in scores:
        item.slide = slide_no
        item.scope = "slide"
    return SlideJudgeResult(
        slide=slide_no,
        role=role,
        score=_renormalized_score(scores),
        criteria=scores,
    )


def judge_deck_level(
    contact_sheet_path: Path | str,
    *,
    rubric: Rubric,
    prompt_path: Path | str | None = None,
    backend: str | None = None,
) -> list[JudgeCriterionScore]:
    """Score deck-level criteria (consistency, executive feel) once on the contact sheet."""
    prompt = render_judge_prompt(rubric, role="", scope="deck", prompt_path=prompt_path)
    payload = _blind_payload(role="", scope="deck", rubric=rubric)
    assert_judge_is_blind(payload)
    assert_judge_is_blind(prompt)
    scores = _invoke_judge(
        contact_sheet_path,
        rubric.deck_criteria,
        prompt,
        payload,
        backend=backend,
        chart_applicable=False,
        scope="deck",
        role="",
    )
    for item in scores:
        item.scope = "deck"
        item.slide = None
    return scores


def median_criterion_scores(
    runs: list[list[JudgeCriterionScore]],
) -> list[JudgeCriterionScore]:
    """Reduce N judge runs to median score per criterion (temperature 0, N=3 default)."""
    if not runs:
        return []
    by_id: dict[str, list[JudgeCriterionScore]] = defaultdict(list)
    for run in runs:
        for item in run:
            by_id[item.criterion].append(item)
    merged: list[JudgeCriterionScore] = []
    for criterion, items in by_id.items():
        numeric = [i.score for i in items if i.score is not None]
        if not numeric:
            template = items[0]
            merged.append(template.model_copy(update={"score": None}))
            continue
        med = float(statistics.median(numeric))
        closest = min(items, key=lambda i: abs((i.score if i.score is not None else med) - med))
        merged.append(closest.model_copy(update={"score": med}))
        _ = criterion
    return merged


def run_gate3(
    *,
    slide_images: list[Path | str],
    blueprint: Blueprint,
    rubric_path: Path | str | None = None,
    prompt_path: Path | str | None = None,
    judge_runs: int = 3,
    temperature: float = 0.0,
    threshold: float | None = None,
    backend: str | None = None,
    output_dir: Path | str | None = None,
) -> Gate3Result:
    """Run the vision judge and produce ``gate3.json``."""
    if temperature != 0.0:
        raise AssertionError("judge must run at temperature 0 (PRD §7.8)")
    if judge_runs < 1:
        raise ValueError("judge_runs must be >= 1")

    images = [Path(p) for p in slide_images]
    if not images:
        raise ValueError("run_gate3 requires rendered slide PNGs")
    rubric = load_rubric(rubric_path)
    pass_at = float(threshold if threshold is not None else get_threshold("judge_threshold", 75))

    roles = [s.role for s in blueprint.slides]
    visual_flags = [s.requires_visual for s in blueprint.slides]

    slide_results: list[SlideJudgeResult] = []
    for index, image in enumerate(images):
        role = roles[index] if index < len(roles) else "unknown"
        has_visual = visual_flags[index] if index < len(visual_flags) else role in _CHART_ROLES
        run_sets: list[list[JudgeCriterionScore]] = []
        for _ in range(judge_runs):
            one = judge_slide(
                image,
                role=role,
                rubric=rubric,
                prompt_path=prompt_path,
                has_data_visual=has_visual,
                backend=backend,
            )
            run_sets.append(one.criteria)
        median = median_criterion_scores(run_sets)
        for item in median:
            item.slide = index + 1
            item.scope = "slide"
        slide_results.append(
            SlideJudgeResult(
                slide=index + 1,
                role=role,
                score=_renormalized_score(median),
                criteria=median,
            )
        )

    sheet_path = images[0].parent / "_contact_sheet.png"
    build_contact_sheet(images, sheet_path)
    deck_runs = [
        judge_deck_level(sheet_path, rubric=rubric, prompt_path=prompt_path, backend=backend)
        for _ in range(judge_runs)
    ]
    deck_criteria = median_criterion_scores(deck_runs)
    for item in deck_criteria:
        item.scope = "deck"
        item.slide = None

    slide_scores = [SlideScoreSummary(slide=s.slide, score=s.score) for s in slide_results]
    deck_score = statistics.mean(s.score for s in slide_results)
    worst = min(s.score for s in slide_results)
    flat = [c for s in slide_results for c in s.criteria] + list(deck_criteria)
    result = Gate3Result(
        gate="gate3",
        deck_score=round(deck_score, 2),
        worst_slide_score=round(worst, 2),
        slide_scores=slide_scores,
        slide_results=slide_results,
        deck_criteria=deck_criteria,
        criteria=flat,
        passed=deck_score >= pass_at,
        judge_runs=judge_runs,
        temperature=temperature,
    )
    if output_dir is not None:
        write_gate3_json(output_dir, result)
    return result


def write_gate3_json(output_dir: Path | str, result: Gate3Result) -> Path:
    """Write ``gate3.json`` under ``output_dir`` (typically ``runs/{id}/round_{n}/``)."""
    dest = Path(output_dir)
    dest.mkdir(parents=True, exist_ok=True)
    path = dest / "gate3.json"
    path.write_text(result.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return path


def _format_anchors(criteria: Iterable[RubricCriterion]) -> str:
    blocks: list[str] = []
    for item in criteria:
        lines = [f"### {item.id} — {item.name} (weight {item.weight})"]
        if item.na_when:
            lines.append(f"- N/A when: {item.na_when}")
        for band, text in sorted(item.anchors.items(), key=lambda kv: float(kv[0])):
            lines.append(f"- {band}: {text}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def _blind_payload(*, role: str, scope: str, rubric: Rubric) -> dict[str, Any]:
    criteria = rubric.deck_criteria if scope == "deck" else rubric.slide_criteria
    return {
        "role": role,
        "scope": scope,
        "criteria": [
            {
                "id": c.id,
                "name": c.name,
                "weight": c.weight,
                "na_when": c.na_when,
                "anchors": c.anchors,
            }
            for c in criteria
        ],
    }


def _forbidden_keys(payload: Any) -> set[str]:
    found: set[str] = set()

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                lowered = str(key).lower()
                if lowered in _BLIND_FORBIDDEN:
                    found.add(lowered)
                walk(value)
        elif isinstance(node, (list, tuple)):
            for item in node:
                walk(item)
        elif isinstance(node, str):
            lowered = node.lower()
            for token in _BLIND_FORBIDDEN:
                if re.search(rf"(?<![a-z]){re.escape(token)}(?![a-z])", lowered):
                    # Prompt file mentions the ban list on purpose; that is allowed.
                    if "you are blind" in lowered or "you will not be told" in lowered:
                        continue
                    if token in {"round", "reasoning"} and (
                        "round number" in lowered or "generator reasoning" in lowered
                    ):
                        continue
                    found.add(token)

    walk(payload)
    return found


def _chart_applicable(role: str, has_data_visual: bool | None) -> bool:
    if has_data_visual is not None:
        return bool(has_data_visual)
    return role in _CHART_ROLES


def _renormalized_score(criteria: list[JudgeCriterionScore]) -> float:
    applicable = [c for c in criteria if c.score is not None]
    weight_sum = sum(c.weight for c in applicable)
    if weight_sum <= 0:
        return 0.0
    earned = sum(float(c.score) for c in applicable)
    return 100.0 * earned / weight_sum


def _invoke_judge(
    image_path: Path | str,
    criteria: list[RubricCriterion],
    prompt: str,
    payload: dict[str, Any],
    *,
    backend: str | None,
    chart_applicable: bool,
    scope: str,
    role: str,
) -> list[JudgeCriterionScore]:
    from app.llm_env import llm_configured

    mode = (backend or os.environ.get("MA_DARWIN_JUDGE") or "auto").lower()
    if mode == "llm" or (mode == "auto" and llm_configured()):
        try:
            parsed = _llm_judge(image_path, prompt)
            if parsed:
                return _coerce_scores(parsed, criteria, chart_applicable=chart_applicable, scope=scope)
        except Exception as exc:  # noqa: BLE001
            logger.warning("vision judge LLM failed (%s); using heuristic", exc)
    features = _image_features(Path(image_path))
    return _heuristic_scores(
        features,
        criteria,
        chart_applicable=chart_applicable,
        scope=scope,
        role=role,
    )


def _llm_judge(image_path: Path | str, prompt: str) -> list[dict[str, Any]]:
    import base64

    from app.llm_env import chat_text

    raw = Path(image_path).read_bytes()
    b64 = base64.standard_b64encode(raw).decode("ascii")
    text = chat_text(
        system=prompt,
        user=[
            {"type": "text", "text": "Score this image against the rubric. JSON array only."},
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{b64}"},
            },
        ],
        max_tokens=2048,
        temperature=0,
    )
    if not text:
        return []
    return _parse_json_array(text)


def _parse_json_array(text: str) -> list[dict[str, Any]]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1:
        return []
    parsed = json.loads(text[start : end + 1])
    if not isinstance(parsed, list):
        return []
    return [item for item in parsed if isinstance(item, dict)]


def _coerce_scores(
    raw: list[dict[str, Any]],
    criteria: list[RubricCriterion],
    *,
    chart_applicable: bool,
    scope: str,
) -> list[JudgeCriterionScore]:
    by_id = {str(item.get("criterion") or item.get("id")): item for item in raw}
    out: list[JudgeCriterionScore] = []
    for spec in criteria:
        if spec.na_when == "no_data_visual" and not chart_applicable:
            out.append(
                JudgeCriterionScore(
                    criterion=spec.id,
                    weight=spec.weight,
                    score=None,
                    rationale="No data visual on this slide; criterion marked N/A.",
                    coordinates=None,
                    scope=scope,  # type: ignore[arg-type]
                )
            )
            continue
        item = by_id.get(spec.id, {})
        score = item.get("score")
        if score is not None:
            score = max(0.0, min(float(spec.weight), float(score)))
        coords = None
        if item.get("x") is not None and item.get("y") is not None:
            coords = IssueCoordinates(x=float(item["x"]), y=float(item["y"]))
        out.append(
            JudgeCriterionScore(
                criterion=spec.id,
                weight=spec.weight,
                score=score,
                rationale=str(item.get("rationale") or ""),
                coordinates=coords,
                scope=scope,  # type: ignore[arg-type]
            )
        )
    return out


def _image_features(path: Path) -> dict[str, float]:
    pix = fitz.Pixmap(str(path))
    if pix.n - pix.alpha != 3:
        pix = fitz.Pixmap(fitz.csRGB, pix)
    width, height = pix.width, pix.height
    step = max(1, min(width, height) // 80)
    lumas: list[float] = []
    colors: set[tuple[int, int, int]] = set()
    header: list[float] = []
    body: list[float] = []
    edge = 0.0
    edge_n = 0
    white_n = 0
    sat_n = 0
    n = 0
    side_margin: list[float] = []
    prev_row: list[float] | None = None
    for y in range(0, height, step):
        row: list[float] = []
        for x in range(0, width, step):
            r, g, b = pix.pixel(x, y)[:3]
            luma = 0.2126 * r + 0.7152 * g + 0.0722 * b
            lumas.append(luma)
            colors.add((r // 32, g // 32, b // 32))
            row.append(luma)
            n += 1
            if luma >= 235:
                white_n += 1
            mx = r / 255
            mn = min(r, g, b) / 255
            mxv = max(r, g, b) / 255
            if mxv - mn > 0.35:
                sat_n += 1
            if x / width < 0.07 or x / width > 0.93:
                side_margin.append(luma)
            if y < height * 0.14:
                header.append(luma)
            else:
                body.append(luma)
            if len(row) > 1:
                edge += abs(row[-1] - row[-2])
                edge_n += 1
        if prev_row is not None:
            for a, b_ in zip(row, prev_row):
                edge += abs(a - b_)
                edge_n += 1
        prev_row = row
    lumas.sort()

    def pct(p: float) -> float:
        if not lumas:
            return 0.0
        return lumas[min(len(lumas) - 1, int(p * (len(lumas) - 1)))]

    contrast = pct(0.9) - pct(0.1)
    header_mean = statistics.mean(header) if header else 0.0
    body_mean = statistics.mean(body) if body else 0.0
    side_white = (
        sum(1 for v in side_margin if v >= 230) / len(side_margin) if side_margin else 0.0
    )
    return {
        "contrast": contrast,
        "std": statistics.pstdev(lumas) if len(lumas) > 1 else 0.0,
        "color_count": float(len(colors)),
        "header_delta": abs(header_mean - body_mean),
        "white_frac": white_n / n if n else 0.0,
        "sat_frac": sat_n / n if n else 0.0,
        "side_white": side_white,
        "edge": (edge / edge_n) if edge_n else 0.0,
        "mean_luma": statistics.mean(lumas) if lumas else 0.0,
    }


def _heuristic_scores(
    features: dict[str, float],
    criteria: list[RubricCriterion],
    *,
    chart_applicable: bool,
    scope: str,
    role: str,
) -> list[JudgeCriterionScore]:
    """Deterministic visual scoring. Rationales quote rubric anchors (config, not prompt)."""
    _ = role
    out: list[JudgeCriterionScore] = []
    for spec in criteria:
        if spec.na_when == "no_data_visual" and not chart_applicable:
            out.append(
                JudgeCriterionScore(
                    criterion=spec.id,
                    weight=spec.weight,
                    score=None,
                    rationale="No data visual on this slide; criterion marked N/A.",
                    scope=scope,  # type: ignore[arg-type]
                )
            )
            continue
        band, coords = _pick_band(spec.id, features, scope)
        score = _anchor_score(spec, band)
        rationale = spec.anchors.get(str(band)) or spec.anchors.get(band) or ""
        # YAML keys may be loaded as ints; try both.
        if not rationale:
            for key, text in spec.anchors.items():
                if str(key) == str(band):
                    rationale = text
                    break
        out.append(
            JudgeCriterionScore(
                criterion=spec.id,
                weight=spec.weight,
                score=score,
                rationale=rationale,
                coordinates=IssueCoordinates(x=coords[0], y=coords[1]) if coords else None,
                scope=scope,  # type: ignore[arg-type]
            )
        )
    return out


def _anchor_score(spec: RubricCriterion, band: int | str) -> float:
    key = str(band)
    if key in spec.anchors:
        return float(key)
    for raw in spec.anchors:
        if str(raw) == key:
            return float(raw)
    return 0.0


def _pick_band(
    criterion_id: str, features: dict[str, float], scope: str
) -> tuple[int, Optional[tuple[float, float]]]:
    contrast = features["contrast"]
    header_delta = features["header_delta"]
    white_frac = features["white_frac"]
    sat_frac = features["sat_frac"]
    side_white = features["side_white"]
    edge = features["edge"]
    colors = features["color_count"]
    std = features["std"]

    clean = header_delta >= 80 and white_frac >= 0.45 and side_white >= 0.5 and sat_frac < 0.25
    messy = header_delta < 30 and (white_frac < 0.2 or sat_frac > 0.35 or side_white < 0.25)

    if criterion_id == "visual_hierarchy":
        if header_delta >= 55 and contrast >= 90:
            return 15, None
        if header_delta >= 35:
            return 10, None
        if header_delta >= 15:
            return 5, (0.5, 0.12)
        return 0, (0.5, 0.12)
    if criterion_id == "layout_composition":
        if side_white >= 0.7 and white_frac >= 0.5:
            return 15, None
        if side_white >= 0.4 and white_frac >= 0.3:
            return 10, None
        if not messy:
            return 5, (0.5, 0.5)
        return 0, (0.5, 0.5)
    if criterion_id == "information_density":
        if 12 <= edge <= 26 and 20 <= std <= 80:
            return 10, None
        if edge < 45:
            return 7, None
        if edge < 60:
            return 4, (0.5, 0.55)
        return 0, (0.5, 0.55)
    if criterion_id == "typography":
        if clean:
            return 10, None
        if not messy:
            return 7, None
        if contrast >= 40:
            return 4, (0.4, 0.2)
        return 0, (0.4, 0.2)
    if criterion_id == "visual_storytelling":
        if header_delta >= 45 and not messy:
            return 15, None
        if header_delta >= 25:
            return 10, None
        if header_delta >= 10:
            return 5, (0.5, 0.2)
        return 0, (0.5, 0.2)
    if criterion_id == "charts_data_visualization":
        if clean:
            return 10, None
        if not messy:
            return 7, None
        return 0, (0.55, 0.55)
    if criterion_id == "colour_contrast":
        if contrast >= 100 and colors <= 8:
            return 8, None
        if contrast >= 70:
            return 6, None
        if contrast >= 45:
            return 3, (0.5, 0.5)
        return 0, (0.5, 0.5)
    if criterion_id == "professional_polish":
        if clean:
            return 5, None
        if not messy:
            return 4, None
        if not (colors > 18 and edge > 45):
            return 2, (0.2, 0.2)
        return 0, (0.2, 0.2)
    if criterion_id == "consistency_design_system":
        if colors <= 10 and contrast >= 80:
            return 7, None
        if colors <= 14:
            return 5, None
        if colors <= 18:
            return 3, (0.5, 0.5)
        return 0, (0.5, 0.5)
    if criterion_id == "executive_premium_feel":
        if clean:
            return 5, None
        if not messy:
            return 4, None
        if contrast >= 40:
            return 2, (0.5, 0.5)
        return 0, (0.5, 0.5)
    _ = scope
    return 0, (0.5, 0.5)
