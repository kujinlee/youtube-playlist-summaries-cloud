# Round 2 — `running-vs-owed` — coordinator — NOT CONVERGED, all three folded

REVIEW GAP: claude — alternation, and weekly usage at 97% (stop 98.4%). Codex: `docs/reviews/codex/running-vs-owed-r2-codex.md`, on `3026c9b0`.

```yaml
round: 2
fixes_nontrivial: true
subject: running-vs-owed
halves:
  codex: ran
  claude: gap
findings:
  - {id: H1, severity: High, aim: deliverable, fix_induced: true, component: agenda-digest, disposition: fixed}
  - {id: M1, severity: Medium, aim: deliverable, fix_induced: true, component: agenda-digest, disposition: fixed}
  - {id: L1, severity: Low, aim: test, fix_induced: false, component: agenda-digest, disposition: fixed}
```

H1 and M1 are both left by r1's fold, which recorded `open_prs` but stopped short of using them everywhere.

- **H1** — the admission filter now reads `open_prs` too: a thread with an open PR is in flight whatever its worst
  state, with or without a ledger entry. ⚠ This changes the `--print` `now:` line for exactly that snapshot (the thread
  was missing there too); every other snapshot's text is unchanged. Case through `derive`; mutation.
- **M1** — items merge when they share a label or ANY open PR (a union, and an entry sharing with two items joins
  them), replacing the first-PR `key`. Two cases; two mutations; three older mutations re-bound.
- **L1** — the two-PR case kills a `prs[:1]` mutant; a case and mutation for the undeclared PR's integer guard.
