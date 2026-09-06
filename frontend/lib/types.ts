/** OpenAPI-aligned types (openapi.yaml). */

export type RunStatus =
  | "created"
  | "running"
  | "awaiting_review"
  | "complete"
  | "failed"
  | "plateau";

export type DeckType = "msl_physician";

export type Severity = "must-fix" | "nice-to-have";
export type Scope = "this-deck-only" | "always";

export interface Brief {
  slide_count: number;
  deck_type: DeckType;
  audience: string;
  purpose: string;
  notes: string;
}

export interface CheckLocation {
  slide: number;
  element_id?: string | null;
  x?: number | null;
  y?: number | null;
  w?: number | null;
  h?: number | null;
  detail?: string;
}

export interface GateCheckResult {
  name: string;
  passed: boolean;
  message?: string;
  flagged?: boolean;
  locations?: CheckLocation[];
}

export interface Gate1Result {
  gate: "gate1";
  passed: boolean;
  checks: GateCheckResult[];
}

export interface Gate2Result {
  gate: "gate2";
  passed: boolean;
  checks: GateCheckResult[];
}

export interface JudgeCriterionScore {
  criterion: string;
  weight: number;
  score: number | null;
  rationale?: string;
  coordinates?: { x: number; y: number; w?: number | null; h?: number | null } | null;
  scope?: "slide" | "deck";
  slide?: number | null;
}

export interface SlideScoreSummary {
  slide: number;
  score: number;
}

export interface Gate3Result {
  gate: "gate3";
  deck_score: number;
  worst_slide_score: number;
  slide_scores: SlideScoreSummary[];
  slide_results?: { slide: number; role: string; score: number; criteria: JudgeCriterionScore[] }[];
  deck_criteria?: JudgeCriterionScore[];
  criteria: JudgeCriterionScore[];
  passed: boolean;
}

export interface HumanComment {
  id: string;
  slide: number;
  x: number;
  y: number;
  text: string;
  severity: Severity;
  criterion_tag: string;
  scope: Scope;
}

export interface ScoreOverride {
  criterion: string;
  slide?: number | null;
  original_score: number;
  override_score: number;
  delta: number;
  rationale?: string;
}

export interface HumanReviewState {
  approved_slides: number[];
  score_overrides: ScoreOverride[];
  synthesized_approvals: string[];
}

export interface MutationRecord {
  id: string;
  kind: "one_off" | "candidate" | "promotion" | "rollback" | "rejection";
  text: string;
  origin_comment_id?: string | null;
  rule_id?: string | null;
  timestamp?: string;
}

export interface SlideMapEntry {
  slide: number;
  element_id: string;
  text: string;
  claim_ids: string[];
}

export interface SlideMap {
  deck_path?: string;
  entries: SlideMapEntry[];
}

export interface RoundSummary {
  n: number;
  deck_score?: number | null;
  gate1_passed?: boolean | null;
  gate2_passed?: boolean | null;
  locked_slides: number[];
}

export interface Run {
  id: string;
  paper_id: string;
  brief: Brief;
  brief_text?: string;
  blueprint_id: string;
  skill_version: string;
  status: RunStatus;
  rounds: RoundSummary[];
  best_round_n?: number | null;
  budget_usd?: number;
  created_at?: string;
  updated_at?: string;
}

export interface LayoutElement {
  id: string;
  kind?: string;
  x: number;
  y: number;
  w: number;
  h: number;
  text?: string;
  claim_ids?: string[];
}

export interface LayoutSlide {
  slide: number;
  role?: string;
  width?: number;
  height?: number;
  elements: LayoutElement[];
}

export interface LayoutSpec {
  canvas_width: number;
  canvas_height: number;
  slides: LayoutSlide[];
}

export interface RoundDetail {
  n: number;
  deck_path?: string | null;
  slide_images: string[];
  slide_svgs?: string[];
  layout_spec?: LayoutSpec | null;
  gate1?: Gate1Result | null;
  gate2?: Gate2Result | null;
  gate3?: Gate3Result | null;
  human?: HumanReviewState;
  mutations: MutationRecord[];
  locked_slides: number[];
  comments: HumanComment[];
  cost_usd?: number;
  token_count?: number;
  slide_map?: SlideMap;
}

export type ProgressEventType =
  | "pages_parsed"
  | "claims_extracted"
  | "figures_extracted"
  | "blueprint_slot_filled"
  | "rendering"
  | "gate1_complete"
  | "gate2_complete"
  | "judging_slide"
  | "round_complete"
  | "awaiting_review"
  | "plateau"
  | "error"
  | "heartbeat";

export interface ProgressEvent {
  event: ProgressEventType;
  run_id: string;
  round_n?: number | null;
  message: string;
  timestamp: string;
  elapsed_ms: number;
  token_count: number;
  cost_usd: number;
  pages?: number | null;
  claims?: number | null;
  figures?: number | null;
  slot?: number | null;
  slot_total?: number | null;
  gate_flags?: number | null;
  slide?: number | null;
  slide_total?: number | null;
}

export interface CreateRunResponse {
  id: string;
  status: RunStatus;
  paper_id?: string;
  blueprint_id?: string;
  skill_version?: string;
}

export interface StartRunResponse {
  run_id: string;
  round_n: number;
  status: RunStatus;
  events_url?: string;
}

export interface BlueprintRole {
  role: string;
  required_content: string[];
  allowed_evidence_classes: string[];
  max_claims: number;
  counts_against_slide_count?: boolean;
}
