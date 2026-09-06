import { readFileSync } from "node:fs";
import { join } from "node:path";
import type { Gate1Result, Gate2Result, Gate3Result, HumanComment, SlideMap } from "../types";

type CommentsFile = { run_id: string; round_n: number; comments: HumanComment[] };

function fixturesDir(): string {
  return join(process.cwd(), "..", "backend", "tests", "fixtures");
}

function loadJson<T>(name: string): T {
  const raw = readFileSync(join(fixturesDir(), name), "utf8");
  return JSON.parse(raw) as T;
}

export function loadFrozenArtifacts() {
  return {
    gate1: loadJson<Gate1Result>("gate1.json"),
    gate2: loadJson<Gate2Result>("gate2.json"),
    gate3: loadJson<Gate3Result>("gate3.json"),
    slideMap: loadJson<SlideMap>("slide_map.json"),
    comments: loadJson<CommentsFile>("comments.json"),
    skillRule: loadJson<{ id: string; text: string }>("skill_rule.json"),
    ledger: loadJson<{ entries: { id: string }[]; source_pages?: number }>("ledger.json"),
  };
}
