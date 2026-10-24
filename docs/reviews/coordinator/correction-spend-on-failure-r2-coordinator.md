# Round 2 — `correction-spend-on-failure` — coordinator — ❌ NOT CONVERGED (2 High, 1 Medium, 2 Low)

```yaml
round: 2
fixes_nontrivial: true
subject: correction-spend-on-failure
halves:
  codex: ran
  claude: ran
findings: [split-loses-cents-near-limit, inflight-abort-unmetered, race-unbounded-understated, dashboard-overclaims, abort-identity-rethrow]
```

Codex High (fold-induced, by the r1 L1 fold): splitting an over-ceiling press consumed one 0026 call slot per
chunk, so near the limit cents were lost — reproduced in a rolled-back transaction ([3,3,1] at calls=7 recorded
3¢). Claude High: an attempt aborted or timed out WHILE `generateContent` was in flight was never metered, so a
client could repeat presses by disconnecting (SDK 0.24.1 measured: abort and timeout both surface as
`GoogleGenerativeAIAbortError`, `name === 'Error'`). Claude Medium: the documented race is unbounded and slipped
presses miss the global ledger too.

Dispositions (§Q3): both Highs in the deliverable — FIX. The fold-induced one is answered by REMOVAL, not a
patch: the split is deleted, one call per press, and a test derives the worst-case press from the real
constants and fails if it can exceed 0026's ceiling. In-flight aborts are charged at the per-attempt bound
(the same conservative policy as r1's H2). The race is restated on backlog #61 as unbounded; no reservation is
built. Text overclaims corrected. FOLD: the batch-2 implementer subagent (`402ea6f5`). Master (PR #389–#391)
merged in (`9b9f00e1`): backlog #61 was edited on both sides — the scrub's 🟠→🟡 re-rate is reverted on the row,
with the reason, because this fix leaves #61's race as the remaining unrecorded-spend path. Round 3: both halves.
⚠ Thrashing check: r1→r2 is one fold-induced round in this component; a fold-induced finding in round 3 would arm it.
