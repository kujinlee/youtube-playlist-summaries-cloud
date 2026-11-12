Reviewed head: 008b9950

# PR #559 (agenda group titles) — round 2 coordinator

REVIEW GAP: claude — alternation (round 1 ran both halves; round 2 is the Codex half).
Codex: NOT CONVERGED, 1 LOW. No BLOCKER, HIGH or MEDIUM. All three mandate checks came back clean: the only
caller (`agenda_lines`) gets byte-identical lines; the JSON merge keeps 364 unique names, the pinned count; each of the
five changed mutations has one anchor and is killed by its named case. Self-test 476/476.

| Finding | Disposition |
|---|---|
| Codex L1 — nothing pins `::first-letter`; reverting to `text-transform:capitalize` passes 476/476 | ACCEPTED, not folded: a cosmetic CSS rule on one page. Folding it changes guarded code and would need a third round, for a defect a reader sees at a glance |
