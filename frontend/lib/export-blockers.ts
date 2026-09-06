import type { RoundDetail } from "./types";

export function exportBlockers(round: RoundDetail | null, slideCount: number): string[] {
  if (!round) return ["No round is available to export."];
  const blockers: string[] = [];
  if (!round.gate1?.passed) {
    const failed = round.gate1?.checks.filter((c) => !c.passed).map((c) => c.name) ?? [];
    blockers.push(
      failed.length
        ? `Gate 1 has not passed (${failed.join(", ")}).`
        : "Gate 1 has not passed.",
    );
  }
  if (!round.gate2?.passed) {
    const failed = round.gate2?.checks.filter((c) => !c.passed) ?? [];
    const detail = failed.map((c) => c.message || c.name).join("; ");
    blockers.push(detail ? `Gate 2 has not passed: ${detail}` : "Gate 2 has not passed.");
  }
  const locked = new Set(round.locked_slides);
  const unlocked = Array.from({ length: slideCount }, (_, i) => i + 1).filter((n) => !locked.has(n));
  if (unlocked.length) {
    blockers.push(`Slides not locked: ${unlocked.join(", ")}.`);
  }
  return blockers;
}

export const CANVAS_WIDTH_IN = 13.333333;
export const CANVAS_HEIGHT_IN = 7.5;

function pct(value: number): string {
  return `${Math.min(98, Math.max(0, Math.round(value * 100) / 100))}%`;
}

export function pinPosition(x: number | null | undefined, y: number | null | undefined): {
  left: string;
  top: string;
} | null {
  if (x == null || y == null) return null;
  // Legacy comments / e2e store unit-square fractions.
  if (x <= 1 && y <= 1) {
    return { left: pct(x * 100), top: pct(y * 100) };
  }
  // LayoutSpec inches. Values past the canvas are treated as points (72 / in).
  const xi = x > CANVAS_WIDTH_IN + 0.05 ? x / 72 : x;
  const yi = y > CANVAS_HEIGHT_IN + 0.05 ? y / 72 : y;
  return { left: pct((xi / CANVAS_WIDTH_IN) * 100), top: pct((yi / CANVAS_HEIGHT_IN) * 100) };
}

export function layoutPinPosition(x: number | null | undefined, y: number | null | undefined): {
  left: string;
  top: string;
} | null {
  if (x == null || y == null) return null;
  return { left: pct((x / CANVAS_WIDTH_IN) * 100), top: pct((y / CANVAS_HEIGHT_IN) * 100) };
}
