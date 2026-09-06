"use client";

import { useCallback, useMemo, useRef, useState } from "react";
import * as api from "@/lib/api";
import { suggestBrief } from "@/lib/parse-brief";
import type { Brief, HumanComment, ProgressEvent, RoundDetail, Scope, ScoreOverride, Severity } from "@/lib/types";
import { ZoneDeck } from "./ZoneDeck";
import { ZoneProgress } from "./ZoneProgress";
import { ZoneReview } from "./ZoneReview";
import { ZoneSetup } from "./ZoneSetup";

const emptyDraft = {
  text: "",
  severity: "must-fix" as Severity,
  criterion_tag: "information_density",
  scope: "this-deck-only" as Scope,
  x: 0.5,
  y: 0.5,
};

export function RunApp() {
  const [pdf, setPdf] = useState<File | null>(null);
  const [briefText, setBriefText] = useState("");
  const [suggested, setSuggested] = useState<Brief | null>(null);
  const [confirmed, setConfirmed] = useState(false);
  const [runId, setRunId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [events, setEvents] = useState<ProgressEvent[]>([]);
  const [streaming, setStreaming] = useState(false);
  const [roundN, setRoundN] = useState(1);
  const [current, setCurrent] = useState<RoundDetail | null>(null);
  const [previous, setPrevious] = useState<RoundDetail | null>(null);
  const [selectedSlide, setSelectedSlide] = useState(1);
  const [provenance, setProvenance] = useState(false);
  const [compare, setCompare] = useState(false);
  const [modalSlide, setModalSlide] = useState<number | null>(null);
  const [draft, setDraft] = useState(emptyDraft);
  const [skillBefore, setSkillBefore] = useState("max 5 bullets, max 12 words each");
  const [skillAfter, setSkillAfter] = useState("max 5 bullets, max 12 words each");
  const stopRef = useRef<(() => void) | null>(null);

  const listen = useCallback((id: string, n: number) => {
    stopRef.current?.();
    setEvents([]);
    setStreaming(true);
    stopRef.current = api.subscribeEvents(
      id,
      async (ev) => {
        setEvents((prev) => [...prev, ev]);
        if (ev.event === "awaiting_review" || ev.event === "round_complete" || ev.event === "error") {
          const detail = await api.getRound(id, n);
          setCurrent(detail);
          setStreaming(false);
          if (ev.event === "awaiting_review" || ev.event === "error") stopRef.current?.();
        }
      },
      () => setStreaming(false),
    );
  }, []);

  const onParse = async () => {
    setError(null);
    setConfirmed(false);
    try {
      setBusy(true);
      let id = runId;
      if (!id) {
        if (!pdf) throw new Error("Upload a PDF first.");
        const created = await api.createRun(pdf, briefText);
        id = created.id;
        setRunId(id);
      }
      const brief = await api.parseBrief(id, briefText);
      setSuggested(brief);
    } catch (err) {
      setSuggested(suggestBrief(briefText));
      setError(err instanceof Error ? err.message : "Parse failed");
    } finally {
      setBusy(false);
    }
  };

  const onConfirm = async () => {
    if (!suggested) return;
    setError(null);
    try {
      if (runId) await api.updateBrief(runId, suggested);
      setConfirmed(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Confirm failed");
    }
  };

  const onGenerate = async () => {
    if (!suggested) return;
    setError(null);
    try {
      setBusy(true);
      let id = runId;
      if (!id) {
        if (!pdf) throw new Error("Upload a PDF first.");
        const created = await api.createRun(pdf, briefText);
        id = created.id;
        setRunId(id);
      }
      await api.updateBrief(id, suggested);
      setConfirmed(true);
      const started = await api.startRun(id);
      setRoundN(started.round_n);
      setPrevious(null);
      listen(id, started.round_n);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Generate failed");
    } finally {
      setBusy(false);
    }
  };

  const onToggleLock = async (slide: number) => {
    if (!runId || !current) return;
    const locked = !current.locked_slides.includes(slide);
    const res = await api.lockSlides(runId, current.n, [slide], locked);
    setCurrent({ ...current, locked_slides: res.locked_slides });
  };

  const onSubmitComment = async () => {
    if (!runId || !current || !draft.text.trim()) return;
    const comment: HumanComment = {
      id: `hc_${crypto.randomUUID().slice(0, 8)}`,
      slide: selectedSlide,
      x: draft.x,
      y: draft.y,
      text: draft.text.trim(),
      severity: draft.severity,
      criterion_tag: draft.criterion_tag,
      scope: draft.scope,
    };
    const res = await api.addComments(runId, current.n, [comment]);
    setCurrent({ ...current, comments: res.comments });
    if (comment.scope === "always") {
      setSkillAfter((prev) => (prev.includes(comment.text) ? prev : `${prev}\n${comment.text}`));
    }
    setDraft({ ...emptyDraft, scope: draft.scope, criterion_tag: draft.criterion_tag });
  };

  const onOverride = async (override: ScoreOverride) => {
    if (!runId || !current) return;
    const recorded = await api.overrideScore(runId, current.n, override);
    const human = current.human ?? { approved_slides: [], score_overrides: [], synthesized_approvals: [] };
    setCurrent({
      ...current,
      human: {
        ...human,
        score_overrides: [
          ...human.score_overrides.filter((o) => o.criterion !== recorded.criterion),
          recorded,
        ],
      },
    });
  };

  const onReiterate = async () => {
    if (!runId) return;
    setError(null);
    try {
      setBusy(true);
      if (current) setPrevious(current);
      const started = await api.reiterateRun(runId);
      setRoundN(started.round_n);
      setCompare(true);
      listen(runId, started.round_n);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Reiterate failed");
    } finally {
      setBusy(false);
    }
  };

  const exportHref = useMemo(
    () => (runId ? api.exportUrl(runId, current?.n) : "#"),
    [runId, current?.n],
  );

  return (
    <div className="mx-auto max-w-[1400px] space-y-4 px-4 py-6">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-brass">Medical affairs</p>
          <h1 className="font-display text-3xl font-semibold tracking-tight">MA-Darwin review desk</h1>
        </div>
        <p className="font-mono text-[11px] text-ink/50">{runId ?? "no run"}</p>
      </header>
      {error && <p className="border border-flag bg-flag/10 px-3 py-2 text-sm text-flag">{error}</p>}

      <div className="grid gap-4 lg:grid-cols-2">
        <ZoneSetup
          pdfName={pdf?.name ?? ""}
          briefText={briefText}
          suggested={suggested}
          confirmed={confirmed}
          busy={busy}
          onPdf={setPdf}
          onDemoPaper={async () => {
            const res = await fetch("/demo/paper.pdf");
            const blob = await res.blob();
            setPdf(new File([blob], "demo_trial_2024.pdf", { type: "application/pdf" }));
            if (!briefText) {
              setBriefText(
                "Create an 8 slide MSL physician deck covering design, primary endpoint, and safety.",
              );
            }
          }}
          onBriefText={(t) => {
            setBriefText(t);
            setConfirmed(false);
          }}
          onChip={(patch) => {
            setSuggested((prev) => (prev ? { ...prev, ...patch } : prev));
            setConfirmed(false);
          }}
          onParse={onParse}
          onConfirm={onConfirm}
          onGenerate={onGenerate}
        />
        <ZoneProgress events={events} streaming={streaming} />
      </div>

      <ZoneDeck
        current={current}
        previous={previous}
        selectedSlide={selectedSlide}
        provenance={provenance}
        compare={compare}
        modalSlide={modalSlide}
        onSelect={setSelectedSlide}
        onToggleLock={onToggleLock}
        onProvenance={setProvenance}
        onCompare={setCompare}
        onRound={async (n) => {
          setRoundN(n);
          if (runId) {
            const detail = await api.getRound(runId, n);
            setCurrent(detail);
          }
        }}
        onModal={setModalSlide}
        onPlacePin={(slide, x, y) => {
          setSelectedSlide(slide);
          setDraft((d) => ({ ...d, x, y }));
        }}
      />

      <ZoneReview
        current={current}
        previous={previous}
        selectedSlide={selectedSlide}
        draft={draft}
        skillBefore={skillBefore}
        skillAfter={skillAfter}
        exportHref={exportHref}
        onDraft={(patch) => setDraft((d) => ({ ...d, ...patch }))}
        onSubmitComment={onSubmitComment}
        onOverride={onOverride}
        onReiterate={onReiterate}
      />
    </div>
  );
}
