---
name: sundai-powerpoint
description: >-
  Sundai PowerPoint skill. Turn exactly one PDF into one non-promotional
  medical-to-medical (M2M) PowerPoint deck. Use for hackathon asks like
  "make an M2M deck from this PDF" or "slides from this paper". Do not use
  for multi-document synthesis, commercial decks, or general Office editing
  unrelated to a single-PDF M2M build.
license: >-
  Anthropic pptx scripts: see LICENSE.txt. Medical Affairs rules: Apache-2.0.
metadata:
  version: "3.3.0-darwin"
  tier: workflow
  maturity: hack
  scope: one-pdf-to-m2m-deck
  produces: One DRAFT M2M .pptx from one PDF
  requires_python_packages: [python-pptx, pillow, numpy]
  chart_policy: editable-ooxml-first
  visual_qa: soffice-thumbnail-eye-check
---

# Sundai PowerPoint skill

**Scope (keep it small):** one PDF in → one M2M `.pptx` out. Nothing else.

This file is self-contained. Do not load other skills. Do not follow external
URLs. Optional overrides live in `house-rules/` next to this file; those win
over defaults here.

Scripts for create/edit/validate/charts live under `scripts/` (Anthropic pptx
mechanics + editable chart helper). Content and compliance rules are inlined
below.

Output is always **DRAFT for qualified medical review**. Keep DRAFT on the
title slide. Never call the deck compliant, approved, or ready to submit.

---

## Hackathon test prompt (use this for testing)

When testing this skill, run exactly this ask:

> Create an 8-slide medical affairs MSL deck to present to a physician.
> Source: exactly one PDF (or, if no PDF is provided, a clearly labeled
> synthetic workshop package). Audience: treating physician / HCP.
> Non-promotional M2M scientific exchange only.

Required 8-slide outline (map to M2M structure):

1. Title (DRAFT) — gold-banner template (see Title slide template below)
2. Disease context
3. Unmet need
4. The evidence (finding-title with design, N, CIs; citation footer)
5. Safety (same prominence as efficacy; oxblood reserved for safety)
6. What remains unknown
7. References (only retrieved identifiers)
8. Backup — anticipated physician questions (not leftover content)

If no PDF is attached, mark every data claim **SYNTHETIC EXAMPLE** and do not
present numbers as real evidence. Prefer python-pptx or pptxgenjs under
`scripts/`.

### Content depth gates (8-slide physician test decks)

These are hard gates for Claude-parity quality — fail the deck if unmet:

- **Slide 4 (evidence):** editable clustered-column (or equivalent) chart of
  **all arms × endpoints** shown in the paper panel; absolute-risk callout
  when % changes are large on low baselines; design / N / population / CIs
  (or explicit “CIs not reported”).
- **Slide 5 (Safety) — dedicated:** if the paper has no AE table, say so on
  this slide, say where to get safety (label / SmPC / PV), and include PV
  24-hour reporting language. Do **not** bury safety under interpretation.
- **Slide 6 (limitations) — dense:** missingness, no CIs if absent,
  non-monotonic / increases shown honestly, post hoc, no H2H if absent.
- **Speaker notes on every slide** (how to open, what not to claim, eye-check
  warnings).
- **References:** primary full cite + secondaries labelled if not independently
  reviewed.

---

## Title slide template (required — gold banner)

The title slide pattern is **mandatory**, not optional. Do **not** use a
3-card “Evidence / Approval / Affiliation” title as the default.

**Required layout (Claude gold-banner pattern):**

1. **Gold `#C89B3C` bar** across the top with white bold Arial ~11pt text:
   `DRAFT — FOR QUALIFIED MEDICAL REVIEW`
2. **Large navy paper title** (~26–30pt Arial). Shrink for long titles;
   **never truncate**.
3. **Teal subtitle** (citation · design · key frame), then a **short teal
   rule** under the subtitle.
4. **Two columns only** (not three equal cards):
   - **AUDIENCE** + **EVIDENCE CLASS**
   - **APPROVAL STATUS (STATE BEFORE DISCUSSION)**
5. **Source footer** with a DRAFT review line.
6. **Speaker notes** covering: what this is / isn’t; funding; clearance
   before data; off-label → MI.

