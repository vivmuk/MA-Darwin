"use client";

import type { ProgressEvent } from "@/lib/types";

export function ZoneProgress({
  events,
  streaming,
}: {
  events: ProgressEvent[];
  streaming: boolean;
}) {
  const last = events.at(-1);
  return (
    <section className="zone flex min-h-[22rem] flex-col p-4">
      <div className="mb-3 flex items-baseline justify-between">
        <p className="zone-label">Zone B · Progress</p>
        <p className="font-mono text-[10px] uppercase tracking-widest text-ink/50">
          {streaming ? "live SSE" : events.length ? "stream closed" : "idle"}
        </p>
      </div>
      <h2 className="font-display text-xl font-semibold">Run log</h2>
      <p className="mt-1 text-xs text-ink/60">
        Only events the backend sent. No inferred status.
      </p>

      <div className="mt-3 grid grid-cols-3 gap-2 text-xs">
        <Stat label="Elapsed" value={last ? formatMs(last.elapsed_ms) : "—"} />
        <Stat label="Tokens" value={last ? String(last.token_count) : "—"} />
        <Stat label="Cost" value={last ? `$${last.cost_usd.toFixed(2)}` : "—"} />
      </div>

      <ol className="mt-3 min-h-0 flex-1 space-y-1 overflow-auto border border-rule bg-white p-2 font-mono text-[11px]">
        {events.length === 0 ? (
          <li className="text-ink/40">No events yet.</li>
        ) : (
          events.map((ev, i) => (
            <li key={`${ev.event}-${ev.timestamp}-${i}`} className="flex gap-3">
              <time className="shrink-0 text-ink/45">{formatStamp(ev.timestamp)}</time>
              <span className="text-brass">{ev.event}</span>
              <span>{ev.message}</span>
            </li>
          ))
        )}
      </ol>
    </section>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="border border-rule bg-white px-2 py-1.5">
      <p className="font-mono text-[9px] uppercase tracking-widest text-ink/45">{label}</p>
      <p className="font-display text-lg">{value}</p>
    </div>
  );
}

function formatMs(ms: number): string {
  const s = Math.floor(ms / 1000);
  const m = Math.floor(s / 60);
  return `${m}:${String(s % 60).padStart(2, "0")}`;
}

function formatStamp(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleTimeString([], { hour12: false, hour: "2-digit", minute: "2-digit", second: "2-digit" });
}
