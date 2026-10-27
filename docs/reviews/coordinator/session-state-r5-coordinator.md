# Round 5 — `session-state` — coordinator — ⟳ NOT CONVERGED on prose only; fixed

```yaml
round: 5
fixes_nontrivial: false
subject: session-state
halves:
  codex: skipped
  claude: ran
findings:
  - {id: CL1, severity: Low, aim: deliverable, fix_induced: true, component: prose, disposition: fixed}
  - {id: CL2, severity: Low, aim: deliverable, fix_induced: true, component: prose, disposition: fixed}
  - {id: CL3, severity: Low, aim: deliverable, fix_induced: false, component: prose, disposition: fixed}
```

REVIEW GAP: codex — round 5 is a confirmation round on the Claude half, scoped to `fb8ade4a..1e973222`
(`review-method.md`, *The protocol*, step 4; backlog #339).

`C` = Claude. CONFIRMED: the `scripts/session-state.py` change is docstring-only (old and new parse to identical code
with docstrings removed); the manifest is unchanged; 36/36; 17/17 mutations killed by their named cases on a temp copy;
the ledger erasure by `--add` and the empty-rollup `NO CHECKS` both reproduce; the decision-log rows, backlog #362 and
the dashboard are accurate; the PR body no longer mentions a fetch.

- **CL1 (fixed):** "the next `--add`/`--done` REPLACES it" was false for `--done`, which writes nothing and reports a
  recorded id as "no such id" — corrected in the docstring, the r4 record, the split row's `observed`, and backlog #369,
  whose falsifier now covers `--done` too.
- **CL2 (fixed):** "missing or non-list" overstated XP2 — only a missing or EMPTY-valued rollup reads as `NO CHECKS`.
- **CL3 (fixed):** the PR title still said "derived from git and gh".

All three are prose; the route stays DEFER. A Codex confirmation round reviews this commit before merge.
