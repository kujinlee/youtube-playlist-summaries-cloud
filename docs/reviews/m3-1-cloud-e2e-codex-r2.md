<!-- codex-review: model=gpt-5.5 -->

**Blocking**
- [tests/e2e/cloud.setup.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/tests/e2e/cloud.setup.ts:53) + [tests/e2e/cloud-journey.spec.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/tests/e2e/cloud-journey.spec.ts:162): the guard still does not cover failures in the setup project. The baseline is captured at setup line 56, but the only assertion is in the dependent `cloud` project. If setup touches money and then fails or times out before writing/finishing, Playwright will not run the dependent cloud project, so this `afterAll` is silently absent. That is exactly the window the baseline move was meant to include.

**High**
- [tests/e2e/cloud-fixture.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/tests/e2e/cloud-fixture.ts:15): `FIXTURE_FILE` is deliberately outside `test-results`, so it survives runs, but it has no run id, timestamp validation, DB identity, or coupling to the current setup execution. A later `--project=cloud --no-deps`, interrupted setup, or cloud-only invocation can compare the current DB ledger against a stale baseline from a previous run. That creates both false positives and false negatives. The normal `npm run test:e2e:cloud` path does run setup via [playwright.cloud.config.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/playwright.cloud.config.ts:40), but the guard is brittle under common Playwright partial-run workflows.

**Medium**
- [tests/e2e/cloud-fixture.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/tests/e2e/cloud-fixture.ts:33): `readLedger()` reads `ledger_audit` and `spend_ledger` concurrently with separate REST queries, not one transaction/snapshot. A concurrent reservation/settle can put `auditMaxId` on one side of the write and `centsTotal` on the other, yielding a baseline that never existed. With `workers: 1` this suite is internally serialized, so this mainly bites when the shared local Supabase has another worker/test/manual request running. Still a real spurious-failure source for a money guard.

- [tests/e2e/cloud-journey.spec.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/tests/e2e/cloud-journey.spec.ts:158): the comment overclaims the witness. `ledger_audit.id` is a good witness for `serve_settle` and `release_underflow`; migration 0025 does write `serve_settle` on settled serve attempts, so the prompt’s “normal paid serve nets to zero and leaves no audit” attack is not true for the current serve path. But the guard still does not prove “no money path was reached” generally: an enqueue reservation followed by a legitimate never-metered queued cancel/release can net `spend_ledger` to zero and write no audit row. That is not reachable from today’s journey because POST `/api/jobs` is intercepted and there is no cancel rung, but the comment is broader than the code.

**Low**
- [tests/e2e/cloud-journey.spec.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/tests/e2e/cloud-journey.spec.ts:18): “STEP 6 PROVES IT” is stale after moving the guard to `afterAll`; step 6 is now sign-out. Also line 23 says “the last step reads the ledger before and after,” but the before read is now in setup. Not functionally wrong, but these long comments are supposed to be load-bearing and currently misdescribe the mechanism.

**Explicitly Found Nothing**
- Same-file earlier rung failure: `afterAll` should run; the move from a serial rung to a hook fixes the original skip-on-failed-rung problem.
- Same-file `beforeAll` failure: Playwright’s worker code marks the suite active before running `beforeAll`, then runs `afterAll` during cleanup. There is no `beforeAll` left in this spec anyway.
- Rung 7 trigger name: [AccountMenu.tsx](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/components/cloud/AccountMenu.tsx:63) renders the email as the button text and the chevron is `aria-hidden`, so `exact: true` should not break on “email plus chevron.”
- Removed `beforeAll`: I found no remaining dependency on it, no import cycle from moving `readLedger` into the plain fixture module, and no new per-test Supabase client churn beyond the afterAll default client plus existing explicit `adminClient()` calls.

`afterAll` is not “always”: it is absent if the setup project fails/times out, if the cloud-journey file is never scheduled due to `--max-failures`/`-x` before it starts, if the worker/process crashes or is killed, or if the whole run is globally aborted. If a rung in this file fails or times out, Playwright should attempt it; if `afterAll` itself times out, the guard result is again inconclusive.

NOT CONVERGED
