# Round 1 — `correction-spend-on-failure` — coordinator — ❌ NOT CONVERGED (2 High, 2 Medium, 3 Low)

```yaml
round: 1
fixes_nontrivial: true
subject: correction-spend-on-failure
halves:
  codex: ran
  claude: ran
findings: [limit-refuses-recording-not-spend, unmeasured-press-dropped, recording-await-unbounded, ceiling-headroom, test-seam-413, integration-global-delta]
```

Both halves found the same High independently: migration 0026's per-owner daily limit refuses only the
RECORDING, and nothing checks it before the paid `fixSummary` call — press 9+ of the day spends unrecorded.
Codex H2: a billed attempt with no usage metadata recorded nothing. Both: the recording `await` had no
deadline (Medium). Claude Lows: the per-press cents ceiling, the 413 test seam, integration cases asserting a
global ledger delta.

Dispositions (§Q3): the Highs are in the deliverable — FIX. H1 is folded by enforcing the EXISTING 0026
limit before the paid call (a read-only allowance RPC, migration 0028, SECURITY DEFINER, revoked from
PUBLIC/anon): this implements a decision already made, it does not make a new one. It is a CHECK, not a
reservation; the race window is recorded on backlog #61 (also flagged by the automated security review).
FOLD: the batch-2 implementer subagent (`07e3f254`). Round 2: both halves, because the fold adds a migration.
