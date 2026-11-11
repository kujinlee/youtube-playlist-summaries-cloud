# Round 3 — `review-tooling-121-182` (PR #439) — coordinator — NOT CONVERGED (Claude); THRASHING armed, the route moves to SPLIT

REVIEW GAP: codex — alternation; one reviewer per round in rounds 2+, the owner's 2026-10-28 answer to backlog #339.

```yaml
round: 3
fixes_nontrivial: true
subject: review-tooling-121-182
halves:
  codex: "GAP: alternation, one reviewer per round in rounds 2+ (backlog #339)"
  claude: ran
findings:
  - {id: B1, severity: Blocking, aim: deliverable, fix_induced: false, component: gap-reader, disposition: filed}
  - {id: M2, severity: High, aim: deliverable, fix_induced: true, component: gap-reader, disposition: filed}
  - {id: M3, severity: High, aim: deliverable, fix_induced: false, component: codex-review, disposition: fixed}
  - {id: m4, severity: Low, aim: instrument, fix_induced: true, component: mutation-manifest, disposition: filed}
  - {id: m5, severity: Low, aim: deliverable, fix_induced: true, component: gap-reader, disposition: filed}
  - {id: m6, severity: Low, aim: deliverable, fix_induced: true, component: gap-reader, disposition: filed}
```

The Claude half reviewed `ffff1e0e`. The coordinator reproduced B1 by hand: `gap_reasons()` on THIS subject's own round-2 Codex half returns `{'claude': 'quota', 'codex': 'example only'}`, i.e. the reviewer's quoted inputs read as declarations. 431 of 887 review halves have no `## ` heading, so for them "the preamble" is the whole document.

**Thrashing:** the gap-reader component carries fix-induced findings in round 2 (X2) and round 3 (M2, m5, m6). That is the arming condition, so the architecture review is `docs/reviews/architecture-review-2026-10-29-gap-reader.md`. Its finding: a review HALF quotes declarations as its evidence, so no rule over a half's text (grammar in round 1, position in round 2) can tell a declaration from a quotation. Each round only moved the line.

**SPLIT** (decision log): backlog #121's wrapper change ships alone in this PR, with M3 fixed: a case-insensitive spelling of `docs/reviews` is refused. The backlog #182 gap reader is REMOVED from this PR, back to master's behaviour, and returns to its row with the review's direction. The `disposition: filed` findings above belong to that removed code.
