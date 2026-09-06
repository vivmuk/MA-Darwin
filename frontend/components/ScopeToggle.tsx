"use client";

import type { Scope } from "@/lib/types";

export function ScopeToggle({
  value,
  onChange,
}: {
  value: Scope;
  onChange: (scope: Scope) => void;
}) {
  return (
    <div className="space-y-2">
      <p className="font-mono text-[11px] font-semibold uppercase tracking-[0.18em] text-always">
        Skill scope — the most important control
      </p>
      <div className="scope-toggle" role="group" aria-label="Comment scope">
        <button
          type="button"
          className={value === "this-deck-only" ? "on-deck" : "off"}
          onClick={() => onChange("this-deck-only")}
        >
          This deck only
        </button>
        <button
          type="button"
          className={value === "always" ? "on-always" : "off"}
          onClick={() => onChange("always")}
        >
          Always
        </button>
      </div>
      <p className="text-xs text-ink/70">
        {value === "always"
          ? "ALWAYS writes a candidate rule into the generation skill."
          : "THIS DECK ONLY is a one-off fix for the next round."}
      </p>
    </div>
  );
}
