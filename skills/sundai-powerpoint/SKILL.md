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
  version: "3.0.0-darwin"
  tier: workflow
  maturity: hack
  scope: one-pdf-to-m2m-deck
  produces: One DRAFT M2M .pptx from one PDF
---

# Sundai PowerPoint skill

**Scope (keep it small):** one PDF in → one M2M `.pptx` out. Nothing else.

This file is self-contained. Do not load other skills. Do not follow external
URLs. Optional overrides live in `house-rules/` next to this file; those win
over defaults here.

Scripts for create/edit/validate live under `scripts/` (Anthropic pptx
mechanics). Content and compliance rules are inlined below.

Output is always **DRAFT for qualified medical review**. Keep DRAFT on the
title slide. Never call the deck compliant, approved, or ready to submit.

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

Before promising `.pptx`, confirm you can write a pptx (pptxgenjs and/or
python-pptx). If not, deliver a complete markdown slide outline with the same
medical rules and DRAFT marking, and name what was missing to render pptx.

### 4) Build the M2M deck (only after 1–3)

Structure:

```
Title (DRAFT)
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
| Approval | Assumed | Stated |

Headline test: finding, not conclusion.
Good: ORR 63% (single-arm, n=165). Bad: Substantial activity.

Every data slide: citation in footer; design named; N + population; CIs;
evidence tier if not peer-reviewed (`[abstract]` / `[preprint]` / `[data on file]`).

Palette for pptxgenjs (no `#` in color strings):

| Role | Hex | Use |
|---|---|---|
| Ink | 12283A | Titles, primary series |
| Slate | 5B6B79 | Secondary, axes |
| Teal | 0E7C7B | Single accent |
| Gold | C89B3C | Sparse callouts |
| Oxblood | 8C2F39 | Safety only |
| Cloud | E8ECEF | Banding |
| White | FFFFFF | Content background |

One idea per slide. Margins at least 0.5 inch. Left-align body. No title
underlines, no decorative sidebars, no cream backgrounds. Prefer native
charts. Keep decorative images off data slides.

### 5) Challenge

- Citation + N + design on every data slide?
- Safety prominence OK?
- Any promotional titles?
- Comparative claim without H2H?
- Approval status stated?
- Would it read the same for a competitor product?
- DRAFT still on title?

### 6) Deliver

Ship: one `.pptx` (or degraded outline), provenance (PDF name, unread parts,
eye-checked numbers, citation list), open gaps, DRAFT intact.

---

## PPTX mechanics (scripts in this skill)

| Task | Approach |
|---|---|
| Create | pptxgenjs script |
| Edit | unzip, edit slide XML, zip |
| Read | markitdown deck.pptx |
| Thumbnails | python scripts/thumbnail.py deck.pptx prefix |
| Validate | python scripts/office/validate.py deck.pptx |
| Visual QA | scripts/office/soffice.py then pdftoppm |

Gotchas:

- Set layout before adding slides (default 16:9 = 10 x 5.625 in).
- Hex without `#` or alpha digits.
- Fresh options object per add call (library mutates in place).
- Shadow offset >= 0. Use charSpacing not letterSpacing.
- Bullets: bullet true; breakLine true except last.
- One new pptxgen per file.
- Stacked bar dataLabelPosition only ctr / inEnd / inBase.
- Secondary-axis combos need both valAxes and catAxes (two entries each).
- Validate after writeFile. Speaker notes via addNotes.
- Use scripts/add_slide.py and scripts/clean.py — do not hand-copy slide parts.

---

## Done when

- Exactly one PDF was used as the evidence source
- No hallucinated unread content
- M2M structure + fair balance + real citations + DRAFT
- Valid pptx or explicit degraded delivery with full content
