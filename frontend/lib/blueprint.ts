import type { BlueprintRole } from "./types";

/** Static copy of blueprints/msl_physician_8.yaml roles (PRD §7.3). */
export const BLUEPRINT_ROLES: BlueprintRole[] = [
  {
    role: "title",
    required_content: ["paper_title", "journal", "citation", "audience", "evidence_class"],
    allowed_evidence_classes: ["background", "design"],
    max_claims: 4,
  },
  {
    role: "unmet_need",
    required_content: ["clinical_context", "unmet_need"],
    allowed_evidence_classes: ["background"],
    max_claims: 5,
  },
  {
    role: "study_design",
    required_content: ["design_type", "N", "arms", "duration", "endpoints"],
    allowed_evidence_classes: ["design"],
    max_claims: 6,
  },
  {
    role: "population",
    required_content: ["inclusion", "exclusion", "baseline_characteristics"],
    allowed_evidence_classes: ["design", "background"],
    max_claims: 6,
  },
  {
    role: "primary_endpoint",
    required_content: ["primary_result", "CI_or_p", "design_N"],
    allowed_evidence_classes: ["primary_endpoint"],
    max_claims: 5,
  },
  {
    role: "key_secondary",
    required_content: ["secondary_results_labelled"],
    allowed_evidence_classes: ["secondary_endpoint", "exploratory", "post_hoc"],
    max_claims: 6,
  },
  {
    role: "safety",
    required_content: ["ae_profile", "discontinuations"],
    allowed_evidence_classes: ["safety"],
    max_claims: 6,
  },
  {
    role: "limitations_relevance",
    required_content: ["limitations", "clinical_relevance"],
    allowed_evidence_classes: ["limitation", "background"],
    max_claims: 6,
  },
  {
    role: "references",
    required_content: ["citations"],
    allowed_evidence_classes: ["background", "design", "primary_endpoint", "secondary_endpoint", "exploratory", "post_hoc", "safety", "limitation"],
    max_claims: 20,
    counts_against_slide_count: false,
  },
];

export const BLUEPRINT_ID = "msl_physician_8";
export const BLUEPRINT_NAME = "MSL physician deck (8 content slides + references)";
