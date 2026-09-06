import { loadFrozenArtifacts } from "./fixtures";
import { suggestBrief } from "../parse-brief";
import type {
  Brief,
  HumanComment,
  MutationRecord,
  ProgressEvent,
  RoundDetail,
  Run,
  ScoreOverride,
} from "../types";

export interface StoredRun {
  run: Run;
  briefConfirmed: boolean;
  paperName: string;
  rounds: Map<number, RoundDetail>;
  events: ProgressEvent[];
  skillBefore: string;
  skillAfter: string;
}

const g = globalThis as unknown as { __maDarwinStore?: Map<string, StoredRun> };

function store(): Map<string, StoredRun> {
  if (!g.__maDarwinStore) g.__maDarwinStore = new Map();
  return g.__maDarwinStore;
}

function newId(): string {
  const hex = Array.from({ length: 12 }, () => Math.floor(Math.random() * 16).toString(16)).join("");
  return `run_${hex}`;
}

function slideImages(): string[] {
  return ["/demo/slide-1.svg", "/demo/slide-2.svg", "/demo/slide-3.svg", "/demo/slide-4.svg"];
}

function buildRound(n: number, artifacts: ReturnType<typeof loadFrozenArtifacts>): RoundDetail {
  const gate3 = structuredClone(artifacts.gate3);
  if (n > 1) {
    gate3.deck_score = Math.min(100, gate3.deck_score + 3);
    gate3.slide_scores = gate3.slide_scores.map((s) => ({
      ...s,
      score: Math.min(100, s.score + 2),
    }));
  }
  const mutations: MutationRecord[] =
    n > 1
      ? [
          {
            id: "mut_density",
            kind: "candidate",
            text: artifacts.skillRule.text,
            timestamp: new Date().toISOString(),
          },
        ]
      : [];
  return {
    n,
    deck_path: `round_${n}/deck.pptx`,
    slide_images: slideImages(),
    gate1: structuredClone(artifacts.gate1),
    gate2: structuredClone(artifacts.gate2),
    gate3,
    human: { approved_slides: [], score_overrides: [], synthesized_approvals: [] },
    mutations,
    locked_slides: [],
    comments: n === 1 ? structuredClone(artifacts.comments.comments) : [],
    cost_usd: n === 1 ? 1.24 : 2.08,
    token_count: n === 1 ? 18420 : 33110,
    slide_map: structuredClone(artifacts.slideMap),
  };
}

export function createRun(briefText: string, paperName: string): StoredRun {
  const artifacts = loadFrozenArtifacts();
  const suggested = suggestBrief(briefText);
  const id = newId();
  const now = new Date().toISOString();
  const stored: StoredRun = {
    briefConfirmed: false,
    paperName,
    skillBefore: artifacts.skillRule.text,
    skillAfter: artifacts.skillRule.text,
    events: [],
    rounds: new Map(),
    run: {
      id,
      paper_id: paperName.replace(/\.pdf$/i, "") || artifacts.ledger.entries[0]?.id || "demo_trial_2024",
      brief: suggested,
      brief_text: briefText,
      blueprint_id: "msl_physician_8",
      skill_version: "v1",
      status: "created",
      rounds: [],
      best_round_n: null,
      budget_usd: 25,
      created_at: now,
      updated_at: now,
    },
  };
  store().set(id, stored);
  return stored;
}

export function getRun(id: string): StoredRun | undefined {
  return store().get(id);
}

export function updateBrief(id: string, brief: Brief): StoredRun {
  const stored = must(id);
  stored.run.brief = brief;
  stored.run.brief_text = brief.notes || stored.run.brief_text;
  stored.briefConfirmed = true;
  stored.run.updated_at = new Date().toISOString();
  return stored;
}

export function markBriefParsed(id: string, brief: Brief): StoredRun {
  const stored = must(id);
  stored.run.brief = brief;
  stored.briefConfirmed = false;
  stored.run.updated_at = new Date().toISOString();
  return stored;
}

export function startRound(id: string): { stored: StoredRun; round_n: number } {
  const stored = must(id);
  const artifacts = loadFrozenArtifacts();
  const round_n = stored.rounds.size + 1;
  stored.rounds.set(round_n, buildRound(round_n, artifacts));
  stored.run.status = "running";
  stored.run.updated_at = new Date().toISOString();
  stored.events = scriptEvents(id, round_n, artifacts);
  syncSummary(id);
  const last = stored.events.at(-1);
  setTimeout(() => finalizeRound(id, round_n), (last?.elapsed_ms ?? 0) + 50);
  return { stored, round_n };
}

