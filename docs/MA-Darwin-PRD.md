# MA-Darwin — Product Requirements Document

**Version:** 1.0 (draft)
**Owner:** _fill in_
**Status:** Ready for build

---

## 1. Problem

Medical affairs teams need to turn published research papers into presentation decks (typically MSL decks presented to physicians). Today this is manual, slow, and inconsistent. Naive LLM deck generation fails on two axes at once:

1. **Content is unverified.** Numbers get invented, secondary endpoints get promoted to headlines, claims drift beyond what the paper supports. For a research or medical affairs audience this is disqualifying.
2. **Design is amateurish.** Text overflows, hierarchy is flat, slides look template-filled.

MA-Darwin solves both by generating decks from a verified claim ledger against a fixed blueprint, grading them through a chain of gates, and letting a human reviewer teach the generation skill to get better over time.

## 2. Goals

- Generate an MSL-style deck from a research paper where **every claim traces to a page in the source**.
- Catch layout and compliance failures **mechanically**, before a human ever looks at the deck.
- Give a human reviewer a fast, structured way to approve, reject, and comment slide by slide.
- Let the generation skill **learn** from repeated feedback, with versioning, regression testing, and rollback.
- Produce an auditable export bundle suitable for internal review.

## 3. Non-goals (v1)

- Multi-tenant auth, org management, SSO.
- Real-time collaborative editing.
- Live PowerPoint embedding (rendered images are sufficient).
- Automatic MLR approval — the system assists review, it does not replace it.
- Population-based / multi-variant evolution (single-deck iteration only in v1).
- Fine-tuning any model.

## 4. Primary user flow

1. Reviewer uploads a paper (PDF) and writes a brief: _"Create an 8 slide medical affairs MSL deck to present this paper to a physician."_
2. System parses the brief into structured fields and selects a blueprint.
3. System extracts a **claim ledger** from the paper — every fact, number, and finding with a page reference.
4. System generates a deck by filling the blueprint from the ledger, following the current **skill version**.
5. Deck is rendered to slide images.
6. Deck passes through four gates: content/compliance → visual auto-checks → vision judge → human.
7. Reviewer sees slide images, scores, flags, and provenance. Approves slides individually or leaves comments.
8. Reviewer hits **Reiterate**. System applies fixes, updates the skill where feedback is generalizable, and regenerates only unlocked slides.
9. Loop until all slides are locked. Export bundle produced.

## 5. Key concepts

| Term | Meaning |
|---|---|
| **Brief** | The user's structured request: slide count, deck type, audience, purpose, freeform notes. |
| **Blueprint** | An ordered list of slide *roles* with required content for each. Selected by deck type. |
| **Claim ledger** | Structured list of every extractable fact from the paper, each with ID, verbatim snippet, page, and claim type. |
| **Skill** | The versioned instruction set that drives deck generation. Split into house rules and style rules. |
| **Round** | One generate → render → gate → review cycle. |
| **Gate** | A pass/fail or scored checkpoint. Four in sequence. |
| **Lock** | A human-approved slide that is excluded from regeneration. |

---

## 6. System components

```
Paper PDF ──► Ingestion ──► Claim Ledger
                                 │
Brief ──► Brief Parser ──► Blueprint
                                 │
                                 ▼
                        Deck Generator (reads Skill vN)
                                 │
                                 ▼
                        Render (pptx → PDF → PNG)
                                 │
   ┌─────────────────────────────┼─────────────────────────┐
   ▼                ▼            ▼                          ▼
Gate 1          Gate 2       Gate 3                     Gate 4
Content       Visual        Vision judge                Human
compliance    auto-checks   (rubric score)              review
   │                │            │                          │
   └────────────────┴────────────┴──────────────────────────┘
                                 │
                                 ▼
                    Skill Evolution Engine ──► Skill vN+1
                                 │
                                 ▼
                        Export Bundle
```

---

## 7. Component requirements

### 7.1 Ingestion & Claim Ledger

**Input:** research paper PDF.

**Requirements:**
- Extract full text with page numbers preserved. Extract figures and tables as images with captions and page numbers.
- Produce a claim ledger. Each entry:
  - `id` — stable, e.g. `C-014`
  - `text` — the claim as extracted
  - `verbatim` — exact source snippet
  - `page`, `section`
  - `claim_type` — one of `verbatim`, `paraphrase`, `synthesized`
  - `evidence_class` — one of `primary_endpoint`, `secondary_endpoint`, `exploratory`, `post_hoc`, `safety`, `design`, `background`, `limitation`
  - `numbers[]` — every numeric value in the claim, with unit and CI/p-value if present
