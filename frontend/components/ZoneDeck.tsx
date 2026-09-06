"use client";

import { pinPosition } from "@/lib/export-blockers";
import type { RoundDetail } from "@/lib/types";

export function ZoneDeck({
  current,
  previous,
  selectedSlide,
  provenance,
  compare,
  modalSlide,
  onSelect,
  onToggleLock,
  onProvenance,
  onCompare,
  onRound,
  onModal,
  onPlacePin,
}: {
  current: RoundDetail | null;
  previous: RoundDetail | null;
  selectedSlide: number;
  provenance: boolean;
  compare: boolean;
  modalSlide: number | null;
  onSelect: (slide: number) => void;
  onToggleLock: (slide: number) => void;
  onProvenance: (on: boolean) => void;
  onCompare: (on: boolean) => void;
  onRound: (n: number) => void;
  onModal: (slide: number | null) => void;
  onPlacePin: (slide: number, x: number, y: number) => void;
}) {
  if (!current) {
    return (
      <section className="zone p-4">
        <p className="zone-label">Zone C · Deck</p>
        <p className="mt-3 text-sm text-ink/50">No rendered slides yet.</p>
      </section>
    );
  }

  const images = current.slide_images;
  const showCompare = compare && previous;

  return (
    <section className="zone p-4">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className="zone-label">Zone C · Deck</p>
          <h2 className="font-display text-xl font-semibold">Round {current.n}</h2>
        </div>
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <label className="chip">
            Round
            <select
              className="bg-transparent"
              value={current.n}
              onChange={(e) => onRound(Number(e.target.value))}
            >
              {Array.from({ length: current.n }, (_, i) => i + 1).map((n) => (
                <option key={n} value={n}>
                  {n}
                </option>
              ))}
            </select>
          </label>
          <button
            type="button"
            className={`chip ${compare ? "border-ink bg-ink text-paper" : ""}`}
            disabled={!previous}
            onClick={() => onCompare(!compare)}
          >
            Compare previous
          </button>
          <button
            type="button"
            className={`chip ${provenance ? "border-ink bg-ink text-paper" : ""}`}
            onClick={() => onProvenance(!provenance)}
          >
            Provenance
          </button>
        </div>
      </div>

      <div className={`grid gap-3 ${showCompare ? "md:grid-cols-2" : ""}`}>
        <SlideGrid
          round={current}
          images={images}
          selectedSlide={selectedSlide}
          provenance={provenance}
          onSelect={onSelect}
          onToggleLock={onToggleLock}
          onModal={onModal}
        />
        {showCompare && previous && (
          <SlideGrid
            round={previous}
            images={previous.slide_images}
            selectedSlide={selectedSlide}
            provenance={provenance}
            onSelect={onSelect}
            onToggleLock={() => undefined}
            onModal={onModal}
            readOnly
          />
        )}
      </div>

      {modalSlide != null && images[modalSlide - 1] && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink/70 p-6" role="dialog">
          <div className="max-h-full w-full max-w-5xl overflow-auto bg-paper p-4">
            <div className="mb-2 flex justify-between">
              <p className="font-display text-lg">Slide {modalSlide}</p>
              <button type="button" className="text-sm underline" onClick={() => onModal(null)}>
                Close
              </button>
            </div>
            <SlideCanvas
              src={images[modalSlide - 1]}
              slide={modalSlide}
              round={current}
              provenance={provenance}
              large
              onClick={(x, y) => onPlacePin(modalSlide, x, y)}
            />
            <p className="mt-2 text-xs text-ink/60">Click the slide to drop a review pin.</p>
          </div>
        </div>
      )}
    </section>
  );
}

