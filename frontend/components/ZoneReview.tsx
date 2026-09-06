"use client";

import { RUBRIC_CRITERIA, criterionName } from "@/lib/criteria";
import { exportBlockers } from "@/lib/export-blockers";
import type { HumanComment, RoundDetail, Scope, ScoreOverride, Severity } from "@/lib/types";
import { ScopeToggle } from "./ScopeToggle";

export function ZoneReview({
  current,
  previous,
  selectedSlide,
  draft,
  skillBefore,
  skillAfter,
  exportHref,
  onDraft,
  onSubmitComment,
  onOverride,
  onReiterate,
}: {
  current: RoundDetail | null;
  previous: RoundDetail | null;
  selectedSlide: number;
  draft: {
    text: string;
    severity: Severity;
    criterion_tag: string;
    scope: Scope;
    x: number;
    y: number;
  };
  skillBefore: string;
  skillAfter: string;
  exportHref: string;
  onDraft: (patch: Partial<typeof draft>) => void;
  onSubmitComment: () => void;
  onOverride: (override: ScoreOverride) => void;
  onReiterate: () => void;
}) {
  const blockers = exportBlockers(current, current?.slide_images.length ?? 0);
  const exportDisabled = blockers.length > 0;

  return (
    <section className="zone p-4">
      <p className="zone-label">Zone D · Review</p>
      <h2 className="font-display text-xl font-semibold">Judge, comments, skill</h2>

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <Scorecard current={current} onOverride={onOverride} />
        <div className="space-y-3 border border-rule bg-white p-3">
          <p className="font-mono text-[10px] uppercase tracking-widest text-brass">
            Comment composer · slide {selectedSlide}
          </p>
          <p className="text-xs text-ink/60">
            Pin at {(draft.x * 100).toFixed(0)}% × {(draft.y * 100).toFixed(0)}%. Click a slide in Zone C to move it.
          </p>
          <textarea
            className="w-full border border-ink/20 px-2 py-1 text-sm"
            rows={3}
            value={draft.text}
            onChange={(e) => onDraft({ text: e.target.value })}
            placeholder="What should change?"
          />
          <div className="flex flex-wrap gap-2 text-xs">
            <label className="chip">
              Severity
              <select
                value={draft.severity}
                onChange={(e) => onDraft({ severity: e.target.value as Severity })}
              >
                <option value="must-fix">must-fix</option>
                <option value="nice-to-have">nice-to-have</option>
              </select>
            </label>
            <label className="chip">
              Criterion
              <select
                value={draft.criterion_tag}
                onChange={(e) => onDraft({ criterion_tag: e.target.value })}
              >
                {RUBRIC_CRITERIA.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <ScopeToggle value={draft.scope} onChange={(scope) => onDraft({ scope })} />
          <button
            type="button"
            className="w-full border border-ink bg-ink py-2 text-sm font-semibold text-paper disabled:opacity-40"
            disabled={!draft.text.trim()}
            onClick={onSubmitComment}
          >
            Pin comment
          </button>
          <CommentList comments={current?.comments ?? []} />
        </div>
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <ScoreTrend current={current} previous={previous} />
        <SkillDiff before={skillBefore} after={skillAfter} />
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-3">
        <button
          type="button"
          className="rounded-sm bg-ink px-6 py-3 font-display text-lg font-semibold text-paper"
          onClick={onReiterate}
        >
          Reiterate
        </button>
        <div className="relative">
          <a
            href={exportDisabled ? undefined : exportHref}
            aria-disabled={exportDisabled}
            className={`inline-block rounded-sm border border-ink px-6 py-3 font-display text-lg ${
              exportDisabled ? "pointer-events-none cursor-not-allowed opacity-40" : ""
            }`}
            title={exportDisabled ? blockers.join(" ") : "Download export bundle"}
          >
            Export
          </a>
          {exportDisabled && (
            <p className="mt-1 max-w-md text-xs text-flag" title={blockers.join(" ")}>
              {blockers.join(" ")}
            </p>
          )}
        </div>
      </div>
    </section>
  );
}

function Scorecard({
  current,
  onOverride,
}: {
  current: RoundDetail | null;
  onOverride: (override: ScoreOverride) => void;
}) {
  const overrides = current?.human?.score_overrides ?? [];
  return (
    <div className="border border-rule bg-white p-3">
      <p className="font-mono text-[10px] uppercase tracking-widest text-brass">Judge scorecard · 10 criteria</p>
      <div className="mt-2 space-y-2">
        {RUBRIC_CRITERIA.map((def) => {
          const scored = findScore(current, def.id);
          const existing = overrides.find((o) => o.criterion === def.id);
          const original = existing?.original_score ?? scored?.score ?? null;
          const shown = existing?.override_score ?? original;
          return (
            <div key={def.id} className="grid grid-cols-[1fr_auto] gap-2 border-b border-rule/70 pb-2 text-xs">
              <div>
                <p className="font-medium">
                  {def.name}{" "}
                  <span className="font-mono text-[10px] text-ink/45">w{def.weight}</span>
                </p>
                <p className="text-ink/60">{scored?.rationale || "No rationale on this round."}</p>
                {existing && (
                  <p className="font-mono text-[10px] text-ok">
                    override Δ {existing.delta > 0 ? "+" : ""}
                    {existing.delta}
                  </p>
                )}
              </div>
              <label className="text-right">
                <span className="block font-mono text-[9px] uppercase text-ink/40">score</span>
                <input
                  type="number"
                  className="w-16 border border-ink/20 px-1 py-0.5 text-right"
                  value={shown ?? ""}
                  disabled={original == null}
                  onChange={(e) => {
                    if (original == null) return;
                    const override_score = Number(e.target.value);
                    onOverride({
                      criterion: def.id,
                      slide: scored?.slide ?? null,
                      original_score: original,
                      override_score,
                      delta: override_score - original,
                      rationale: "reviewer override",
                    });
                  }}
                />
              </label>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function findScore(round: RoundDetail | null, id: string) {
  if (!round?.gate3) return undefined;
  return (
    round.gate3.criteria.find((c) => c.criterion === id) ??
    round.gate3.deck_criteria?.find((c) => c.criterion === id) ??
    round.gate3.slide_results?.flatMap((s) => s.criteria).find((c) => c.criterion === id)
  );
}

function CommentList({ comments }: { comments: HumanComment[] }) {
  if (!comments.length) return <p className="text-xs text-ink/40">No comments yet.</p>;
  return (
    <ul className="space-y-1 text-xs">
      {comments.map((c) => (
        <li key={c.id} className="border border-rule px-2 py-1">
          <span className="font-mono text-[10px]">s{c.slide}</span> {c.text}{" "}
          <span className={c.scope === "always" ? "text-always" : "text-deckonly"}>
            {c.scope === "always" ? "ALWAYS" : "THIS DECK"}
          </span>
        </li>
      ))}
    </ul>
  );
}

function ScoreTrend({ current, previous }: { current: RoundDetail | null; previous: RoundDetail | null }) {
  const points = [previous, current]
    .filter((r): r is RoundDetail => Boolean(r?.gate3))
    .map((r) => ({ n: r.n, score: r.gate3!.deck_score }));
  const w = 320;
  const h = 120;
  const xs = points.map((p, i) => 24 + (i * (w - 48)) / Math.max(1, points.length - 1));
  const ys = points.map((p) => h - 20 - (p.score / 100) * (h - 40));
  const d = points
    .map((p, i) => `${i === 0 ? "M" : "L"} ${xs[i]} ${ys[i]}`)
    .join(" ");
  return (
    <div className="border border-rule bg-white p-3">
      <p className="font-mono text-[10px] uppercase tracking-widest text-brass">Score trend</p>
      {points.length === 0 ? (
        <p className="mt-2 text-xs text-ink/40">No Gate 3 scores yet.</p>
      ) : (
        <svg viewBox={`0 0 ${w} ${h}`} className="mt-2 w-full">
          <path d={d} fill="none" stroke="#b8860b" strokeWidth="2" />
          {points.map((p, i) => (
            <g key={p.n}>
              <circle cx={xs[i]} cy={ys[i]} r="4" fill="#1b1914" />
              <text x={xs[i]} y={ys[i] - 8} textAnchor="middle" fontSize="10">
                r{p.n} {p.score}
              </text>
            </g>
          ))}
        </svg>
      )}
    </div>
  );
}

function SkillDiff({ before, after }: { before: string; after: string }) {
  const a = before.split("\n").filter(Boolean);
  const b = after.split("\n").filter(Boolean);
  const removed = a.filter((line) => !b.includes(line));
  const added = b.filter((line) => !a.includes(line));
  const same = a.filter((line) => b.includes(line));
  return (
    <div className="border border-rule bg-white p-3">
      <p className="font-mono text-[10px] uppercase tracking-widest text-brass">Skill diff this round</p>
      <pre className="mt-2 max-h-40 overflow-auto font-mono text-[11px] leading-5">
        {same.map((line) => (
          <div key={`s-${line}`}> {line}</div>
        ))}
        {removed.map((line) => (
          <div key={`r-${line}`} className="bg-flag/15 text-flag">
            - {line}
          </div>
        ))}
        {added.map((line) => (
          <div key={`a-${line}`} className="bg-ok/15 text-ok">
            + {line}
          </div>
        ))}
        {!removed.length && !added.length && <div className="text-ink/40">No skill change this round.</div>}
      </pre>
    </div>
  );
}

export { criterionName };
