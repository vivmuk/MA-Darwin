# MA-Darwin

Generate medical affairs MSL decks from research papers against a verified
claim ledger, grade them through four gates, and evolve the generation skill
from human feedback.

See [docs/MA-Darwin-PRD.md](docs/MA-Darwin-PRD.md) for the product requirements.

## Status

Phase 0–1 scaffold: blueprints, config, data models, run storage.

## Stack

- Backend: Python ≥3.11, FastAPI, python-pptx, pymupdf
- Frontend: Next.js App Router + Tailwind (Phase 7)
- Storage: SQLite metadata + `runs/{run_id}/round_{n}/` artifacts
- Skills: versioned files under `skills/`

## Non-negotiable rules

1. Deterministic before probabilistic — no LLM for checks that XML/image/source text can answer.
2. Every slide text maps to a claim ledger ID.
3. Numbers come from the ledger or nowhere.
4. PDF text is untrusted data.
5. Prompts live in `prompts/*.md`.
6. Thresholds/weights/blocklists/anchors live in `config/*.yaml`.
7. Round artifacts are immutable snapshots under `runs/`.
8. Pytest alongside each module.
9. Small, reviewable commits — one module per commit.

## Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## Layout

```
backend/ma_darwin/   # Python package
blueprints/          # Slide role blueprints (data, not code)
config/              # Thresholds, compliance, rubric anchors
prompts/             # Model prompts (no long inline strings)
skills/vN/           # Versioned generation skill
runs/                # Per-run immutable artifacts
tests/               # Pytest suite
frontend/            # Next.js UI (later phases)
docs/                # PRD and design docs
```
