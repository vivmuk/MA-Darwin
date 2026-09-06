import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { suggestBrief } from "./parse-brief";

describe("suggestBrief", () => {
  it("reads slide count from the freeform brief", () => {
    const brief = suggestBrief("Create an 8 slide MSL physician deck covering design.");
    assert.equal(brief.slide_count, 8);
    assert.equal(brief.deck_type, "msl_physician");
    assert.equal(brief.purpose, "MSL presentation");
    assert.match(brief.audience, /physician/i);
  });

  it("defaults slide_count to 8 when unspecified", () => {
    const brief = suggestBrief("Medical to medical exchange on HFrEF.");
    assert.equal(brief.slide_count, 8);
  });
});