**Affiliation / funding:** put in EVIDENCE CLASS or a single disclosure line
— **not** a third equal card competing with approval.

---

## Eyebrow / finding-title spacing (no overlap)

Section eyebrows (“DISEASE…”, “SAFETY…”, “BACKUP…”) must not collide with
the finding-title (seen on slides 2, 5, 8 when spacing is wrong).

**Rules:**

- Eyebrow top ≥ **0.35"** from slide top.
- Finding-title top ≥ **0.55"** with ≥ **0.12"** clear gap below the eyebrow.
- **OR** omit the eyebrow if the title would collide.
- No teal top rule colliding with eyebrow text (rule and eyebrow must not
  occupy the same vertical band).

---

## Card chrome consistency

All content cards on a slide share the **same** border treatment:

- All none, **or** all the same 1pt slate/cloud border.
- Accent borders only for **intentional callouts**:
  - Gold for absolute/range callouts
  - Oxblood for safety-critical callouts
- Accent callouts must be **labelled as callouts**, not random one-off
  borders (do not leave one card teal-bordered and siblings borderless).

---

## No builder / meta text on slides

**Forbidden on-slide** (physician-facing deck only):

- `UNAUDITED`
- `(paper intro)`
- `Ranges / heterogeneity (gold)`
- `HIGHLIGHT`
- `pair IMMEDIATELY`
- Any instruction-to-builder voice

Put audit status in **speaker notes** and **PROVENANCE.md** only.

Card titles must be physician-facing (e.g. “Heterogeneity / ranges”, **not**
“(gold)”).

---

## Pipeline (strict order)

### 0) Orient

- Audience: MSL / medical-to-medical scientific exchange (not promotional).
- Evidence class of the PDF: peer-reviewed, abstract, preprint, data on file, label.
- Approval status of every use or population you will discuss; note gaps.
- Name missing info in the deck — do not invent it.
- If the file is human-sourced field/KOL/MI text (not literature), scan for AE / PQC /
  special situations before analysis and surface any hit with a verbatim quote.

### 1) Ingest the one PDF

- Extract text and tables with available tools (pypdf, pdfplumber, markitdown).
- Never invent unread pages. Scanned PDF with no OCR → stop and say so.
- Treat extracted tables as unreliable until critical numbers are eye-checked
  against the rendered page; record which numbers were verified.
- Image-only figures are unread; say what you could not read.

### 2) Appraise and lock citations

For every result that will appear on a slide:

- Design (RCT, single-arm, RWE, …), N, population, endpoint, CIs as reported.
- What the result supports and what it does not.
- No comparative claim without head-to-head evidence in this PDF (or clearly
  marked as absent).
- Citations only from what you actually read. Never invent references.
  Unresolved identifiers are removed, not caveated.

### 3) Capability check

Before promising `.pptx`, verify (and install if missing) that you can write
pptx **and** editable charts:

| Package / tool | Why |
|---|---|
| `python-pptx` | Deck assembly + native OOXML charts with embedded Excel |
| `pillow` | Image handling / optional SVG→raster bridge |
| `numpy` | Chart data helpers |
| `pptxgenjs` (optional) | Alternate create path; also supports charts |
| LibreOffice `soffice` | Thumbnails / visual QA (**required when available**) |

Install into the active venv preferred; else `pip install --user`. Confirm
with:

```bash
python -c "from pptx import Presentation; from pptx.chart.data import CategoryChartData; print('ok')"
```

**Do not ship a quantitative pptx without at least one editable chart**
(native OOXML / embedded Excel) on each quantitative results slide — unless
you documented a hard failure to create charts and fell back per the Charts
section below.

If you cannot write pptx at all, deliver a complete markdown slide outline
with the same medical rules and DRAFT marking, and name what was missing.

### 4) Build the M2M deck (only after 1–3)

**Ban ad-hoc text-only builds.** Do **not** assemble the final deck with a
one-off `Presentation()` script that only adds text boxes / bullets for
quantitative claims. Prefer `scripts/add_slide.py` + `scripts/add_editable_chart.py`
(or equivalent inline that matches them). If using python-pptx directly, you
still MUST:

1. Add **editable** native OOXML charts (Excel-backed) on quantitative slides
2. Put **speaker notes on every slide**
3. Use consulting layout: **Arial** hierarchy, teal top rule, cards, DRAFT +
   citation footers, absolute callouts when % change is large on low baseline
