# Round 3 — `correction-spend-on-failure` — coordinator — ❌ NOT CONVERGED (1 High, 1 Medium, 4 Low)

```yaml
round: 3
fixes_nontrivial: true
subject: correction-spend-on-failure
halves:
  codex: ran
  claude: ran
findings: [body-read-timeout-unmetered, other-dead-abort-checks, refusal-rate-claim, ceiling-test-regex]
```

Both halves measured the same gap with the REAL SDK: a timeout during the response-BODY read rejects with a
plain DOMException `AbortError` (outside the SDK's abort wrapper), signal not aborted, so neither r2 meter
condition fired. Codex rated it High, Claude Low (client cannot trigger it; window small); Claude also showed
it PRE-DATES the r2 fold, so it is a gap not closed rather than one caused — thrashing is not armed.

Disposition (§Q3): FIX, by REDESIGN rather than a third error-shape check — every attempt is charged at the
per-attempt bound AT DISPATCH and replaced by measured usage when a response arrives, so any exit path is
metered by construction and the classification branches are deleted; a cancel is decided by the caller's
signal alone. Real-SDK tests (body stall, header stall, caller abort, last-attempt abort). Ceiling test made
strict by construction (any mention outside 0026 fails; 0028 no longer reads `max_cents`). Codex Medium (the
other dead name-checks) FILED as backlog #345; the refusal-rate claim removed. FOLD: implementer subagent
(`4f60ac97`). Round 4: both halves.
