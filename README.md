# MA-Darwin

Generate medical affairs MSL decks from research papers against a verified
claim ledger, grade them through four gates, and evolve the generation skill
from human feedback.

See [docs/MA-Darwin-PRD.md](docs/MA-Darwin-PRD.md) for the product requirements.

## Status

Phase 1 scaffold: `backend/app` package, Pydantic models (PRD §8), run storage,
`config/defaults.yaml`, and `python -m app.cli new-run`.

## Stack

- Backend: Python ≥3.11, FastAPI, python-pptx, pymupdf
- Frontend: Next.js App Router + Tailwind (Phase 7)
- Storage: SQLite metadata + `runs/{run_id}/round_{n}/` artifacts
- Skills: versioned files under `skills/`

## Development

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate
pip install -e ".[dev]"
pytest
python -m app.cli new-run --paper path/to/paper.pdf --brief "Create an 8 slide MSL deck"
```

## Layout

```
backend/app/         # Python package (models, storage, gates, …)
backend/config/      # Thresholds and defaults
backend/prompts/     # Model prompts (later phases)
backend/tests/       # Pytest suite
blueprints/          # Slide role blueprints (data, not code)
skills/vN/           # Versioned generation skill
runs/                # Per-run immutable artifacts
frontend/            # Next.js UI (Phase 7)
docs/                # PRD and design docs
```
