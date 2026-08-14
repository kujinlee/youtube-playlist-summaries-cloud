<!-- codex-review: model=gpt-5.5 -->

**Findings**

**Blocking:** none.

**High:** none.

**Medium**
- [tests/e2e/cloud-global.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/tests/e2e/cloud-global.ts:22): the comment overclaims `global timeout` coverage. Playwright does attempt cleanup, but it reuses the original global-timeout deadline for teardown: [runner/index.js](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/node_modules/playwright/lib/runner/index.js:5698). If the deadline is already expired, `TimeoutWatcher` resolves immediately: [runner/index.js](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/node_modules/playwright/lib/runner/index.js:5708). So a global timeout during or just before teardown can prevent the ledger read from completing. The run is still non-zero, but the money guard has not made its claim.

**Low**
- [tests/e2e/cloud-global.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/tests/e2e/cloud-global.ts:36): "`globalSetup` runs on EVERY invocation" is not true if the `webServer` plugin fails. Playwright runs plugin setup before user global setup: [runner/index.js](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/node_modules/playwright/lib/runner/index.js:5828) and [runner/index.js](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/node_modules/playwright/lib/runner/index.js:5864). Therefore a webServer startup failure means no fixture deletion and no baseline read. Also, `next dev` and the `/login` readiness probes happen before the baseline. I do not see a current `/login` startup money path, so this is an overclaim/comment precision issue, not a functional failure in the current suite.
- [tests/e2e/cloud-global.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/tests/e2e/cloud-global.ts:63): if `globalSetup` itself throws after reading `baseline` but before returning the teardown function, Playwright will run the task teardown but `globalSetupResult` is not a function, so no ledger check runs: [runner/index.js](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/node_modules/playwright/lib/runner/index.js:5894). Current code has no meaningful throwing work between the baseline read and `return`, so this is not a current bug.

**Explicit Checks Where I Find Nothing**
- Teardown failure does fail a passing run. `TaskRunner.run()` returns teardown status when the main phase passed: [runner/index.js](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/node_modules/playwright/lib/runner/index.js:5644). Errors thrown by teardown are reported through `reporter.onError`: [runner/index.js](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/node_modules/playwright/lib/runner/index.js:5668). A CI reader should see the thrown message.
- Setup project failure / unscheduled dependent project / `-x` / `--max-failures` / SIGINT are materially supported. Cleanup tasks are queued before each setup task executes: [runner/index.js](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/node_modules/playwright/lib/runner/index.js:5662), teardown mode does not interrupt on teardown task errors: [runner/index.js](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/node_modules/playwright/lib/runner/index.js:5671), and SIGINT is handled in-process: [runner/index.js](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/node_modules/playwright/lib/runner/index.js:5554). SIGKILL remains correctly excluded.
- Destructive deletion consumers are limited to the cloud config storage state, the setup writer, and the journey fixture reader. The local `playwright.config.ts` shares `testDir` but ignores `cloud[.-]`, so it does not consume these files.
- The Supabase response checks use the right shape for this client: `PostgrestResponse` exposes `error` and `data`; service-role `adminClient()` avoids the repo’s known RLS-denial-as-absence trap.
- The updated serve/enqueue witness comments now match migrations 0025 and 0020: `serve_settle` is durable, normal queued release has no audit unless underflow.

NOT CONVERGED
