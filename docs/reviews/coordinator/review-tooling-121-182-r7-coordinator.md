# Round 7 — `review-tooling-121-182` (PR #439, backlog #121) — coordinator — a SECOND regression against master; parity by construction

REVIEW GAP: claude — alternation; one reviewer per round in rounds 2+, the owner's 2026-10-28 answer to backlog #339.

```yaml
round: 7
fixes_nontrivial: true
subject: review-tooling-121-182
halves:
  codex: ran
  claude: "GAP: alternation, one reviewer per round in rounds 2+ (backlog #339)"
findings:
  - {id: X1, severity: Blocking, aim: deliverable, fix_induced: true, component: out-path, disposition: fixed}
```

Codex reviewed `45286165`. A symlink NESTED inside `docs/reviews` (`A/docs/reviews/nested -> /tmp/external`, then `--out A/docs/reviews/nested/victim.md`) is refused by master and accepted here: the victim is overwritten. Resolving `--out` first erases its ROUTE through `docs/reviews`, and adding the resolved review root (r6) protects only the top level. Every other comparison against master held: a top-level review symlink inside or outside the checkout, case and NFD variants, hard links, late file symlinks, and ordinary scratch paths.

**Thrashing in `out-path`:** r6 X1 and r7 X1 are both caused by the previous fold, in one component. The cause is structural. Each fold re-derived master's refusal from a different resolution, and every re-derivation dropped a route master covered.

**Redesign: parity BY CONSTRUCTION.** Keep master's `out_location_refusal` logic VERBATIM, as its own function, and refuse when EITHER it or the identity rule refuses. This branch can then only refuse MORE than master, never less, whatever the path shape. A case runs a table of inputs through both master's function and the combined rule, and asserts that every refusal by master is also a refusal here.
