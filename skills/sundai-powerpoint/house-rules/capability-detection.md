# House rules — `capability-detection`

Rules here override the defaults in `skills/capability-detection/SKILL.md`.
See [README.md](README.md) for how to write a good one.

## Seeded examples

- Never deliver a degraded output to an external audience without flagging it to
  the requester first. Internally, markdown instead of a deck is fine; externally
  it is a conversation to have before, not after.
- Our deliverables must be PDF for anything leaving the department. If PDF
  generation is unavailable, produce HTML and say explicitly that it needs
  printing to PDF — do not send the HTML on.
- When the network is unavailable, every reference in the output must carry
  `[UNVERIFIED]` inline, not just a note at the bottom. Our reviewers read the
  reference list first and a footnote gets missed.

## YOUR RULES — ADD BELOW THIS LINE
