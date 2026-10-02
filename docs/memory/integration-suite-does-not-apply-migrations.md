---
name: integration-suite-does-not-apply-migrations
description: "FIRES-WHEN: running test:integration, or trusting it against a schema change — FIXED 2026-08-04 (PR #46) — test:integration now applies pending migrations in globalSetup and refuses to run if it can't; keep the lesson about green-but-meaningless gates"
metadata: 
  node_type: memory
  type: project
  originSessionId: 18820d36-e0cd-46c7-945b-e5f3417ebb5f
  modified: 2026-08-04T22:32:36.719Z
---

✅ **FIXED — PR #46 (`b0cde4f`, 2026-08-04).** `tests/integration/global-setup.ts` runs
`supabase migration up` once per suite (jest `globalSetup`, **not** `setupFiles`, which fires per
test file). No manual step is needed any more.

Behaviour worth knowing:
- Warns loudly if anything WAS pending — that means every earlier run on that machine tested the
  wrong schema.
- **Refuses to run** if migrations cannot be applied, including when the CLI succeeds but returns
  unrecognised output. Unknown is treated as unknown, never as fine.
- A no-op costs ~4.6 s against a ~160 s suite.

**Why it existed, and the lesson that outlives the fix.** `npm run test:integration` used to run
against whatever schema the local stack happened to have. On a branch adding a migration that is the
OLD schema, so the suite reported **green while testing code that was not the code under review** —
the dangerous shape is not a red suite people ignore, but a green one that proves nothing.

It bit once: migration `0023` sat unapplied on `fix/serial-coherence-sync`, and applying it by hand
surfaced two real failures immediately — one test asserting the very phantom-serial bug `0023` fixes
(its own comment said *"Observed behavior … per T8/T9 flag"*: someone noticed it was odd, wrote down
what it **did** rather than what it **should** do, and never closed the flag), and one stale key
assertion passing for the wrong reason.

**Generalisable:** when a test-harness step can silently no-op, verify the FAILING direction too. The
fix here was mutation-tested by breaking the migration command and confirming **0 tests executed** —
testing only the happy path would have reproduced the original bug inside its own fix.

Still true regardless: run the integration suite **twice back-to-back with no DB reset**; green only
on the first run counts as red.

Related: [[serial-coherence-slice-state]], [[worker-vs-sync-fencing-gap]], [[local-cloud-validation-run]].
