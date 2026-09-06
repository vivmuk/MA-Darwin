# House rules (objective, non-negotiable)

- Fair balance: `safety` and `limitations_relevance` roles must be present and non-empty.
- Secondary, exploratory, and post-hoc results must be explicitly labelled as such.
- No comparative or superiority language unless a ledger claim of class
  `primary_endpoint` from a head-to-head design supports it.
- Promotional blocklist terms from `config/compliance.yaml` are forbidden.
- Do not generalize beyond the ledger's stated population.
- A references slide is always appended and does not count against `slide_count`.
- Any `synthesized` claim requires explicit human approval before export.

## Proposed in v2 — chart and density gates

- Require at least one editable OOXML chart or data visualization on every
  quantitative slide AND on the Backup slide whenever it restates numeric
  endpoints; a backup slide that references data must include ≥1 chart, not
  text-only Q&A.
- Set a minimum visual-density rule: no quantitative slide may exceed 6 bullets
  without also carrying a chart or table; if a slide has >3 numeric claims, a
  chart is mandatory.
- Add a deck-level minimum: the 8-slide MSL deck must contain at least 2
  editable charts total (evidence slide + one other), enforced in validate.
