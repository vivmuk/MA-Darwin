import type { Brief } from "./types";

/** Suggest structured fields from freeform text. Caller must confirm — never auto-apply. */
export function suggestBrief(text: string): Brief {
  const slideMatch = text.match(/(\d+)\s*-?\s*slide/i);
  return {
    slide_count: slideMatch ? Number(slideMatch[1]) : 8,
    deck_type: "msl_physician",
    audience: /\b(kOl|specialist|cardiolog|oncolog|physician|msl)\b/i.test(text)
      ? (text.match(/\b(cardiolog\w*|oncolog\w*|physician|KOL|specialist)\b/i)?.[0] ?? "physician")
      : "physician",
    purpose: /\bMSL\b/i.test(text) ? "MSL presentation" : "MSL presentation",
    notes: text.trim(),
  };
}
