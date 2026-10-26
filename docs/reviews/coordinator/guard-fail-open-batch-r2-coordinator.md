# Round 2 — `guard-fail-open-batch` — coordinator — ⟳ NOT CONVERGED (bet LOST); REDESIGN

```yaml
round: 2
fixes_nontrivial: true
subject: guard-fail-open-batch
halves:
  codex: ran
  claude: skipped
findings:
  - {id: XM1, severity: Medium, aim: deliverable, fix_induced: true, component: handoff-hook, disposition: fixed}
  - {id: XM2, severity: Medium, aim: deliverable, fix_induced: false, component: malformed-input, disposition: declined}
  - {id: XM3, severity: Medium, aim: deliverable, fix_induced: false, component: malformed-input, disposition: declined}
  - {id: XL4, severity: Low, aim: deliverable, fix_induced: true, component: ci-watched, disposition: fixed}
  - {id: XL5, severity: Low, aim: deliverable, fix_induced: false, component: handoff-hook, disposition: fixed}
  - {id: XL6, severity: Low, aim: deliverable, fix_induced: false, component: malformed-input, disposition: declined}
  - {id: XL7, severity: Low, aim: deliverable, fix_induced: false, component: malformed-input, disposition: declined}
  - {id: XL8, severity: Low, aim: deliverable, fix_induced: false, component: malformed-input, disposition: declined}
  - {id: XL9, severity: Low, aim: deliverable, fix_induced: false, component: prose, disposition: fixed}
```

REVIEW GAP: claude — round 2 alternates to the Codex half on the final tree (`review-method.md`, *The
protocol*, step 4; backlog #339).

`X` = Codex, tree `aa631d9f`. Every touched suite green. **The bet — no Medium+, nothing fold-induced — is LOST.**

- **XM1 (fold-induced) + XL5 (residual, same root) — fixed by REDESIGN:** the r1 hook told a checker verdict from an
  interpreter failure by matching the checker's ENGLISH, so a rewording downgraded a real block to a warning; and a
  wrapper exiting 0 without running the checker passed. Now the checker writes a RECEIPT (`--receipt FILE`, 0/1/2)
  once it reaches a verdict, and the hook acts on the receipt alone — no receipt is a warning. Two new hook cases
  (a reworded checker still blocks; a fake-OK wrapper warns) and one mutation (no receipt written).
- **XL4 (fold-induced, fixed):** a blind `--clear` said "removed NOTHING" after tidying the legacy file.
- **XM2, XM3, XL6, XL7, XL8 (pre-existing, declined here — FILED as backlog #357):** undecodable transcript, a
  non-object envelope, an undecodable skill, a permission-denied sentinel, a malformed check row. Filed, as the stop
  rule written before this round requires.
- **XL9 (fixed):** the PR body's "each now says CANNOT RUN" is narrowed.

Route: REDESIGN (decision-log row written before the change). Round 3 is the last, a confirmation round.
