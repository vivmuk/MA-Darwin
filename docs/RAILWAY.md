# Railway deploy (two services)

MA-Darwin ships as **two Railway services**. Generate is async (start + SSE). Venice never writes a `.pptx`.

## Backend service

- Root: repo root
- Builder: **Dockerfile** → `Dockerfile.backend`
- Required env:
  - `VENICE_API_KEY`
  - `VENICE_MODEL=claude-opus-4-8`
  - `VENICE_BASE_URL=https://api.venice.ai/api/v1`
  - `CORS_ORIGINS` — frontend URL, or `*`
  - `MA_DARWIN_RELAX_FONTS=1` (Liberation Sans / Carlito stand in for Arial / Calibri)
- Optional: `MA_DARWIN_RUNS_DIR=/data/runs` + a volume on `/data`
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

Confirm after deploy:

```bash
curl https://YOUR-BACKEND.up.railway.app/health/capabilities
```

`capabilities.soffice` should be `true`. `packages.matplotlib` / `python-pptx` should be `true`.

## Frontend service

- Root: repo root
- Builder: **Dockerfile** → `Dockerfile.frontend`
- Env:
  - `API_UPSTREAM=https://YOUR-BACKEND.up.railway.app` (no trailing slash)
  - `NEXT_PUBLIC_API_BASE=` (empty — browser talks same-origin `/api`, Next rewrites)

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
