# Railway deploy

Generate is async (start + SSE). Venice never writes a `.pptx`.

The public domain (`madarwin.up.railway.app`) is the **backend** service.
That process now serves the product UI at `/` when a Next.js export is present
(`frontend/out` or `backend/web`). `/health`, `/docs`, and `/api/*` stay on FastAPI.
The browser calls same-origin `/api`, so no `NEXT_PUBLIC_API_BASE` is required.

A second frontend service is optional.

## Backend service (current public URL)

- Root: **repo root** (not `/backend` — `pyproject.toml`, skills, and blueprints live at the root)
- Builder: **Dockerfile** → `Dockerfile.backend` (preferred; installs LibreOffice + fonts + exports the UI)
- Fallback: if Railway uses **Railpack** instead of the Dockerfile, `requirements.txt`
  is required (Railpack's pip installer ignores a setuptools `pyproject.toml` alone).
  `railpack.json` then:
  - builds the Next.js static export into `backend/web`
  - starts `python -m uvicorn app.api.app:app --host 0.0.0.0 --port ${PORT:-8000}`
    (`python -m` because the uvicorn binary is often missing from PATH).
  Do **not** add a root `railway.toml` that pins `Dockerfile.backend` — that would
  also apply to an optional frontend service.
- Required env:
  - `VENICE_API_KEY`
  - `VENICE_MODEL=claude-opus-4-8`
  - `VENICE_BASE_URL=https://api.venice.ai/api/v1`
  - `CORS_ORIGINS` — frontend URL, or `*`
  - `MA_DARWIN_RELAX_FONTS=1` (Liberation Sans / Carlito stand in for Arial / Calibri)
- Optional: `MA_DARWIN_RUNS_DIR=/data/runs` + a volume on `/data`
- Optional: `MA_DARWIN_FRONTEND_DIR` — override path to a built `index.html` directory
- Health: `GET /health` and `GET /health/capabilities`

The image installs:

| Need | Package |
|---|---|
| Skill PPTX + editable OOXML charts | `python-pptx`, `lxml`, `xlsxwriter` |
| Last-resort raster charts | `matplotlib`, `numpy`, `pillow` |
| Ingest | `pymupdf`, `pypdf`, `pdfplumber` |
| Render / PDF | `cairosvg`, `reportlab`, `poppler-utils` |
| Thumbnails / visual QA | **LibreOffice Impress (`soffice`)** |
| Fonts | Liberation Sans, Carlito, DejaVu |
| Product UI | Next.js static export served at `/` |

Confirm after deploy:

```bash
curl https://YOUR-BACKEND.up.railway.app/health/capabilities
curl -I https://YOUR-BACKEND.up.railway.app/
```

`capabilities.soffice` should be `true`. `packages.matplotlib` / `python-pptx` should be `true`.
`GET /` should return HTML (`MA·Darwin`), not `{"detail":"Not Found"}`.

## Optional frontend service

Use this only if you want Next.js on its own Railway service and domain.

- Root: repo root
- Builder: **Dockerfile** → `Dockerfile.frontend`
- Env:
  - `API_UPSTREAM=https://YOUR-BACKEND.up.railway.app` (no trailing slash)
  - `NEXT_PUBLIC_API_BASE=` (empty — browser talks same-origin `/api`, Next rewrites)
- Attach the public domain to this service if it should be the site visitors open

## Local

```bash
pip install -e ".[dev]"
# Windows: Arial/Calibri are already present.
# macOS: brew install --cask libreoffice
# Debian/Ubuntu: sudo apt install libreoffice-impress fonts-liberation fonts-crosextra-carlito
cp .env.example .env   # set VENICE_API_KEY
cd frontend && npm install && npm run dev
# other terminal:
set PYTHONPATH=backend
uvicorn app.api.app:app --reload --port 8000
```

Point the UI at the API with `API_UPSTREAM=http://localhost:8000` in `frontend/.env.local`.

To preview the combined Railway shape locally:

```bash
cd frontend && npm run build:static
set PYTHONPATH=backend
uvicorn app.api.app:app --port 8000
```