function SlideGrid({
  round,
  images,
  selectedSlide,
  provenance,
  onSelect,
  onToggleLock,
  onModal,
  readOnly,
}: {
  round: RoundDetail;
  images: string[];
  selectedSlide: number;
  provenance: boolean;
  onSelect: (n: number) => void;
  onToggleLock: (n: number) => void;
  onModal: (n: number) => void;
  readOnly?: boolean;
}) {
  return (
    <div>
      {!readOnly ? null : <p className="mb-2 font-mono text-[10px] uppercase text-ink/50">Previous round {round.n}</p>}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {images.map((src, i) => {
          const n = i + 1;
          const locked = round.locked_slides.includes(n);
          const flagged = isFlagged(round, n);
          const score = round.gate3?.slide_scores.find((s) => s.slide === n)?.score;
          const status = locked ? "locked" : flagged ? "flagged" : "pending";
          return (
            <article
              key={`${round.n}-${n}`}
              className={`border bg-white p-1 ${selectedSlide === n ? "border-ink" : "border-rule"}`}
            >
              <button type="button" className="block w-full" onClick={() => { onSelect(n); onModal(n); }}>
                <SlideCanvas src={src} slide={n} round={round} provenance={provenance} />
              </button>
              <div className="mt-1 flex items-center justify-between gap-1 px-1 text-[10px]">
                <span
                  className={`rounded-sm px-1.5 py-0.5 font-mono uppercase ${
                    status === "locked"
                      ? "bg-ok/15 text-ok"
                      : status === "flagged"
                        ? "bg-flag/15 text-flag"
                        : "bg-ink/10 text-ink/70"
                  }`}
                >
                  {status}
                </span>
                <span className="font-display text-sm">{score != null ? score : "—"}</span>
              </div>
              {!readOnly && (
                <button
                  type="button"
                  className="mt-1 w-full text-[10px] uppercase tracking-wide underline"
                  onClick={() => onToggleLock(n)}
                >
                  {locked ? "Unlock" : "Lock slide"}
                </button>
              )}
            </article>
          );
        })}
      </div>
    </div>
  );
}

function SlideCanvas({
  src,
  slide,
  round,
  provenance,
  large,
  onClick,
}: {
  src: string;
  slide: number;
  round: RoundDetail;
  provenance: boolean;
  large?: boolean;
  onClick?: (x: number, y: number) => void;
}) {
  const pins = collectPins(round, slide);
  const claims = (round.slide_map?.entries ?? []).filter((e) => e.slide === slide);
  return (
    <div
      className={`relative overflow-hidden border border-rule ${large ? "" : "aspect-video"}`}
      onClick={(e) => {
        if (!onClick) return;
        const box = e.currentTarget.getBoundingClientRect();
        onClick((e.clientX - box.left) / box.width, (e.clientY - box.top) / box.height);
      }}
    >
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src={src} alt={`Slide ${slide}`} className="block h-auto w-full" />
      {pins.map((pin, i) => {
        const pos = pinPosition(pin.x, pin.y);
        if (!pos) return null;
        return (
          <span
            key={`${pin.kind}-${i}`}
            className="pin absolute -translate-x-1/2 -translate-y-1/2"
            style={{ left: pos.left, top: pos.top, background: pin.color }}
            title={pin.title}
          />
        );
      })}
      {provenance &&
        claims.map((entry, i) => (
          <span
            key={entry.element_id}
            className="absolute rounded-sm bg-ink/80 px-1 py-0.5 font-mono text-[9px] text-paper"
            style={{ left: `${8 + (i % 3) * 28}%`, top: `${18 + Math.floor(i / 3) * 14}%` }}
          >
            {entry.claim_ids.join(" ")}
          </span>
        ))}
    </div>
  );
}

function isFlagged(round: RoundDetail, slide: number): boolean {
  const failed = [...(round.gate1?.checks ?? []), ...(round.gate2?.checks ?? [])].filter(
    (c) => !c.passed || c.flagged,
  );
  return failed.some((c) => (c.locations ?? []).some((l) => l.slide === slide));
}

function collectPins(
  round: RoundDetail,
  slide: number,
): { x?: number | null; y?: number | null; color: string; title: string; kind: string }[] {
  const pins: { x?: number | null; y?: number | null; color: string; title: string; kind: string }[] = [];
  for (const check of round.gate1?.checks ?? []) {
    if (check.passed && !check.flagged) continue;
    for (const loc of check.locations ?? []) {
      if (loc.slide === slide) {
        pins.push({ x: loc.x, y: loc.y, color: "#c23b22", title: `G1 ${check.name}: ${loc.detail || check.message}`, kind: "g1" });
      }
    }
  }
  for (const check of round.gate2?.checks ?? []) {
    if (check.passed) continue;
    for (const loc of check.locations ?? []) {
      if (loc.slide === slide) {
        pins.push({ x: loc.x, y: loc.y, color: "#b8860b", title: `G2 ${check.name}: ${loc.detail || check.message}`, kind: "g2" });
      }
    }
  }
  for (const c of round.comments) {
    if (c.slide === slide) {
      pins.push({
        x: c.x,
        y: c.y,
        color: c.scope === "always" ? "#8b1e3f" : "#1f4e5f",
        title: c.text,
        kind: "comment",
      });
    }
  }
  return pins;
}