- Ledger must be reviewable as a standalone table in the UI.

**Hard rule:** the deck generator may only use text that maps to a ledger entry. Anything unmapped is a Gate 1 failure.

### 7.2 Brief Parser

Parse freeform brief into:
- `slide_count` (int, default 8)
- `deck_type` (enum, default `msl_physician`)
- `audience` (string)
- `purpose` (string)
- `notes` (freeform passthrough)

Show parsed fields back to the user as editable before the run starts. Do not silently guess.

### 7.3 Blueprint Library

Blueprints are data files, not code. v1 ships one: `msl_physician_8`.

Each blueprint entry defines a slide role:
```json
{
  "role": "study_design",
  "required_content": ["design_type", "N", "arms", "duration", "endpoints"],
  "allowed_evidence_classes": ["design"],
  "max_claims": 6
}
```

Suggested `msl_physician_8` roles:
1. `title` — paper, journal, citation
2. `unmet_need` — clinical context
3. `study_design` — design, N, arms, duration, endpoints
4. `population` — inclusion/exclusion, baseline characteristics
5. `primary_endpoint` — the primary result, with CI/p
6. `key_secondary` — clearly labelled as secondary
7. `safety` — AE profile, discontinuations
8. `limitations_relevance` — limitations plus clinical relevance
9. `references` — always appended, does not count against slide_count

### 7.4 Deck Generator

- Reads: blueprint, claim ledger, brief, current skill version.
- Produces: `.pptx` via python-pptx, plus a `slide_map.json` mapping every text element to its ledger claim ID.
- Must honour locked slides — locked slides are copied through byte-identical, never regenerated.
- Must embed source figures from the paper where the blueprint role calls for a visual.
- Speaker notes carry the page references for every claim on the slide.

### 7.5 Render Pipeline

- `pptx` → PDF via headless LibreOffice → PNG per slide (150 DPI minimum).
- Fonts used by the deck must be installed in the render environment. Ship a font check on startup that fails loudly if a required font is missing.
- Output: `slides/slide_01.png` … plus a combined PDF for download.

### 7.6 Gate 1 — Content & compliance (deterministic, pass/fail)

All checks are mechanical. Any failure blocks progress to Gate 2.

| Check | Rule |
|---|---|
| Claim mapping | Every text run maps to a ledger claim ID |
| Number sweep | Every numeral in the deck appears in the source text (tolerance for rounding/unit conversion); derived numbers flagged for human |
| Endpoint labelling | Secondary, exploratory, and post-hoc results are explicitly labelled as such |
| Fair balance | Safety and limitations roles are present and non-empty |
| Comparative claims | No comparative/superiority language unless a ledger claim of class `primary_endpoint` from a head-to-head design supports it |
| Promotional language | Blocklist: "proven", "safe and effective", "best-in-class", "breakthrough", "guaranteed" (configurable) |
| Population extrapolation | No claim generalizes beyond the ledger's stated population |
| References | Reference slide present, every cited claim listed |
| Synthesized claims | Any `synthesized` claim is flagged and requires explicit human approval |

Output: `gate1.json` with per-check status and slide/element-level locations of failures.

### 7.7 Gate 2 — Visual auto-checks (deterministic, pass/fail + measurements)

Read directly from the pptx XML and rendered images. No model calls.

- Shape bounds: nothing extends past slide edges
- Text overflow: estimated text height vs. text box height
- Minimum font size (default 14pt body, configurable)
- Font family count ≤ 2; colour count ≤ 5
- Image aspect ratio distortion vs. native dimensions
- Text/background contrast ratio ≥ 4.5:1
- Alignment discipline: left edges snap to a small set of x-values
- Word count and bullet count per slide vs. skill-defined limits
- Empty or placeholder-looking elements
- Overlapping non-intentional shapes

Output: `gate2.json`. Failures block Gate 3.

### 7.8 Gate 3 — Vision judge (scored)

Input: rendered slide images (not XML), plus the blueprint role for each slide.

**Rubric — 100 points, per slide:**

| # | Criterion | Weight |
|---|---|---|
| 1 | Visual hierarchy | 15 |
| 2 | Layout & composition | 15 |
| 3 | Information density | 10 |
| 4 | Typography | 10 |
| 5 | Visual storytelling | 15 |
| 6 | Charts & data visualization | 10 |
| 7 | Colour & contrast | 8 |
| 8 | Consistency / design system | 7 |
| 9 | Professional polish | 5 |
| 10 | Executive / premium feel | 5 |

