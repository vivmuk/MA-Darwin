# MA-Darwin

One PDF → one M2M PowerPoint. Venice **Claude Opus 4.8** plans the deck as JSON.
Railway (or your laptop) writes a real `.pptx` with the `sundai-powerpoint` skill
scripts — **editable OOXML charts first**. Then Zac’s Darwin loop revises the
skill, regenerates, and keeps the winner.

## Architecture

- **Brain:** Venice `claude-opus-4-8` (never emits a PowerPoint file)
- **Hands:** `skills/sundai-powerpoint/scripts/add_slide.py` + `add_editable_chart.py`
- **Ingest:** Jay’s page-level claim ledger (`pymupdf` / `pdfplumber` / `pypdf`)
- **UI:** Viv’s intro → Zac’s lock-eval → AI eval → skill mutate → A/B
- **Deploy:** two Railway services — see [docs/RAILWAY.md](docs/RAILWAY.md)

## Deck-generation environment

These must be present for a beautiful, skill-faithful deck:

| Layer | What |
|---|---|
| Writer | `python-pptx`, `lxml`, `xlsxwriter` |
| Charts | `add_editable_chart.py` (native `ppt/charts` + Excel embed). `matplotlib` + `numpy` + `pillow` only if OOXML fails — disclosed in speaker notes |
| Ingest | `pymupdf`, `pypdf`, `pdfplumber` |
| Render | `cairosvg`, `reportlab` |
| QA | **LibreOffice `soffice`** for thumbnails / visual QA |
| Fonts | Arial + Calibri on Windows; Liberation Sans + Carlito on Linux/Railway |

`GET /health/capabilities` reports what the running backend actually has.

## Local

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
copy .env.example .env
# set VENICE_API_KEY  (VENICE_MODEL defaults to claude-opus-4-8)
pytest
set PYTHONPATH=backend
uvicorn app.api.app:app --reload --port 8000
```

Frontend (other terminal):

```bash
cd frontend
npm install
echo API_UPSTREAM=http://localhost:8000> .env.local
npm run dev
```

LibreOffice (thumbnails):

- Windows: install LibreOffice and keep `soffice.exe` on PATH
- macOS: `brew install --cask libreoffice`
- Debian/Ubuntu: `sudo apt install libreoffice-impress fonts-liberation fonts-crosextra-carlito`

## Layout

```
backend/app/                 # FastAPI, ledger, planner, skill writer, gates
skills/sundai-powerpoint/    # Skill + scripts + Darwin lineage/
frontend/                    # Next.js — intro + Darwin loop
Dockerfile.backend           # Python + LibreOffice + fonts
Dockerfile.frontend          # Next.js
requirements.txt             # Triggers Railpack pip install (pyproject.toml alone is not enough)
railpack.json                # Railpack start command if Railway skips the Dockerfile
docs/RAILWAY.md              # Two-service deploy
```
