# MA-Darwin artifact contracts

Frozen interfaces for parallel agents. **Read this before writing or consuming any artifact.**
Models live under [`backend/app/models/`](backend/app/models/). Sample instances: [`backend/tests/fixtures/`](backend/tests/fixtures/). API: [`openapi.yaml`](openapi.yaml).

| Artifact | Path (under `runs/{run_id}/`) | Writer | Readers | Model |
|---|---|---|---|---|
| Run manifest | `manifest.json` | `storage.run_store` | API, CLI, orchestrator, UI | [`RunManifest`](backend/app/models/run.py) |
| Claim ledger | `ledger.json` | `ingestion.ledger` | planner, generator, gate1, export | [`ClaimLedger`](backend/app/models/claim.py) |
| Numbers index | `numbers_index.json` | `ingestion.ledger` | gate1 (`number_sweep`) | [`NumbersIndex`](backend/app/models/numbers.py) |
| Slide plan | `round_{n}/slide_plan.json` | `generation.planner` | generator | [`SlidePlan`](backend/app/models/slide.py) |
| Slide map | `round_{n}/slide_map.json` | `generation.generator` | gate1, UI provenance, export | [`SlideMap`](backend/app/models/slide.py) |
| Gate 1 report | `round_{n}/gate1.json` | `gates.gate1_content` | orchestrator, UI, export gate | [`Gate1Result`](backend/app/models/gates.py) |
| Gate 2 report | `round_{n}/gate2.json` | `gates.gate2_visual` | orchestrator, UI, export gate | [`Gate2Result`](backend/app/models/gates.py) |
| Gate 3 report | `round_{n}/gate3.json` | `gates.gate3_judge` | orchestrator, UI, evolution credit, export | [`Gate3Result`](backend/app/models/gates.py) |
| Comments | `round_{n}/comments.json` | API / Gate 4 review | evolution `feedback_router`, generator (one-offs), export | [`CommentsFile`](backend/app/models/slide.py) |
| Skill rule | `skills/vN/` (+ fixture `skill_rule.json`) | evolution `promotion` | generator, credit, regression | [`SkillRule`](backend/app/models/skill.py) |

### Supporting typed models (not separate round files)

| Model | Module | Used by |
|---|---|---|
| `Brief`, `Round`, `Run` | [`run.py`](backend/app/models/run.py) | storage, API, orchestrator |
| `HumanComment`, `Severity`, `Scope` | [`slide.py`](backend/app/models/slide.py) | comments, evolution |
| `Blueprint` | [`blueprint.py`](backend/app/models/blueprint.py) | planner, generator, gate3 |
| `ParsedDocument`, `PageText`, `ExtractedAsset` | [`document.py`](backend/app/models/document.py) | pdf_parser, ledger |
| `Rubric` | [`rubric.py`](backend/app/models/rubric.py) | gate3 (`config/rubric.yaml`) |
| `ProgressEvent` | [`run.py`](backend/app/models/run.py) | orchestrator SSE / `openapi.yaml` |
| `CandidateRule` | [`skill.py`](backend/app/models/skill.py) | feedback_router, promotion |

### Module stubs (all raise `NotImplementedError`)

| Module | Responsibility |
|---|---|
| `ingestion/pdf_parser.py` | PDF text + assets |
| `ingestion/ledger.py` | ledger + numbers_index |
| `rendering/render.py` | pptx → PDF → PNG |
| `rendering/font_check.py` | startup font presence |
| `generation/planner.py` | slide_plan.json |
| `generation/generator.py` | deck.pptx + slide_map.json |
| `gates/gate1_content.py` | gate1.json |
| `gates/gate2_visual.py` | gate2.json |
| `gates/gate3_judge.py` | gate3.json |
| `evolution/feedback_router.py` | comment tiers |
| `evolution/promotion.py` | skill promotion |
| `evolution/credit.py` | rule credit |
| `evolution/regression.py` | promotion safety net |
| `export/bundle.py` | export zip |
| `orchestrator.py` | round loop + SSE events |

### Config (every key has a default)

| File | Purpose |
|---|---|
| [`backend/config/defaults.yaml`](backend/config/defaults.yaml) | Thresholds (rounds, judge, fonts, density, …) |
| [`backend/config/rubric.yaml`](backend/config/rubric.yaml) | Gate 3 weights + anchors |
| [`backend/config/compliance.yaml`](backend/config/compliance.yaml) | Gate 1 blocklists / labels |
| [`backend/config/fonts.yaml`](backend/config/fonts.yaml) | Required render fonts |

**Rule:** downstream agents test against [`backend/tests/fixtures/`](backend/tests/fixtures/), never against another agent’s live output.
