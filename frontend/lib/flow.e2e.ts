import { readFileSync } from "node:fs";

const BASE = "http://localhost:3000";

async function main() {
  const pdf = readFileSync("public/demo/paper.pdf");
  const form = new FormData();
  form.append("pdf", new File([pdf], "paper.pdf", { type: "application/pdf" }));
  form.append("brief", "Create an 8 slide MSL physician deck covering design, primary endpoint, and safety.");
  const created = await (await fetch(`${BASE}/api/runs`, { method: "POST", body: form })).json();
  const id = created.id as string;
  if (!id) throw new Error(`create failed: ${JSON.stringify(created)}`);

  const parsed = await (await fetch(`${BASE}/api/runs/${id}/parse-brief`, { method: "POST", body: "{}" })).json();
  if (parsed.slide_count !== 8) throw new Error("parse brief did not yield 8 slides");

  const confirmed = await (
    await fetch(`${BASE}/api/runs/${id}/brief`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(parsed),
    })
  ).json();
  if (confirmed.deck_type !== "msl_physician") throw new Error("confirm failed");

  const started = await (await fetch(`${BASE}/api/runs/${id}/start`, { method: "POST" })).json();
  if (started.round_n !== 1) throw new Error("start failed");

  await new Promise((r) => setTimeout(r, 6500));
  const round = await (await fetch(`${BASE}/api/runs/${id}/rounds/1`)).json();
  if (!round.slide_images?.length) throw new Error("no slide images");
  if (round.gate1?.passed !== true) throw new Error("expected fixture gate1 pass");
  if (round.gate2?.passed !== false) throw new Error("expected fixture gate2 fail");

  const locked = await (
    await fetch(`${BASE}/api/runs/${id}/rounds/1/lock`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ slides: [1, 2, 3, 4], locked: true }),
    })
  ).json();
  if (locked.locked_slides.length !== 4) throw new Error("lock failed");

  const comments = await (
    await fetch(`${BASE}/api/runs/${id}/rounds/1/comments`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        comments: [
          {
            id: "hc_e2e",
            slide: 3,
            x: 0.4,
            y: 0.4,
            text: "Tighten primary bullets",
            severity: "must-fix",
            criterion_tag: "information_density",
            scope: "always",
          },
        ],
      }),
    })
  ).json();
  if (!comments.comments.some((c: { id: string }) => c.id === "hc_e2e")) throw new Error("comment missing");

  const override = await (
    await fetch(`${BASE}/api/runs/${id}/overrides`.replace("overrides", "rounds/1/overrides"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        criterion: "visual_hierarchy",
        original_score: 10,
        override_score: 12,
        delta: 2,
        rationale: "reviewer",
      }),
    })
  ).json();
  if (override.delta !== 2) throw new Error("override delta not stored");

  const exp = await fetch(`${BASE}/api/runs/${id}/export?round_n=1`);
  if (exp.status !== 403) throw new Error(`export should be 403, got ${exp.status}`);

  const runAfter = await (await fetch(`${BASE}/api/runs/${id}`)).json();
  if (runAfter.status !== "awaiting_review") {
    throw new Error(`expected awaiting_review, got ${runAfter.status}`);
  }
  const next = await (await fetch(`${BASE}/api/runs/${id}/reiterate`, { method: "POST" })).json();
  if (next.round_n !== 2) throw new Error(`reiterate did not open round 2: ${JSON.stringify(next)}`);

  console.log("e2e ok", { id, round_n: started.round_n, next: next.round_n, images: round.slide_images.length });
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
