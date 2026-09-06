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

export function pinPosition(x: number | null | undefined, y: number | null | undefined): {
  left: string;
  top: string;
} | null {
  if (x == null || y == null) return null;
  const nx = x > 1 ? x / 960 : x;
  const ny = y > 1 ? y / 540 : y;
  return { left: `${Math.min(98, Math.max(0, nx * 100))}%`, top: `${Math.min(98, Math.max(0, ny * 100))}%` };
}
