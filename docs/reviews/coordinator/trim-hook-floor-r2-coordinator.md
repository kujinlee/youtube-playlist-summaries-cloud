# Round 2 — `trim-hook-floor` — coordinator — ⟳ NOT CONVERGED (Codex); REDESIGN

REVIEW GAP: claude — alternation, one reviewer per round in rounds 2+ (backlog #339).

```yaml
round: 2
fixes_nontrivial: true
subject: trim-hook-floor
halves:
  codex: ran
  claude: gap
findings:
  - {id: R2-1, severity: Blocking, aim: deliverable, fix_induced: false, component: owner-relevance-inference, disposition: fixed}
  - {id: R2-2, severity: High, aim: deliverable, fix_induced: false, component: owner-relevance-inference, disposition: fixed}
  - {id: R2-3, severity: High, aim: deliverable, fix_induced: false, component: owner-relevance-inference, disposition: fixed}
  - {id: R2-4, severity: Medium, aim: deliverable, fix_induced: true, component: size-bound-test, disposition: fixed}
```

Codex on `9d76aef1`. **R2-1** the compact block still hides real owner instructions: `build-402`'s "implement when
convenient" falls outside the 120-character title, and four phrasings of a wait (lower-case marker, `NOTE:` prefix, an
`OWNER hh:mm:` answer in `on_done`, `NOTE: (card when back)`) are all hidden. **R2-2** the snapshot capture still selects
by the strict marker, so nine entries the print keeps vanish from the digest. **R2-3** "whole" owner sections are built
from text already cut at 160 and 120 characters, and the `/compact instructions` are cut at 300. **R2-4** the approval
case passes with either field's check removed, and the 25% assertion used twenty long routine entries.

**Root cause, one for all four:** the code INFERS owner relevance from free text, and every widening of the matcher is
a guess about phrasing the next real entry will not use. **Route: REDESIGN.** Owner relevance is DECLARED in a `kind`
field on each ledger entry (`owner-wait`, `owner-instruction`, `routine`); every reader prints an owner kind whole and
trims only `routine`. The prose heuristic survives only as the fallback for an entry that has no `kind`, and as the
one-time migration's proposal for the existing ledger.
