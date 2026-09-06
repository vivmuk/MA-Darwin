import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { exportBlockers, pinPosition } from "./export-blockers";
import type { RoundDetail } from "./types";

const base: RoundDetail = {
  n: 1,
  slide_images: [],
  mutations: [],
  locked_slides: [],
  comments: [],
  gate1: { gate: "gate1", passed: true, checks: [] },
  gate2: {
    gate: "gate2",
    passed: false,
    checks: [{ name: "min_font_size", passed: false, message: "Body text below 14pt on slide 3" }],
  },
};

describe("exportBlockers", () => {
  it("lists Gate 2 failure and unlocked slides", () => {
    const blockers = exportBlockers(base, 4);
    assert.ok(blockers.some((b) => b.includes("Gate 2")));
    assert.ok(blockers.some((b) => b.includes("Slides not locked")));
  });

  it("is empty when gates pass and every slide is locked", () => {
    const ready: RoundDetail = {
      ...base,
      gate2: { gate: "gate2", passed: true, checks: [] },
      locked_slides: [1, 2, 3, 4],
    };
    assert.deepEqual(exportBlockers(ready, 4), []);
  });
});

describe("pinPosition", () => {
  it("keeps unit-square comments as percents", () => {
    const pos = pinPosition(0.4, 0.55);
    assert.ok(pos);
    assert.equal(pos.left, "40%");
    assert.equal(pos.top, "55%");
  });

  it("maps LayoutSpec inches onto the 13.333 x 7.5 canvas", () => {
    const pos = pinPosition(1, 2.5);
    assert.ok(pos);
    assert.equal(pos.left, "7.5%");
    assert.equal(pos.top, "33.33%");
  });
});
