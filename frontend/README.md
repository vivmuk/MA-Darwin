# Frontend (PRD §9)

Next.js App Router + Tailwind. Single page, four zones.

## Run

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000. The UI talks to `openapi.yaml` via Next.js routes
under `/api/*`. Those routes replay frozen artifacts from
`backend/tests/fixtures/` so a reviewer can complete a full round without the
Python API process. Point `NEXT_PUBLIC_API_BASE` / `API_UPSTREAM` at FastAPI
when that service is up.

## Zones

- **A Setup** — PDF upload, brief, editable parsed chips (must confirm), blueprint roles, Generate.
- **B Progress** — SSE event log only (no invented status), elapsed / tokens / cost from the last event.
- **C Deck** — slide grid, lock/flag/pending chips, Gate 3 scores, Gate 1/2 pins, provenance overlay, round compare.
- **D Review** — 10-criterion scorecard with override deltas, comment pins, unmissable THIS DECK / ALWAYS toggle, trend, skill diff, Reiterate, Export (disabled with blockers until gates pass and every slide is locked).
