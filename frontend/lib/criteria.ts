/** Rubric ids from backend/config/rubric.yaml — 8 slide + 2 deck = 10. */
export interface CriterionDef {
  id: string;
  name: string;
  weight: number;
  scope: "slide" | "deck";
}

export const RUBRIC_CRITERIA: CriterionDef[] = [
  { id: "visual_hierarchy", name: "Visual hierarchy", weight: 15, scope: "slide" },
  { id: "layout_composition", name: "Layout & composition", weight: 15, scope: "slide" },
  { id: "information_density", name: "Information density", weight: 10, scope: "slide" },
  { id: "typography", name: "Typography", weight: 10, scope: "slide" },
  { id: "visual_storytelling", name: "Visual storytelling", weight: 15, scope: "slide" },
  { id: "charts_data_visualization", name: "Charts & data visualization", weight: 10, scope: "slide" },
  { id: "colour_contrast", name: "Colour & contrast", weight: 8, scope: "slide" },
  { id: "professional_polish", name: "Professional polish", weight: 5, scope: "slide" },
  { id: "consistency_design_system", name: "Consistency / design system", weight: 7, scope: "deck" },
  { id: "executive_premium_feel", name: "Executive / premium feel", weight: 5, scope: "deck" },
];

export function criterionName(id: string): string {
  return RUBRIC_CRITERIA.find((c) => c.id === id)?.name ?? id.replaceAll("_", " ");
}