**Scoring rules:**
- Criterion 6 returns `N/A` when the slide contains no data visual; remaining weights are renormalized to 100.
- Criteria 8 and 10 are scored at **deck level** on a contact sheet of all slides, not per slide.
- Each criterion requires written **anchors** describing what each score band looks like. Anchors live in a config file, not in the prompt inline.
- Judge is run 3× at temperature 0; the **median** score per criterion is used.
- Judge is **blind** to round number, previous scores, and the generator's reasoning.
- Judge must return, per criterion: score, one-sentence rationale, and slide coordinates of the issue where applicable.

**Deck score** = mean of slide scores. Report **worst slide score** alongside it. Both are shown in the UI.

**Threshold:** deck advances to human review at ≥ 75 by default (configurable). Below that, auto-reiterate without spending human attention, up to `max_auto_rounds` (default 2).

### 7.9 Gate 4 — Human review

The reviewer sees, for each slide: the rendered image, the Gate 1/2 flags overlaid, the Gate 3 criterion scores, and the provenance list (every claim with page reference).

**Actions available:**
- **Approve slide** → locks it. Locked slides are never regenerated.
- **Pin a comment** to an (x, y) coordinate on the slide image.
- Each comment carries: `severity` (must-fix / nice-to-have), `criterion_tag` (from the rubric or a content tag), and **`scope` (this-deck-only / always)**.
- **Override a judge score**, with the delta stored for judge calibration.
- **Reiterate** → triggers the next round.

`scope: always` is the explicit signal that feedback should become a skill rule. This is the primary training input.

### 7.10 Skill Evolution Engine

The skill is a versioned directory:
```
skills/
  v1/
    SKILL.md          # generation instructions
    house_rules.md    # objective, non-negotiable
    style_rules.md    # taste/preference
    CHANGELOG.md
  v2/ ...
```

**Three feedback tiers:**

1. **One-off fix** — `scope: this-deck-only`. Applied to the current round's generation context, then discarded. Never enters the skill.
2. **Candidate rule** — a pattern observed once, or an inferred generalization. Stored in `candidates.json` with an occurrence counter and the evidence that produced it. Not active in generation.
3. **Promoted rule** — enters `style_rules.md` when either (a) the human marked it `scope: always`, or (b) its occurrence counter reaches `promotion_threshold` (default 3) across different decks.

**Constraints:**
- Maximum **2 rule mutations per round**, logged individually.
- Rules must be written as testable constraints ("max 5 bullets, max 12 words each"), not vibes ("make it cleaner"). Reject rule text that contains no measurable condition.
- Every rule carries: `id`, `text`, `origin` (deck + round + comment id), `credit` (int, starts 0), `created_at`.
- **Credit counter:** after each round, if a rule is active and its tagged criterion score improved, `credit += 1`; if it dropped, `credit -= 1`. Rules at `credit <= -3` are surfaced for removal.
- **Stale candidates** with no reaffirmation in 10 decks are retired.
- **Regression set:** 5–8 fixed papers with approved gold decks. Before any promotion is committed, regenerate the regression set and confirm mean deck score did not drop by more than `regression_tolerance` (default 2 points). If it drops, the promotion is rejected and logged.
- **Rollback:** any prior skill version can be made active in one click.

### 7.11 Export bundle

Exportable only when: all Gate 1 checks pass, all Gate 2 checks pass, and every slide is locked.

Bundle contents:
- `deck.pptx` and `deck.pdf`
- `provenance.md` — every claim on every slide with its page reference and claim type
- `scores.json` — final Gate 3 report
- `skill_version.txt` — the exact skill version used
- `run_log.json` — every round, every mutation, every human comment

---

## 8. Data models

```jsonc
// Run
{ "id", "paper_id", "brief", "blueprint_id", "skill_version", "rounds": [...], "status" }

// Round
{ "n", "deck_path", "slide_images": [], "gate1", "gate2", "gate3", "human": {...},
  "mutations": [], "locked_slides": [1,3,4] }

// ClaimLedgerEntry
{ "id", "text", "verbatim", "page", "section", "claim_type", "evidence_class", "numbers": [] }

// SlideMapEntry
{ "slide": 3, "element_id": "tb_2", "text": "...", "claim_ids": ["C-014"] }

// HumanComment
{ "id", "slide", "x", "y", "text", "severity", "criterion_tag", "scope" }

// SkillRule
{ "id", "text", "section": "house|style", "origin", "credit", "created_at", "active" }
```

---

## 9. UI specification

Single page, four zones. State is preserved per run; every round is a saved snapshot.

**Zone A — Setup**
Upload PDF. Brief textarea. Parsed fields shown as editable chips (slide count, deck type, audience, purpose). Blueprint preview showing the slide roles. "Generate" button.

