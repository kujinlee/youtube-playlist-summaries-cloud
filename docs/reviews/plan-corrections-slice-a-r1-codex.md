<!-- codex-review: model=gpt-5.5 -->

**Blocking**
- [docs/superpowers/plans/2026-08-24-corrections-in-cloud-slice-a.md](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-08-24-corrections-in-cloud-slice-a.md:2187): `record_correction_spend` is granted to `authenticated` and only caps each call. Since `spend_ledger` is global per UTC day ([0011](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/supabase/migrations/0011_cost_guardrails.sql:12)), one authenticated user can execute `rpc('record_correction_spend', { p_cents: 25 })` repeatedly and fill the global daily cap without doing corrections. The ceiling/reject/anon revoke do not prevent aggregate exhaustion.
  Suggested fix: do not expose this RPC to session clients. Make it service-role-only and call it from a server-only service client after the route has authenticated and completed a real correction, or add an owner/doc/day bounded protocol. Add a test that 20 direct authenticated calls cannot fill the global ledger.

- [docs/superpowers/plans/2026-08-24-corrections-in-cloud-slice-a.md](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-08-24-corrections-in-cloud-slice-a.md:491): the plan says `extractQuickView` still runs unconditionally, but Task 9 says bare press means “no correction, no spend” ([plan](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-08-24-corrections-in-cloud-slice-a.md:2292)). In actual code, `extractQuickView` is a Gemini call ([lib/gemini.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/gemini.ts:425)). Following the plan ships unrecorded paid work on every cloud bare press and underreports correction spend by excluding the quick-view call.
  Suggested fix: either make bare press a real no-op in cloud, or measure and record quick-view usage too. The ledger falsifier should assert the actual paid call set, not just `fixSummary`.

**High**
- [docs/superpowers/plans/2026-08-24-corrections-in-cloud-slice-a.md](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-08-24-corrections-in-cloud-slice-a.md:2392): T10 claims to fix “the other non-ok statuses,” but the implementation only adds fallback for `attempts_exhausted`, `at_capacity`, and `owner_over_budget` ([plan](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-08-24-corrections-in-cloud-slice-a.md:2472)). `busy` still maps to 503 in the consumer ([serve-summary-core.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/html-doc/serve-summary-core.ts:120)) while a title-stable model may be readable. T4 makes this reachable because `readFreshMagazineModel` rejects hash-stale envelopes before reserve.
  Suggested fix: add a stale fallback for `in_flight`/`busy` after the fresh re-read misses, and for reserve timeout if appropriate. Add tests for `busy + stale model`.

- [docs/superpowers/plans/2026-08-24-corrections-in-cloud-slice-a.md](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-08-24-corrections-in-cloud-slice-a.md:367): Task 2 makes `signal` required but its implementation drops it: `fixSummary(stripped, input.corrections)` and `extractQuickView(fixed)` ([plan](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-08-24-corrections-in-cloud-slice-a.md:505)). Task 5 later wires the signal only into `fixSummary`; `extractQuickView` has no signal parameter today ([lib/gemini.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/gemini.ts:425)).
  Suggested fix: extend `extractQuickView` to accept `{ signal, caps, billing }` or equivalent and pass it through to `generateJson`; cover abort during quick-view and bare-press quick-view.

- [docs/superpowers/plans/2026-08-24-corrections-in-cloud-slice-a.md](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-08-24-corrections-in-cloud-slice-a.md:1921): cloud correction checks only `video.summaryMd`; it does not gate on `artifacts.summaryMd.status === 'promoted'` or validate the cloud summary key. The serve path does both ([serve-summary-core.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/html-doc/serve-summary-core.ts:43)). A committed/finalizing artifact can be edited while a worker promotion is still in flight, risking overwrite or incoherent status.
  Suggested fix: reuse `loadSummaryForServe` or duplicate its status/key checks: committed -> 503, non-promoted -> 404, corrupt key -> 409.

- [docs/superpowers/plans/2026-08-24-corrections-in-cloud-slice-a.md](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-08-24-corrections-in-cloud-slice-a.md:1290): Task 5 changes `fixSummary`’s signature but does not update existing tests in [tests/lib/gemini.test.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/tests/lib/gemini.test.ts:542). `tsconfig` includes tests ([tsconfig.json](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/tsconfig.json:24)), so `npx tsc --noEmit` will fail unless those calls are migrated.
  Suggested fix: explicitly update all `fixSummary(` call sites from `rg`, including old unit tests and route tests.

**Medium**
- [docs/superpowers/plans/2026-08-24-corrections-in-cloud-slice-a.md](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-08-24-corrections-in-cloud-slice-a.md:1076): several red-phase predictions say `npx jest` reports TypeScript errors. This repo uses `next/jest` ([jest.config.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/jest.config.ts:1)); type errors are caught by `tsc`, not reliably by Jest. Example: Task 4’s “Expected 2 arguments” prediction is wrong because JS ignores the third arg and the behavioral assertion fails instead.
  Suggested fix: change those steps to expect runtime assertion failures under Jest, and run `npx tsc --noEmit` when the intended red is type-level.

- [docs/superpowers/plans/2026-08-24-corrections-in-cloud-slice-a.md](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-08-24-corrections-in-cloud-slice-a.md:1474): Task 6’s backend parity test is a placeholder, not executable: it uses undefined `principal`, `VIDEO_ID`, and `indexStore`, and literally says “seed an index…”. This violates the “zero context engineer” bar.
  Suggested fix: replace with a complete local temp-dir fixture, or point to an existing helper and exact setup code.

- [docs/superpowers/plans/2026-08-24-corrections-in-cloud-slice-a.md](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-08-24-corrections-in-cloud-slice-a.md:2524): the new component test lacks `/** @jest-environment jsdom */`, while the repo explicitly relies on per-file jsdom headers ([jest.config.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/jest.config.ts:5)). The predicted failure “missing required outputFolder prop” is unlikely to be the observed Jest red.
  Suggested fix: add the jsdom header and make the red expectation about rendered/fetch behavior, not TypeScript.

- [docs/superpowers/plans/2026-08-24-corrections-in-cloud-slice-a.md](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-08-24-corrections-in-cloud-slice-a.md:2891): Task 12 does not implement several spec §7 falsifiers it names: “correction path writes no envelope,” “applying press makes row current true -> false,” full “all six ClassASignals byte-identical,” `updatedAt` blast-radius, already-long stored value, and over-cap local-origin document.
  Suggested fix: either add concrete tests for those rows or move them to the “Out of the 12” tracked residue.

**Low**
- [docs/superpowers/plans/2026-08-24-corrections-in-cloud-slice-a.md](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-08-24-corrections-in-cloud-slice-a.md:2233): the T9 mutation-check manually mutates live `guardrail_config` to `2147483647`. If the run aborts before restore, later tests run with the money guard disabled.
  Suggested fix: wrap in test setup/teardown or use a transaction/reset helper.

- Placeholder scan: no `TBD`, “add appropriate error handling,” or “similar to Task N” found. The real placeholder is the incomplete Task 6 test above.

**NOT VERIFIED**
- I did not run the live Supabase integration suites or production anon-exposure script. SQL/database findings above are from reading migrations, route plan, and existing harness.

NOT CONVERGED
