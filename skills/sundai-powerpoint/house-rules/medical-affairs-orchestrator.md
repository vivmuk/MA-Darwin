# House rules — `medical-affairs-orchestrator`

Rules here override the defaults in `skills/medical-affairs-orchestrator/SKILL.md`.
See [README.md](README.md) for how to write a good one.

This file is the right place for routing decisions specific to your
organisation — which team owns which job, what must never be attempted by an
agent, and where a request should be handed to a person instead.

## Seeded examples

- Never route a medical information enquiry to any skill other than
  `medical-information-response`, and never answer one that touches an
  unapproved use. Hand those to `[named team]` untouched.
- Announce the stages out loud. Our reviewers have said repeatedly that seeing
  what the agent did and did not check is what makes the output trustworthy —
  a silent answer gets rejected even when it is correct.
- Any objective that would produce externally facing material must end with
  `mlr-review-readiness`, without exception, including drafts described as
  "just for internal discussion". Internal drafts become external material more
  often than anyone plans for.
- Stop and ask a person when the request involves a named patient, a specific
  prescribing decision, or a regulatory commitment. These are outside what this
  library is for.

## YOUR RULES — ADD BELOW THIS LINE
