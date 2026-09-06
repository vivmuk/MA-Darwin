import type {
  Brief,
  CreateRunResponse,
  HumanComment,
  ProgressEvent,
  RoundDetail,
  Run,
  ScoreOverride,
  StartRunResponse,
} from "./types";

const BASE = process.env.NEXT_PUBLIC_API_BASE ?? "";

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, init);
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = (await res.json()) as { detail?: string };
      if (body.detail) detail = body.detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  return (await res.json()) as T;
}

export function createRun(pdf: File, brief: string): Promise<CreateRunResponse> {
  const body = new FormData();
  body.append("pdf", pdf);
  body.append("brief", brief);
  body.append("blueprint_id", "msl_physician_8");
  body.append("skill_version", "v1");
  return req<CreateRunResponse>("/api/runs", { method: "POST", body });
}

export function getRun(runId: string): Promise<Run> {
  return req<Run>(`/api/runs/${runId}`);
}

export function parseBrief(runId: string, brief?: string): Promise<Brief> {
  return req<Brief>(`/api/runs/${runId}/parse-brief`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(brief != null ? { brief } : {}),
  });
}

export function updateBrief(runId: string, brief: Brief): Promise<Brief> {
  return req<Brief>(`/api/runs/${runId}/brief`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(brief),
  });
}

export function startRun(runId: string): Promise<StartRunResponse> {
  return req<StartRunResponse>(`/api/runs/${runId}/start`, { method: "POST" });
}

export function reiterateRun(runId: string): Promise<StartRunResponse> {
  return req<StartRunResponse>(`/api/runs/${runId}/reiterate`, { method: "POST" });
}

export function getRound(runId: string, roundN: number): Promise<RoundDetail> {
  return req<RoundDetail>(`/api/runs/${runId}/rounds/${roundN}`);
}

export function addComments(
  runId: string,
  roundN: number,
  comments: HumanComment[],
): Promise<{ run_id: string; round_n: number; comments: HumanComment[] }> {
  return req(`/api/runs/${runId}/rounds/${roundN}/comments`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ comments }),
  });
}

export function lockSlides(
  runId: string,
  roundN: number,
  slides: number[],
  locked: boolean,
): Promise<{ locked_slides: number[] }> {
  return req(`/api/runs/${runId}/rounds/${roundN}/lock`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ slides, locked }),
  });
}

export function overrideScore(
  runId: string,
  roundN: number,
  override: ScoreOverride,
): Promise<ScoreOverride> {
  return req(`/api/runs/${runId}/rounds/${roundN}/overrides`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(override),
  });
}

export function exportUrl(runId: string, roundN?: number): string {
  const q = roundN ? `?round_n=${roundN}` : "";
  return `${BASE}/api/runs/${runId}/export${q}`;
}

export function eventsUrl(runId: string): string {
  return `${BASE}/api/runs/${runId}/events`;
}

export function subscribeEvents(
  runId: string,
  onEvent: (event: ProgressEvent) => void,
  onError?: (err: Event) => void,
): () => void {
  const source = new EventSource(eventsUrl(runId));
  const handler = (raw: MessageEvent) => {
    try {
      onEvent(JSON.parse(raw.data as string) as ProgressEvent);
    } catch {
      /* ignore malformed frames */
    }
  };
  source.onmessage = handler;
  [
    "pages_parsed",
    "claims_extracted",
    "figures_extracted",
    "blueprint_slot_filled",
    "rendering",
    "gate1_complete",
    "gate2_complete",
    "judging_slide",
    "round_complete",
    "awaiting_review",
    "plateau",
    "error",
    "heartbeat",
  ].forEach((name) => source.addEventListener(name, handler as EventListener));
  if (onError) source.onerror = onError;
  return () => source.close();
}