export function addComments(id: string, roundN: number, comments: HumanComment[]): HumanComment[] {
  const round = mustRound(id, roundN);
  const stored = must(id);
  for (const c of comments) {
    round.comments = round.comments.filter((x) => x.id !== c.id);
    round.comments.push(c);
    if (c.scope === "always") {
      stored.skillAfter = `${stored.skillBefore}\n${c.text}`;
    }
  }
  return round.comments;
}

export function lockSlides(id: string, roundN: number, slides: number[], locked: boolean): number[] {
  const round = mustRound(id, roundN);
  const set = new Set(round.locked_slides);
  for (const s of slides) {
    if (locked) set.add(s);
    else set.delete(s);
  }
  round.locked_slides = [...set].sort((a, b) => a - b);
  syncSummary(id);
  return round.locked_slides;
}

export function addOverride(id: string, roundN: number, override: ScoreOverride): ScoreOverride {
  const round = mustRound(id, roundN);
  if (!round.human) {
    round.human = { approved_slides: [], score_overrides: [], synthesized_approvals: [] };
  }
  const delta = override.override_score - override.original_score;
  const recorded: ScoreOverride = { ...override, delta };
  round.human.score_overrides = [
    ...round.human.score_overrides.filter(
      (o) => !(o.criterion === recorded.criterion && o.slide === recorded.slide),
    ),
    recorded,
  ];
  return recorded;
}

function must(id: string): StoredRun {
  const stored = store().get(id);
  if (!stored) {
    const err = new Error("not found");
    (err as Error & { status: number }).status = 404;
    throw err;
  }
  return stored;
}

function mustRound(id: string, n: number): RoundDetail {
  const stored = must(id);
  const round = stored.rounds.get(n);
  if (!round) {
    const err = new Error("not found");
    (err as Error & { status: number }).status = 404;
    throw err;
  }
  return round;
}

export { must, mustRound };

function syncSummary(id: string): void {
  const stored = must(id);
  stored.run.rounds = [...stored.rounds.values()].map((r) => ({
    n: r.n,
    deck_score: r.gate3?.deck_score ?? null,
    gate1_passed: r.gate1?.passed ?? null,
    gate2_passed: r.gate2?.passed ?? null,
    locked_slides: r.locked_slides,
  }));
  stored.run.best_round_n = stored.run.rounds.at(-1)?.n ?? null;
}

export function finalizeRound(id: string, roundN: number): void {
  const stored = must(id);
  stored.run.status = "awaiting_review";
  syncSummary(id);
  stored.run.updated_at = new Date().toISOString();
  void roundN;
}

function scriptEvents(
  runId: string,
  roundN: number,
  artifacts: ReturnType<typeof loadFrozenArtifacts>,
): ProgressEvent[] {
  const pages = artifacts.ledger.source_pages ?? 12;
  const claims = artifacts.ledger.entries.length;
  const g1Flags = artifacts.gate1.checks.filter((c) => !c.passed || c.flagged).length;
  const g2Flags = artifacts.gate2.checks.filter((c) => !c.passed).length;
  const slides = 4;
  const started = Date.now();
  const mk = (
    event: ProgressEvent["event"],
    message: string,
    extra: Partial<ProgressEvent> = {},
    delayMs = 0,
  ): ProgressEvent => ({
    event,
    run_id: runId,
    round_n: roundN,
    message,
    timestamp: new Date(started + delayMs).toISOString(),
    elapsed_ms: delayMs,
    token_count: extra.token_count ?? Math.round(delayMs * 4),
    cost_usd: extra.cost_usd ?? delayMs / 80_000,
    ...extra,
  });

  const events: ProgressEvent[] = [
    mk("pages_parsed", `Parsed ${pages} pages`, { pages }, 400),
    mk("claims_extracted", `Extracted ${claims} claims`, { claims }, 900),
    mk("figures_extracted", "Extracted 0 figures", { figures: 0 }, 1200),
  ];
  for (let slot = 1; slot <= 9; slot += 1) {
    events.push(
      mk("blueprint_slot_filled", `Filling blueprint ${slot}/9`, { slot, slot_total: 9 }, 1200 + slot * 180),
    );
  }
  events.push(mk("rendering", "Rendering", {}, 3000));
  events.push(mk("gate1_complete", `Gate 1: ${g1Flags} flags`, { gate_flags: g1Flags }, 3400));
  events.push(mk("gate2_complete", `Gate 2: ${g2Flags} flags`, { gate_flags: g2Flags }, 3800));
  for (let slide = 1; slide <= slides; slide += 1) {
    events.push(
      mk("judging_slide", `Judging slide ${slide}/${slides}`, { slide, slide_total: slides }, 4000 + slide * 220),
    );
  }
  events.push(mk("round_complete", "Round complete", { token_count: 18420, cost_usd: 1.24 }, 5200));
  events.push(mk("awaiting_review", "Awaiting review", { token_count: 18420, cost_usd: 1.24 }, 5400));
  return events;
}
