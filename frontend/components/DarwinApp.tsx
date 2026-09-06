"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import * as api from "@/lib/api";
import type { HumanComment, ProgressEvent, RoundDetail, SkillSuggestion } from "@/lib/types";

type Screen =
  | "upload"
  | "progress"
  | "deck"
  | "eval"
  | "suggestions"
  | "compare"
  | "done";

export function DarwinApp() {
  const [screen, setScreen] = useState<Screen>("upload");
  const [pdf, setPdf] = useState<File | null>(null);
  const [brief, setBrief] = useState(
    "Create an 8-slide medical affairs MSL deck to present to a physician.",
  );
  const [runId, setRunId] = useState<string | null>(null);
  const [roundN, setRoundN] = useState(1);
  const [events, setEvents] = useState<ProgressEvent[]>([]);
  const [current, setCurrent] = useState<RoundDetail | null>(null);
  const [previous, setPrevious] = useState<RoundDetail | null>(null);
  const [feedback, setFeedback] = useState("");
  const [slide, setSlide] = useState(1);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [suggestions, setSuggestions] = useState<SkillSuggestion[]>([]);
  const [picked, setPicked] = useState<number | null>(null);

  const images = useMemo(() => {
    if (!current) return [];
    const raw = current.slide_svgs?.length ? current.slide_svgs : current.slide_images;
    return raw.map(api.mediaSrc);
  }, [current]);

  const listen = (id: string, n: number) => {
    setEvents([]);
    return api.subscribeEvents(
      id,
      async (ev) => {
        setEvents((prev) => [...prev, ev]);
        if (ev.event === "awaiting_review" || ev.event === "round_complete" || ev.event === "error") {
          try {
            const detail = await api.getRound(id, ev.round_n ?? n);
            setCurrent(detail);
            setRoundN(detail.n);
            setSlide(1);
            if (ev.event !== "error") setScreen("deck");
          } catch (err) {
            setError(err instanceof Error ? err.message : "Could not load round");
          }
        }
        if (ev.event === "error") setError(ev.message);
      },
      () => undefined,
    );
  };

  const onGenerate = async () => {
    setError(null);
    if (!pdf) {
      setError("Upload a PDF first.");
      return;
    }
    try {
      setBusy(true);
      const created = await api.createRun(pdf, brief);
      setRunId(created.id);
      await api.startRun(created.id);
      setScreen("progress");
      listen(created.id, 1);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Generate failed");
    } finally {
      setBusy(false);
    }
  };

  const onLockEval = async () => {
    if (!runId || !current) return;
    setError(null);
    try {
      setBusy(true);
      if (feedback.trim()) {
        const comment: HumanComment = {
          id: `hc_${crypto.randomUUID().slice(0, 8)}`,
          slide,
          x: 0.5,
          y: 0.5,
          text: feedback.trim(),
          severity: "must-fix",
          criterion_tag: "information_density",
          scope: "always",
        };
        await api.addComments(runId, current.n, [comment]);
      }
      await api.lockEvaluation(runId, current.n, true);
      const detail = await api.getRound(runId, current.n);
      setCurrent(detail);
      setScreen("eval");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Lock failed");
    } finally {
      setBusy(false);
    }
  };

  const onSuggest = async () => {
    if (!runId || !current) return;
    setError(null);
    try {
      setBusy(true);
      const res = await api.suggestSkill(runId, current.n);
      setSuggestions(res.suggestions);
      setScreen("suggestions");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Suggest failed");
    } finally {
      setBusy(false);
    }
  };

  const onApply = async () => {
    if (!runId) return;
    setError(null);
    try {
      setBusy(true);
      if (current) setPrevious(current);
      setCurrent(null);
      const started = await api.applySkill(
        runId,
        suggestions.map((s) => s.text),
      );
      setRoundN(started.round_n);
      setScreen("progress");
      listen(runId, started.round_n);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Apply failed");
    } finally {
      setBusy(false);
    }
  };

  const onDecide = async (winner: number) => {
    if (!runId) return;
    setError(null);
    try {
      setBusy(true);
      await api.decideWinner(runId, winner);
      setPicked(winner);
      setScreen("done");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Decide failed");
    } finally {
      setBusy(false);
    }
  };

  const onToggleLock = async (n: number) => {
    if (!runId || !current) return;
    const locked = !current.locked_slides.includes(n);
    const res = await api.lockSlides(runId, current.n, [n], locked);
    setCurrent({ ...current, locked_slides: res.locked_slides });
  };

  return (
    <div className="min-h-svh bg-sand text-ink">
      <header className="mx-auto flex max-w-6xl items-center justify-between px-5 py-4">
        <Link href="/" className="font-display text-lg font-bold">
          MA<span className="text-pink">·</span>Darwin
        </Link>
        <p className="text-[10px] uppercase tracking-[0.16em] text-muted">{runId ?? "no run"}</p>
      </header>

      <main className="mx-auto max-w-6xl px-5 pb-16">
        {error && <p className="mb-4 rounded-md border border-pink/40 bg-white px-3 py-2 text-sm text-pink">{error}</p>}

        {screen === "upload" && (
          <section className="rounded-xl border-2 border-teal/30 bg-paper p-6 shadow-[4px_5px_0_#d6ded3]">
            <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-muted">Document center</p>
            <h1 className="font-display text-3xl">Upload a PDF</h1>
            <p className="mt-2 max-w-lg text-sm text-muted">
              Parsed on Railway with page-level claims. Claude Opus 4.8 plans the deck. The skill writes the PowerPoint.
            </p>
            <label className="mt-6 block rounded-lg border border-dashed border-teal/40 bg-white px-4 py-8 text-center">
              <input
                type="file"
                accept="application/pdf"
                className="hidden"
                onChange={(e) => setPdf(e.target.files?.[0] ?? null)}
              />
              <span className="font-display text-sm">{pdf ? pdf.name : "Select PDF"}</span>
            </label>
            <textarea
              className="mt-4 w-full rounded-md border border-teal/25 bg-white p-3 text-sm"
              rows={3}
              value={brief}
              onChange={(e) => setBrief(e.target.value)}
            />
            <button
              disabled={busy}
              onClick={onGenerate}
              className="mt-4 rounded-md bg-teal px-4 py-2 text-sm font-extrabold text-sand disabled:opacity-50"
            >
              Convert to PowerPoint
            </button>
          </section>
        )}

        {screen === "progress" && (
          <section className="rounded-xl border-2 border-teal/30 bg-paper p-6">
            <h1 className="font-display text-2xl">Generating slides…</h1>
            <p className="text-sm text-muted">Parse → ledger → Opus 4.8 plan → skill writer → gates.</p>
            <ol className="mt-4 space-y-1 font-mono text-xs text-teal">
              {events.map((ev, i) => (
                <li key={`${ev.event}-${i}`}>{ev.message}</li>
              ))}
            </ol>
          </section>
        )}

        {screen === "deck" && current && (
          <section className="grid gap-4 lg:grid-cols-[1.4fr_0.8fr]">
            <div className="rounded-xl border-2 border-teal/30 bg-paper p-4">
              <div className="mb-3 flex items-center justify-between gap-2">
                <h1 className="font-display text-2xl">Generated deck</h1>
                <div className="flex gap-2">
                  <button className="rounded border px-2 py-1 text-xs" onClick={() => onToggleLock(slide)}>
                    {current.locked_slides.includes(slide) ? "Unlock slide" : "Lock slide"}
                  </button>
                  {runId && (
                    <a className="rounded border px-2 py-1 text-xs" href={api.exportUrl(runId, current.n)}>
                      Download .pptx
                    </a>
                  )}
                </div>
              </div>
              {images[slide - 1] ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={images[slide - 1]} alt={`Slide ${slide}`} className="w-full rounded-md border bg-white" />
              ) : (
                <p className="text-sm text-muted">Slide preview not ready yet.</p>
              )}
              <div className="mt-3 flex items-center justify-between text-xs">
                <button disabled={slide <= 1} onClick={() => setSlide((s) => s - 1)}>
                  ‹ Prev
                </button>
                <span>
                  Slide {slide} / {images.length || 1}
                </span>
                <button disabled={slide >= images.length} onClick={() => setSlide((s) => s + 1)}>
                  Next ›
                </button>
              </div>
            </div>
            <aside className="rounded-xl border-2 border-teal/30 bg-paper p-4">
              <h2 className="font-display text-lg">Your feedback</h2>
              <textarea
                className="mt-2 w-full rounded-md border border-teal/25 bg-white p-2 text-sm"
                rows={8}
                value={feedback}
                onChange={(e) => setFeedback(e.target.value)}
                placeholder="What do you like or want changed?"
              />
              <button
                disabled={busy}
                onClick={onLockEval}
                className="mt-3 w-full rounded-md bg-pink px-3 py-2 text-sm font-extrabold text-white"
              >
                Lock evaluation
              </button>
              {previous && (
                <button className="mt-2 w-full text-xs underline" onClick={() => setScreen("compare")}>
                  Compare versions
                </button>
              )}
            </aside>
          </section>
        )}

        {screen === "eval" && current && (
          <section className="rounded-xl border-2 border-teal/30 bg-paper p-6">
            <h1 className="font-display text-2xl">AI evaluation</h1>
            <p className="text-sm text-muted">Your evaluation is locked. Gate 3 score: {current.gate3?.deck_score ?? "—"}</p>
            <ul className="mt-4 space-y-2 text-sm">
              {(current.gate3?.criteria ?? []).slice(0, 8).map((c) => (
                <li key={c.criterion} className="rounded-md bg-white px-3 py-2">
                  <strong>{c.criterion}</strong> · {c.score ?? "—"} — {c.rationale}
                </li>
              ))}
            </ul>
            <button
              disabled={busy}
              onClick={onSuggest}
              className="mt-4 rounded-md bg-teal px-4 py-2 text-sm font-extrabold text-sand"
            >
              See skill suggestions
            </button>
          </section>
        )}

        {screen === "suggestions" && (
          <section className="rounded-xl border-2 border-teal/30 bg-paper p-6">
            <h1 className="font-display text-2xl">Suggested skill changes</h1>
            <ul className="mt-4 space-y-2">
              {suggestions.map((s) => (
                <li key={s.id} className="rounded-md bg-white px-3 py-2 text-sm">
                  <p className="font-semibold">{s.text}</p>
                  {s.rationale && <p className="text-muted">{s.rationale}</p>}
                </li>
              ))}
            </ul>
            <button
              disabled={busy}
              onClick={onApply}
              className="mt-4 rounded-md bg-teal px-4 py-2 text-sm font-extrabold text-sand"
            >
              Apply changes & regenerate
            </button>
          </section>
        )}

        {screen === "compare" && current && previous && (
          <section className="rounded-xl border-2 border-teal/30 bg-paper p-6">
            <h1 className="font-display text-2xl">Original vs regenerated</h1>
            <div className="mt-4 grid gap-4 md:grid-cols-2">
              <div>
                <p className="font-display text-sm">Version {previous.n}</p>
                <p className="text-xs text-muted">Score {previous.gate3?.deck_score ?? "—"}</p>
              </div>
              <div>
                <p className="font-display text-sm">Version {current.n}</p>
                <p className="text-xs text-muted">Score {current.gate3?.deck_score ?? "—"}</p>
              </div>
            </div>
            <div className="mt-4 flex gap-2">
              <button className="rounded-md border px-3 py-2 text-sm" onClick={() => onDecide(previous.n)}>
                Keep version {previous.n}
              </button>
              <button className="rounded-md bg-teal px-3 py-2 text-sm text-sand" onClick={() => onDecide(current.n)}>
                Keep version {current.n}
              </button>
            </div>
          </section>
        )}

        {screen === "done" && (
          <section className="rounded-xl border-2 border-teal/30 bg-paper p-6">
            <h1 className="font-display text-2xl">Round complete</h1>
            <p className="text-sm text-muted">Winner: version {picked}. Upload a new PDF or start another improvement round.</p>
            <button className="mt-4 rounded-md bg-teal px-4 py-2 text-sm text-sand" onClick={() => setScreen("upload")}>
              Upload new PDF
            </button>
          </section>
        )}
      </main>
    </div>
  );
}