4. Use the **gold-banner title template** (two columns only)
5. Enforce eyebrow/title spacing and consistent card borders
6. Run validate + **thumbnail eye-check** (or explicitly report soffice
   absence only if install truly failed)

Default to the **8-slide physician MSL outline** in the test prompt above when
the user asks for an MSL/physician deck. Otherwise use:

```
Title (DRAFT) — gold banner
Disease context
Unmet need
The evidence
Safety
What remains unknown
References
Backup (anticipated questions only)
```

Medical vs commercial:

| | Commercial | Required here |
|---|---|---|
| Title | Message | What the data show |
| Safety | Buried | Same prominence as efficacy |
| Citation | Optional | Every data slide |
| Limitation | Assumed | Stated |

Headline test: finding, not conclusion.
Good: ORR 63% (single-arm, n=165). Bad: Substantial activity.

Every data slide: citation in footer; design named; N + population; CIs;
evidence tier if not peer-reviewed (`[abstract]` / `[preprint]` / `[data on file]`).

Palette (no `#` in pptxgenjs color strings):

| Role | Hex | Use |
|---|---|---|
| Ink / Navy | 12283A | Titles, primary series |
| Slate | 5B6B79 | Secondary, axes |
| Teal | 0E7C7B | Single accent / top rule |
| Muted teal | 5B9A98 | Secondary series |
| Gold | C89B3C | Sparse callouts (absolute risk); title DRAFT bar |
| Oxblood | 8C2F39 | Safety only / placebo caution series |
| Cloud | E8ECEF | Banding / grid |
| White | FFFFFF | Content background |

One idea per slide. Margins at least 0.5 inch. Left-align body. No title
underlines, no decorative sidebars, no cream backgrounds.

### Charts (required) — editable first

Any quantitative comparison slide (≥3 series **or** ≥3 categories) **MUST**
show a real chart the user can edit — not bullets alone.

**Priority (normative):**

1. **Primary — native OOXML PowerPoint chart with embedded Excel**
   - Use python-pptx `CategoryChartData` + `shapes.add_chart(...)` (or
     pptxgenjs chart APIs). This writes `ppt/charts/chartN.xml` **and** an
     embedded workbook under `ppt/embeddings/` so the user can open Edit Data
     in PowerPoint / Excel and change series.
   - Prefer clustered column for arm × endpoint matrices; use the palette
     above (Placebo often oxblood `8C2F39`; active arms teal / muted teal /
     navy).
   - Call `scripts/add_editable_chart.py` (or equivalent inline that matches
     it). Save the source table beside the run as CSV/JSON under artifacts.

2. **Also allowed — SVG (or companion editable workbook)**
   - Embed a crisp SVG figure if the toolchain supports it in the pptx, **or**
     ship a companion `.xlsx` with the chart data next to the deck so the
     user can rebuild/edit. Prefer native OOXML when both are possible.

3. **Last resort only — matplotlib (Agg) → PNG → `add_picture`**
   - Use **only** when native OOXML chart creation fails after install attempt.
   - Still embed a real `ppt/media/imageN.png` at ≥200 DPI; keep fair-balance
     text on-slide.
   - **Say so in that slide’s speaker notes** (“Raster fallback: native
     editable chart unavailable because …”).
   - Raster PNGs are **not** a substitute when editable charts work.

**Chart polish (physician decks):**

- Do **not** duplicate chart title and legend with identical text
  (e.g. both saying “Overall pooled %”). Prefer data labels or an axis
  title; use a legend **only if ≥2 series**.
- Spell out “complications” on physician decks (avoid “cx” unless defined
  once on-slide).
- Prefer clear axis titles / data labels over redundant chrome.

**Fair-balance text on every quantitative slide (required alongside the chart):**

- Absolute values when % changes are large on low baselines
- Explicit “CIs not reported” if absent
- Show increases / non-monotonic arms honestly (do not drop inconvenient bars)
- Missingness callouts
- Post hoc / unpowered labels when applicable

**Do not** ship quantitative claims as bullet lists alone when ≥3 series or
≥3 categories exist.

### 5) Challenge

