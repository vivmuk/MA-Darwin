"use client";

import { BLUEPRINT_ID, BLUEPRINT_NAME, BLUEPRINT_ROLES } from "@/lib/blueprint";
import type { Brief } from "@/lib/types";

export function ZoneSetup({
  pdfName,
  briefText,
  suggested,
  confirmed,
  busy,
  onPdf,
  onDemoPaper,
  onBriefText,
  onChip,
  onParse,
  onConfirm,
  onGenerate,
}: {
  pdfName: string;
  briefText: string;
  suggested: Brief | null;
  confirmed: boolean;
  busy: boolean;
  onPdf: (file: File) => void;
  onDemoPaper: () => void;
  onBriefText: (text: string) => void;
  onChip: (patch: Partial<Brief>) => void;
  onParse: () => void;
  onConfirm: () => void;
  onGenerate: () => void;
}) {
  const canParse = Boolean(pdfName && briefText.trim());
  const canGenerate = canParse && confirmed && !busy;

  return (
    <section className="zone p-4">
      <div className="mb-3 flex items-baseline justify-between">
        <p className="zone-label">Zone A · Setup</p>
        <p className="font-mono text-[10px] text-ink/50">{BLUEPRINT_ID}</p>
      </div>
      <h2 className="font-display text-xl font-semibold">Paper and brief</h2>

      <label className="mt-3 block cursor-pointer rounded-sm border border-dashed border-ink/30 bg-white px-3 py-3 text-sm">
        <input
          type="file"
          accept="application/pdf"
          className="sr-only"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) onPdf(file);
          }}
        />
        {pdfName ? (
          <span>
            PDF selected: <strong>{pdfName}</strong>
          </span>
        ) : (
          <span>Upload research paper PDF</span>
        )}
      </label>
      <button
        type="button"
        className="mt-2 text-xs underline"
        onClick={onDemoPaper}
      >
        Use synthetic demo paper
      </button>

      <textarea
        className="mt-3 w-full resize-y rounded-sm border border-ink/20 bg-white px-3 py-2 text-sm outline-none ring-brass focus:ring-2"
        rows={3}
        placeholder="Freeform brief — e.g. Create an 8 slide MSL physician deck covering design, primary endpoint, and safety."
        value={briefText}
        onChange={(e) => onBriefText(e.target.value)}
      />

      <div className="mt-2 flex flex-wrap gap-2">
        <button
          type="button"
          className="rounded-sm border border-ink bg-ink px-3 py-1.5 text-xs font-semibold uppercase tracking-wide text-paper disabled:opacity-40"
          disabled={!canParse || busy}
          onClick={onParse}
        >
          Parse brief
        </button>
        <p className="self-center text-[11px] text-ink/60">
          Suggestions stay editable. Generate stays off until you confirm.
        </p>
      </div>

      {suggested && (
        <div className="mt-3 space-y-2 rounded-sm border border-brass/40 bg-white p-3">
          <p className="font-mono text-[10px] uppercase tracking-widest text-brass">
            {confirmed ? "Confirmed brief" : "Suggested — edit and confirm"}
          </p>
          <div className="flex flex-wrap gap-2">
            <Chip label="slides">
              <input
                type="number"
                min={1}
                className="w-14 bg-transparent outline-none"
                value={suggested.slide_count}
                onChange={(e) => onChip({ slide_count: Number(e.target.value) || 1 })}
              />
            </Chip>
            <Chip label="deck">
              <select
                className="bg-transparent outline-none"
                value={suggested.deck_type}
                onChange={(e) => onChip({ deck_type: e.target.value as Brief["deck_type"] })}
              >
                <option value="msl_physician">msl_physician</option>
              </select>
            </Chip>
            <Chip label="audience">
              <input
                className="w-28 bg-transparent outline-none"
                value={suggested.audience}
                onChange={(e) => onChip({ audience: e.target.value })}
              />
            </Chip>
            <Chip label="purpose">
              <input
                className="w-36 bg-transparent outline-none"
                value={suggested.purpose}
                onChange={(e) => onChip({ purpose: e.target.value })}
              />
            </Chip>
          </div>
          <button
            type="button"
            className="rounded-sm border border-ok px-3 py-1.5 text-xs font-semibold uppercase tracking-wide text-ok"
            onClick={onConfirm}
          >
            Confirm parsed fields
          </button>
        </div>
      )}

      <div className="mt-4">
        <p className="zone-label mb-2">Blueprint preview</p>
        <p className="mb-2 text-xs text-ink/70">{BLUEPRINT_NAME}</p>
        <ol className="grid grid-cols-1 gap-1 text-xs sm:grid-cols-2">
          {BLUEPRINT_ROLES.map((role, i) => (
            <li key={role.role} className="flex items-start gap-2 border-b border-rule/80 py-1">
              <span className="font-mono text-[10px] text-brass">{String(i + 1).padStart(2, "0")}</span>
              <span>
                <span className="font-medium">{role.role}</span>
                {role.counts_against_slide_count === false && (
                  <span className="ml-1 text-ink/50">(appended)</span>
                )}
                <span className="block text-[10px] text-ink/50">
                  {role.required_content.join(" · ")}
                </span>
              </span>
            </li>
          ))}
        </ol>
      </div>

      <button
        type="button"
        className="mt-4 w-full rounded-sm bg-brass px-4 py-2.5 font-display text-lg font-semibold text-ink disabled:cursor-not-allowed disabled:opacity-40"
        disabled={!canGenerate}
        onClick={onGenerate}
      >
        Generate
      </button>
    </section>
  );
}

function Chip({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="chip">
      <span className="font-mono text-[9px] uppercase tracking-widest text-ink/50">{label}</span>
      {children}
    </label>
  );
}
