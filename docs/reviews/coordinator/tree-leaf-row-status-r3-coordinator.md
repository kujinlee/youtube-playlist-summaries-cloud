# Round 3 — `tree-leaf-row-status` — coordinator — NOT CONVERGED (Claude): a several-row leaf and a list tail

Claude reviewed d237dfe7 (the round-2 fold): `docs/reviews/claude/tree-leaf-row-status-r3-claude.md`, 1 MAJOR and
2 MINOR. The Codex half is a gap by alternation; round 2 was Codex's.

REVIEW GAP: codex — alternation.

No round-3 finding was caused by round 2's fix (d237dfe7); M1 came in with round 1's list matcher (4c191f00). So the
fix-induced run in `goal-tree-leaf` is one round (r2), not two, and Phase 6 is NOT armed.

```yaml
round: 3
fixes_nontrivial: true
subject: tree-leaf-row-status
halves:
  codex: gap
  claude: ran
findings:
  - {id: M1, severity: Major, aim: deliverable, fix_induced: false, component: goal-tree-leaf, disposition: fixed}
  - {id: m2, severity: Minor, aim: deliverable, fix_induced: false, component: goal-tree-leaf, disposition: filed}
  - {id: m3, severity: Minor, aim: deliverable, fix_induced: false, component: goal-tree-leaf, disposition: filed}
```

| # | Severity | Finding | Disposition |
|---|---|---|---|
| M1 | MAJOR | The round-2 gate is per row, but a leaf combines rows with `any`: a leaf naming backlog #23 and #46, only #23 ✅, reads merged via `(backlog #23, backlog #46) (#537)`. | **Fixed.** A leaf takes a list tail as its merge only when EVERY live row is ✅ in its Status cell. Case "⭐ backlog #689 r3 M1" (one subject, three cell sets); a mutation (`leaf_closed = _cr`) turns it red at 592/593, control 593/593; pin 519 → 520. |
| m2 | MINOR | A list tail credits a PR that named a ✅ row, not the PR that made it ✅ (backlog #231: PR #590 credited, PR #593 wrote the ✅). | **Filed** as backlog #690 — the cap is next round, and it is not fix-induced. |
| m3 | MINOR | A tail with a non-row item (`(backlog #N, slice 2)`) is missed, so backlog #544 and #499 read ✅ by cell with no merge; an open row's leaf says "no PR names it yet" while its agenda step names the PR. | **Filed** as backlog #690 (origin/master reads the same). |
