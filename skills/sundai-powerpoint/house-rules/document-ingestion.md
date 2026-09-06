# House rules — `document-ingestion`

Rules here override the defaults in `skills/document-ingestion/SKILL.md`.
See [README.md](README.md) for how to write a good one.

## Seeded examples

- Never process a document containing patient-identifying information through
  an AI system. Stop, tell the requester, and route to `[named team]`.
- Any number taken from a PDF table must be verified by eye against the rendered
  document before it appears in a deliverable. Column misalignment turns a
  hazard ratio into a CI bound and it is silent.
- Run the safety scan on every advisory board transcript and field export, not
  just the ones labelled as safety-related.

## YOUR RULES — ADD BELOW THIS LINE