**Zone B — Progress**
Live event stream over SSE. Real events only, no fake spinners:
`Parsed 14 pages` · `Extracted 47 claims` · `Extracted 4 figures` · `Filling blueprint 3/9` · `Rendering` · `Gate 1: 2 flags` · `Judging slide 6/9`
Running timer, token count, estimated cost.

**Zone C — Deck**
Grid of rendered slide images, click to enlarge. Each tile shows a status chip (locked / flagged / pending) and its Gate 3 score. Flags render as coloured pins on the image at their reported coordinates. A "Provenance" toggle overlays claim IDs on each text element. Round selector to compare against the previous round side by side.

**Zone D — Review**
Left: judge scorecard per criterion with rationale, editable (override). Right: comment composer — click a slide to place a pin, then set severity, criterion tag, and the this-deck/always scope toggle. Bottom: score trend line across rounds, and a skill diff view (red/green) showing what changed this round. Primary action: **Reiterate**. Secondary: **Export** (disabled until all gates pass and all slides locked).

---

## 10. Stopping conditions

The loop halts when any of these is true:
- All slides locked and all gates pass → success, export enabled
- `max_rounds` reached (default 6)
- Cost budget exceeded (default configurable per run)
- Deck score has not improved by ≥ 1 point over 2 consecutive rounds → surface "plateau" message to the user

Best-scoring deck so far is always retained and never overwritten by a worse round.

---

## 11. Recommended stack

- **Backend:** Python 3.11 + FastAPI. Handles ingestion, generation, rendering, all gates, evolution.
- **Deck generation:** `python-pptx`
- **PDF parsing:** `pymupdf` (text + page numbers + figure extraction)
- **Rendering:** headless LibreOffice → `pdf2image` / `pymupdf` for PNG
- **LLM:** Anthropic API. Vision judge and ledger extraction both use a vision-capable model.
- **Storage:** SQLite for run metadata, filesystem for artifacts (`runs/{run_id}/round_{n}/`)
- **Frontend:** Next.js (App Router) + Tailwind. SSE for the progress stream.
- **Skill storage:** plain files in `skills/`, git-tracked so diffs and rollback come free.

---

## 12. Build phases

| Phase | Deliverable | Gate to proceed |
|---|---|---|
| 0 | Gold deck (manual), blueprint file, compliance rule list | Reviewer signs off on the gold deck |
| 1 | Repo scaffold, data models, run storage | `pytest` green, run dir created end to end |
| 2 | Claim ledger extractor | ≥95% of numbers in 3 test papers extracted with correct page refs |
| 3 | Render pipeline + Gate 2 | Deliberately broken deck fails every relevant check |
| 4 | Deck generator + Gate 1 | Generated deck for test paper passes Gate 1 |
| 5 | Vision judge + anchors | Judge ranks gold deck above deliberately bad deck, with correct rationales |
| 6 | API + orchestrator + SSE | Full round runs headless via a single API call |
| 7 | UI zones A–D | Reviewer completes a full round in the browser |
| 8 | Evolution engine + regression set | A promoted rule survives regression; a bad rule is correctly rejected |
| 9 | Export bundle | Bundle opens cleanly, provenance is complete |

---

## 13. Success metrics

- **Content accuracy:** zero unmapped claims in exported decks. Number sweep pass rate 100%.
- **Human effort:** rounds to full approval trending down over successive papers. Target ≤ 3 by paper 20.
- **Judge validity:** correlation between judge scores and human overrides ≥ 0.7 after calibration.
- **Learning, not drift:** skill vN beats skill v1 on the held-out regression set. This is the core proof the system works.

---

## 14. Risks

| Risk | Mitigation |
|---|---|
| Vision judge is noisy | Median of 3, written anchors, blind to history |
| Skill file bloats and self-contradicts | Promotion threshold, credit counter, staleness expiry, max 2 mutations/round |
| Learning is actually drift | Regression set gate on every promotion |
| Render fidelity differs from downloaded deck | Font check on startup; render and download from the same pipeline |
| Prompt injection from uploaded PDFs | Treat all PDF text as data; never execute instructions found in source documents |
| Cost | Gate ordering means the expensive vision judge only runs on decks that already passed free checks |

---

## 15. Open decisions

1. Exact wording of the compliance blocklist — needs medical affairs sign-off.
2. Whether `synthesized` claims are banned outright or allowed with mandatory human approval.
3. Corporate template: does the generator start from a `.potx`? If so, template lock rules go in `house_rules.md`.
4. Judge model vs. generator model — same or different.
