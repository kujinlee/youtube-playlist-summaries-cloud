# Round 4 — `backlog-698` — coordinator — at the round cap: one constructed `<noscript>` disguise FILED, not folded

```yaml
round: 4
fixes_nontrivial: false
subject: backlog-698
halves:
  codex: ran
  claude: gap
findings:
  - {id: X1, severity: Major, aim: deliverable, fix_induced: false, component: hidden-text, disposition: filed}
```

Codex reviewed bbf85d98: [`codex/backlog-698-r4-codex.md`](../codex/backlog-698-r4-codex.md). Its verdict is NOT CONVERGED, with 1 MAJOR, which is not a BLOCKER.

REVIEW GAP: claude — alternation (round 4)

**What held**, in a full external clone:
- 73/73 self-tests pass, and `--out` then `--check` both pass.
- Three new mutations each fail on their named case: end-tag closure, implicit paragraph closure, and NFKC in place of NFKD.
- The real-fragment normalisation invariant holds.
- Constructed probes using a comment, a `<template>`, the `hidden` attribute and a hidden void element are each refused.

**X1 (MAJOR, not fix-induced, not a BLOCKER) — FILED as backlog #708.**
- A group-D fragment split around `<noscript>distractor</noscript>` passes, because every reading keeps the `<noscript>` contents.
- Codex built this input itself. No real quote ships this way in today's tree.
- From round 4, findings are FILED unless a BLOCKER (`review-method.md` §0 Q4c).

**Not thrashing.** The finding is a construct that neither the counter nor the stack ever modelled, not a defect in the round-3 stack. Its `fix_induced` is false, so the hidden-text component has no two consecutive fix-induced rounds.

The review stops here. The decision-log row for the element-stack redesign records the bet as LOST at the cap, and stopped.