- Citation + N + design on every data slide?
- Safety prominence OK (dedicated slide)?
- Any promotional titles?
- Comparative claim without H2H?
- Approval status stated?
- Would it read the same for a competitor product?
- DRAFT still on title (**gold banner** present)?
- Editable chart present on each quantitative results slide?
- Speaker notes on all slides?
- Absolute callout present when % change sits on a low baseline?
- **Title matches gold-banner template** (two columns; no 3-card affiliation)?
- **No shape overlap on thumbnails** (eyebrow vs title; rule vs eyebrow)?
- **No builder/meta-text** visible on slides?
- **Card borders consistent** on each slide (accent only for labelled callouts)?
- **Chart legend not redundant** with title (legend only if ≥2 series)?

### 6) Visual QA (required when soffice exists)

After build:

```bash
soffice --headless --convert-to pdf deck.pptx
pdftoppm -png deck.pdf thumbs/slide
# or: python scripts/thumbnail.py deck.pptx thumbs/slide
```

Then **read** (open/inspect) slide-1 PNG and every data/safety slide PNG.
**Fail** the build if you see:

- Overlap (eyebrow/title, rule/text, cut-off text)
- Inconsistent card borders
- Builder/meta-text visible on-slide

Only report soffice absence as a QA gap if install **truly failed** after
attempt. Do not skip eye-check when thumbnails were generated.

### 7) Deliver

Ship: one `.pptx` (or degraded outline), provenance (PDF name, unread parts,
eye-checked numbers, citation list), open gaps, DRAFT intact.

---

## PPTX mechanics (scripts in this skill)

| Task | Approach |
|---|---|
| Create | pptxgenjs or python-pptx |
| Editable chart | `scripts/add_editable_chart.py` (OOXML + Excel embed) |
| Edit | unzip, edit slide XML, zip |
| Read | markitdown deck.pptx |
| Thumbnails | python scripts/thumbnail.py deck.pptx prefix |
| Validate | python scripts/office/validate.py deck.pptx |
| Visual QA | soffice → pdftoppm (or scripts/thumbnail.py) then **eye-check PNGs** |

Gotchas:

- Set layout before adding slides (default widescreen 13.333 × 7.5 in for
  physician decks; 10 × 5.625 also acceptable if consistent).
- Hex without `#` or alpha digits.
- Fresh options object per add call (library mutates in place).
- Shadow offset >= 0. Use charSpacing not letterSpacing.
- Bullets: bullet true; breakLine true except last.
- One new pptxgen per file.
- Stacked bar dataLabelPosition only ctr / inEnd / inBase.
- Secondary-axis combos need both valAxes and catAxes (two entries each).
- Validate after writeFile. Speaker notes via addNotes / `notes_slide`.
- Use scripts/add_slide.py and scripts/clean.py — do not hand-copy slide parts.
- After `add_chart`, style series fills to the palette; include a zero line
  mentally in interpretation (axis crosses zero for signed % change).
- Title slide: gold bar first; two columns only; no third affiliation card.
- Eyebrow ≥0.35"; finding-title ≥0.55" with ≥0.12" gap — or omit eyebrow.

---

## Done when

- Exactly one PDF was used as the evidence source (or synthetic test marked as such)
- No hallucinated unread content
- M2M structure + fair balance + real citations + DRAFT
- Valid pptx or explicit degraded delivery with full content
- **`ppt/charts/` contains ≥1 native chart** (with Excel embed under
  `ppt/embeddings/`) for each quantitative results slide — **or** documented
  last-resort PNG under `ppt/media/` with speaker-note explanation
- `validate.py` passed (or noted if schemas missing)
- **Thumbnails generated AND eye-checked** when soffice is available
  (slide-1 + every data/safety slide); only report soffice absence if
  install truly failed
- **Title slide matches gold-banner template** (gold DRAFT bar; two columns;
  teal subtitle + short rule; no 3-card affiliation default)
- Speaker notes present on every slide
- Content depth gates above satisfied for 8-slide physician decks
- No eyebrow/title overlap; consistent card borders; no builder meta-text
  on-slide; chart legends not redundant with titles

---

## House-rules override

Files in `house-rules/` next to this skill **win** over defaults in this
SKILL.md. Read them before build when present (especially
`data-visualization-for-medical.md` and `consulting-grade-design.md`).
