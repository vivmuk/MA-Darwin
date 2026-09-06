# House rules — `consulting-grade-design`

Rules here override the defaults in `skills/consulting-grade-design/SKILL.md`.
See [README.md](README.md) for how to write a good one.

## Seeded examples

- Replace the library palette with the corporate brand system at `[path]` —
  brand colours win over the defaults, but the one-accent rule and the
  reserved safety colour still apply within your palette.
- All external-facing decks use the corporate template; the library look is
  for internal and draft material only.
- Photography of patients or healthcare professionals requires a licensed
  image with a documented release — generated imagery of identifiable people
  is not used at all.

## YOUR RULES — ADD BELOW THIS LINE

- Speaker notes required on every slide.
- Typography: Arial hierarchy (title > section eyebrow > body > footer).
- Layout: teal top rule (`0E7C7B`), card structure, DRAFT + citation footers on data slides.
- Absolute-risk callouts (gold border) when percent change is large on a low baseline.
- Prefer editable OOXML charts (Excel-backed) on quantitative slides; do not ship text-only efficacy panels.

### Title slide (gold-banner template — required)

- Gold `#C89B3C` bar: `DRAFT — FOR QUALIFIED MEDICAL REVIEW` (white bold Arial ~11pt).
- Large navy paper title (~26–30pt; shrink for long titles, never truncate).
- Teal subtitle (citation · design · key frame) + short teal rule under subtitle.
- Two columns only: AUDIENCE + EVIDENCE CLASS | APPROVAL STATUS (STATE BEFORE DISCUSSION).
- Source footer with DRAFT review line.
- Speaker notes: what this is/isn’t, funding, clearance before data, off-label→MI.
- Do **not** use a 3-card “Evidence/Approval/Affiliation” title as default; affiliation/funding goes in EVIDENCE CLASS or a single disclosure line.

### Eyebrow / finding-title spacing

- Eyebrow top ≥ 0.35"; finding-title top ≥ 0.55" with ≥ 0.12" clear gap below eyebrow; OR omit eyebrow if title would collide.
- No teal top rule colliding with eyebrow text.

### Card chrome consistency

- All content cards on a slide share the same border treatment (all none, or all same 1pt slate/cloud).
- Accent borders only for intentional labelled callouts (gold = absolute/range; oxblood = safety-critical).

### No builder / meta-text on slides

- Forbidden on-slide: `UNAUDITED`, `(paper intro)`, `(gold)`, `HIGHLIGHT`, `pair IMMEDIATELY`, instruction-to-builder voice.
- Audit status belongs in speaker notes + PROVENANCE.md only.
- Card titles must be physician-facing.

### Thumbnail visual QA

- When soffice exists: convert to PDF → pdftoppm PNG (or scripts/thumbnail.py); **read** slide-1 and every data/safety PNG; fail on overlap, cut-off text, inconsistent borders, or meta-text.
- Only report soffice absence as gap if install truly failed.
