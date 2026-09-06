"""Darwin loop: lock eval → skill suggestions → mutate sundai-powerpoint lineage."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field

from app.generation.skill_lineage import load_skill_text, propose_skill_version, read_active
from app.llm_env import chat_text, llm_configured
from app.models.run import Round, Run
from app.models.slide import HumanComment


class SkillSuggestion(BaseModel):
    id: str
    text: str
    rationale: str = ""


class SkillSuggestionFile(BaseModel):
    run_id: str
    round_n: int
    skill_version: str
    suggestions: list[SkillSuggestion] = Field(default_factory=list)


def suggest_skill_changes(
    run: Run,
    rnd: Round,
    *,
    output_path: Path | str | None = None,
) -> SkillSuggestionFile:
    comments = rnd.comments
    gate3 = rnd.gate3
    system = (
        "You revise the sundai-powerpoint skill. Propose 1–4 concrete, measurable "
        "house-rule changes (max bullets, chart required, safety table, etc.). "
        "Do not rewrite the whole SKILL.md. Return JSON: "
        '{"suggestions":[{"id":"s1","text":"...","rationale":"..."}]}'
    )
    payload = {
        "skill_version": run.skill_version,
        "skill": load_skill_text(run.skill_version)[:12000],
        "comments": [json.loads(c.model_dump_json()) for c in comments],
        "gate3": json.loads(gate3.model_dump_json()) if gate3 else None,
    }
    suggestions: list[SkillSuggestion] = []
    if llm_configured():
        raw = chat_text(system=system, user=json.dumps(payload), max_tokens=2048, temperature=0)
        parsed = _parse(raw)
        suggestions = parsed
    if not suggestions:
        suggestions = _from_comments(comments)
    artifact = SkillSuggestionFile(
        run_id=run.id,
        round_n=rnd.n,
        skill_version=run.skill_version or read_active(),
        suggestions=suggestions,
    )
    if output_path is not None:
        dest = Path(output_path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(artifact.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return artifact


def apply_skill_suggestions(
    texts: list[str],
    *,
    from_version: str | None = None,
    run_dir: Path | str | None = None,
) -> str:
    """Record a proposed skill version. Does not overwrite repo ``skills/v1``."""
    return propose_skill_version(texts, from_version=from_version, run_dir=run_dir)


def _parse(raw: str) -> list[SkillSuggestion]:
    if not raw:
        return []
    blob = raw.strip()
    start, end = blob.find("{"), blob.rfind("}")
    if start < 0 or end <= start:
        return []
    try:
        data = json.loads(blob[start : end + 1])
    except json.JSONDecodeError:
        return []
    out: list[SkillSuggestion] = []
    for i, item in enumerate(data.get("suggestions") or [], start=1):
        text = str(item.get("text") or "").strip()
        if not text:
            continue
        out.append(
            SkillSuggestion(
                id=str(item.get("id") or f"s{i}"),
                text=text,
                rationale=str(item.get("rationale") or ""),
            )
        )
    return out


def _from_comments(comments: list[HumanComment]) -> list[SkillSuggestion]:
    always = [c for c in comments if c.scope.value == "always"]
    source = always or comments
    out: list[SkillSuggestion] = []
    for i, comment in enumerate(source[:4], start=1):
        out.append(
            SkillSuggestion(
                id=f"s{i}",
                text=comment.text.strip(),
                rationale=f"From human comment {comment.id} ({comment.scope.value})",
            )
        )
    if not out:
        out.append(
            SkillSuggestion(
                id="s1",
                text="Keep quantitative slides to one idea and require an editable clustered-column chart.",
                rationale="Default Darwin suggestion when no comments were filed.",
            )
        )
    return out
