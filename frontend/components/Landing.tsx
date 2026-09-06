"use client";

import Link from "next/link";

const STEPS = [
  { n: "01", title: "Upload one PDF", body: "Jay’s ledger keeps page-level claims. No flattened blob." },
  { n: "02", title: "Venice plans", body: "Claude Opus 4.8 returns SlidePlan JSON. It never writes a .pptx." },
  { n: "03", title: "Skill writes", body: "sundai-powerpoint scripts build editable OOXML charts on Railway." },
  { n: "04", title: "You evaluate", body: "Lock your notes. Then see the AI evaluation." },
  { n: "05", title: "Mutate the skill", body: "Suggestions land in a new sundai-powerpoint lineage version." },
  { n: "06", title: "Keep the winner", body: "A/B the decks. The chosen skill becomes current." },
];

export function Landing() {
  return (
    <div className="min-h-svh bg-sand text-ink">
      <header className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-5 py-4">
        <div>
          <p className="font-display text-xl font-bold tracking-tight">
            MA<span className="text-pink">·</span>Darwin
          </p>
          <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-muted">Launched 9.6.2026</p>
        </div>
        <Link
          href="/app"
          className="rounded-md bg-teal px-4 py-2 text-sm font-extrabold text-sand shadow-[2px_3px_0_#cbd9d0] hover:-translate-y-0.5"
        >
          Demo
        </Link>
      </header>

      <main className="mx-auto max-w-6xl px-5 pb-16">
        <section className="mb-8 mt-4 max-w-xl">
          <h1 className="font-display text-[clamp(28px,4vw,48px)] leading-[1.08] tracking-tight">
            An agent skill can adapt. But is it <em className="text-pink not-italic underline decoration-wavy decoration-2 underline-offset-8">evolving</em>?
          </h1>
          <p className="mt-4 text-sm leading-7 text-muted">
            One PDF → one M2M deck, driven by <code className="rounded bg-white px-1.5 py-0.5 text-teal">sundai-powerpoint/SKILL.md</code>.
            Revise the skill, render slides, keep what works.
          </p>
        </section>

        <div className="grid gap-4 rounded-xl border-2 border-teal/40 bg-paper p-5 shadow-[5px_6px_0_#d6ded3] md:grid-cols-2">
          <div className="relative overflow-hidden rounded-lg bg-grid p-6">
            <div className="mx-auto flex h-40 w-40 flex-col items-center justify-center rounded-full bg-teal text-center text-sand shadow-[0_0_0_6px_#28584f]">
              <strong className="font-display text-lg">sundai-powerpoint</strong>
              <small className="mt-2 max-w-[10rem] text-[10px] text-sand/80">Agent skill · SKILL.md</small>
            </div>
            <p className="mt-6 text-center font-display text-xs text-muted">LINEAGE A · ITERATION 01</p>
          </div>
          <div>
            <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-muted">Darwinian audit</p>
            <h2 className="font-display text-2xl">What exists today?</h2>
            <ul className="mt-4 space-y-2">
              {STEPS.map((step) => (
                <li key={step.n} className="rounded-md border border-teal/25 bg-white px-3 py-2">
                  <p className="font-display text-[11px] text-pink">{step.n}</p>
                  <p className="font-display text-sm text-teal">{step.title}</p>
                  <p className="text-xs text-muted">{step.body}</p>
                </li>
              ))}
            </ul>
          </div>
        </div>

        <p className="mt-6 text-center font-display text-xs text-muted">
          Now: one skill lineage · Next: a population of skills
        </p>
      </main>
    </div>
  );
}
