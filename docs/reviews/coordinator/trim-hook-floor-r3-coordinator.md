# Round 3 — `trim-hook-floor` — coordinator — ⟳ NOT CONVERGED (Claude); SPLIT

REVIEW GAP: codex — alternation, one reviewer per round in rounds 2+ (backlog #339).

```yaml
round: 3
fixes_nontrivial: true
subject: trim-hook-floor
halves:
  codex: gap
  claude: ran
findings:
  - {id: R3-1, severity: Blocking, aim: deliverable, fix_induced: true, component: owner-relevance-inference, disposition: fixed}
  - {id: R3-2, severity: Blocking, aim: deliverable, fix_induced: false, component: print-size-cap, disposition: fixed}
  - {id: R3-3, severity: High, aim: deliverable, fix_induced: false, component: owner-relevance-inference, disposition: filed}
  - {id: R3-4, severity: Medium, aim: deliverable, fix_induced: true, component: print-size-cap, disposition: fixed}
  - {id: R3-5, severity: Medium, aim: deliverable, fix_induced: true, component: migration, disposition: fixed}
  - {id: R3-6, severity: Medium, aim: deliverable, fix_induced: true, component: size-bound-test, disposition: fixed}
  - {id: R3-7, severity: Low, aim: deliverable, fix_induced: false, component: print-size-cap, disposition: filed}
```

Claude on `98d024b4` (`docs/reviews/claude/trim-hook-floor-r3-claude.md`). The bet of r2 ("owner relevance is DECLARED, never
inferred; every owner entry is printed whole by every reader") met its named failure observation: **R3-1** the only writer
stored `routine` for owner text typed without `--kind`, so the declared field bypassed the wide fallback; **R3-2** the
in-flight block had no size cap (18 owner entries pass the harness's 10,000 characters); **R3-3** goal-tree still decides by the
text prefix; **R3-4** the compaction print dropped owner entries after its cut without naming them; **R3-5** `--override`
dropped what it could not use; **R3-6** the floor case and the fallback case passed for reasons unrelated to the real subject;
**R3-7** both prints carry the owner entries.

**Route: SPLIT.** The block is capped and bounded; owner-wait first, then owner-instruction, then routine titles; what does not
fit is NAMED by id with the absolute path (not "the whole ledger printed again": that is also unbounded). R3-3 and R3-7 are
filed as backlog 418, a third reader and a cost that belong to other files.

**Fold.** R3-1: `--add` with no `--kind` stores `guess_kind` (the wide reading). R3-2: `BLOCK_CAP` 8,000 for the whole compact
block, the PR list and the problems bounded, the owner notice reserved before an entry is accepted. R3-4: the print's cut names
every owner decision it took. R3-5: an `--override` with no `=`, naming no entry or a declared one, and `--apply`/`--override`/
`--kind` outside their mode, are refused with rc 2. R3-6: a real-ledger-shape case (12 owner, 11 routine, 9 PRs), the 25%
case restated as holding only for its fixture, and the writer driven through `main(--add)`. A case that passed for an ambient
reason was found while folding: the bad-override migration case ran after `--apply`, when the entry was already declared.
