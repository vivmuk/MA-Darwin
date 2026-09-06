import { NextRequest, NextResponse } from "next/server";
import { suggestBrief } from "@/lib/parse-brief";
import { exportBlockers } from "@/lib/export-blockers";
import {
  addComments,
  addOverride,
  createRun,
  finalizeRound,
  getRun,
  lockSlides,
  markBriefParsed,
  mustRound,
  startRound,
  updateBrief,
} from "@/lib/server/store";
import type { Brief, HumanComment, ProgressEvent, ScoreOverride } from "@/lib/types";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

function json(data: unknown, status = 200) {
  return NextResponse.json(data, { status });
}

function notFound() {
  return json({ detail: "not found" }, 404);
}

function conflict(detail: string) {
  return json({ detail }, 409);
}

async function parsePath(params: Promise<{ path: string[] }>): Promise<string[]> {
  return (await params).path;
}

export async function GET(req: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  const parts = await parsePath(ctx.params);
  if (parts.length === 1 && parts[0] === "health") {
    return json({ status: "ok" });
  }
  if (parts[0] !== "runs" || parts.length < 2) return notFound();
  const runId = parts[1];
  const stored = getRun(runId);
  if (!stored) return notFound();

  if (parts.length === 2) {
    return json(stored.run);
  }
  if (parts[2] === "events") {
    return sse(stored.events, () => finalizeRound(runId, stored.rounds.size));
  }
  if (parts[2] === "export") {
    const roundN = Number(req.nextUrl.searchParams.get("round_n") || stored.run.best_round_n || 1);
    const round = stored.rounds.get(roundN);
    const blockers = exportBlockers(round ?? null, round?.slide_images.length ?? 0);
    const kind = blockers.length ? "draft" : "compliant";
    return new NextResponse("PK draft-pptx", {
      status: 200,
      headers: {
        "Content-Type": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "Content-Disposition": `attachment; filename="Round_${roundN}_M2M_${kind}.pptx"`,
        "X-Darwin-Export": kind,
        "X-Darwin-Export-Reason": blockers.join(" "),
      },
    });
  }
  if (parts[2] === "rounds" && parts.length === 4) {
    const n = Number(parts[3]);
    try {
      return json(mustRound(runId, n));
    } catch {
      return notFound();
    }
  }
  return notFound();
}

export async function POST(req: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  const parts = await parsePath(ctx.params);

  if (parts.length === 1 && parts[0] === "runs") {
    const form = await req.formData();
    const brief = String(form.get("brief") ?? "");
    const pdf = form.get("pdf");
    const paperName = pdf instanceof File ? pdf.name : "paper.pdf";
    const stored = createRun(brief, paperName);
    return json(
      {
        id: stored.run.id,
        status: stored.run.status,
        paper_id: stored.run.paper_id,
        blueprint_id: stored.run.blueprint_id,
        skill_version: stored.run.skill_version,
      },
      201,
    );
  }

  if (parts[0] !== "runs" || parts.length < 3) return notFound();
  const runId = parts[1];
  const stored = getRun(runId);
  if (!stored) return notFound();

  if (parts[2] === "parse-brief") {
    const body = (await req.json().catch(() => ({}))) as { brief?: string };
    const text = body.brief ?? stored.run.brief_text ?? "";
    const brief = suggestBrief(text);
    markBriefParsed(runId, brief);
    return json(brief);
  }

  if (parts[2] === "start" || parts[2] === "reiterate") {
    if (parts[2] === "start" && stored.run.status !== "created") {
      return conflict("run already started");
    }
    if (parts[2] === "reiterate" && stored.run.status !== "awaiting_review") {
      return conflict("reiterate requires awaiting_review");
    }
    const { round_n } = startRound(runId);
    return json(
      {
        run_id: runId,
        round_n,
        status: "running",
        events_url: `/api/runs/${runId}/events`,
      },
      202,
    );
  }

  if (parts[2] === "rounds" && parts.length === 5) {
    const n = Number(parts[3]);
    const action = parts[4];
    try {
      mustRound(runId, n);
    } catch {
      return notFound();
    }
    if (action === "comments") {
      const body = (await req.json()) as { comments: HumanComment[] };
      const comments = addComments(runId, n, body.comments);
      return json({ run_id: runId, round_n: n, comments });
    }
    if (action === "lock") {
      const body = (await req.json()) as { slides: number[]; locked: boolean };
      return json({ locked_slides: lockSlides(runId, n, body.slides, body.locked) });
    }
    if (action === "overrides") {
      const body = (await req.json()) as ScoreOverride;
      return json(addOverride(runId, n, body));
    }
  }

  return notFound();
}

export async function PUT(req: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  const parts = await parsePath(ctx.params);
  if (parts[0] !== "runs" || parts[2] !== "brief") return notFound();
  const stored = getRun(parts[1]);
  if (!stored) return notFound();
  let brief: Brief;
  try {
    brief = (await req.json()) as Brief;
  } catch {
    return json({ detail: "invalid brief JSON" }, 400);
  }
  return json(updateBrief(parts[1], brief).run.brief);
}

function sse(events: ProgressEvent[], onDone: () => void): Response {
  const encoder = new TextEncoder();
  let i = 0;
  const stream = new ReadableStream({
    async start(controller) {
      const start = Date.now();
      for (const ev of events) {
        const wait = Math.max(0, ev.elapsed_ms - (Date.now() - start));
        if (wait) await new Promise((r) => setTimeout(r, wait));
        const frame = `event: ${ev.event}\ndata: ${JSON.stringify(ev)}\n\n`;
        controller.enqueue(encoder.encode(frame));
        i += 1;
      }
      onDone();
      controller.close();
    },
  });
  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream; charset=utf-8",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
    },
  });
}
