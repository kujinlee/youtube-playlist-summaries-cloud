<!-- codex-review: model=gpt-5.5 -->

**Blocking**

- **Task 4 Step 1: false `[VERIFIED]` tag.**  
  The plan says `[VERIFIED: tests/lib/html-doc/model-store.test.ts:12]` defines `ENVELOPE`, `principal`, `BASE` and `fakeBlobStore`. That is false. [model-store.test.ts:12](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/tests/lib/html-doc/model-store.test.ts:12) starts `ENVELOPE`; `BASE` is line 11, `principal` is declared line 10 and assigned in `beforeEach`, and `fakeBlobStore` only exists as a local const inside one test at line 83. The next paragraph corrects part of this, but the false `[VERIFIED]` tag is explicitly Blocking under the round-3 rules.  
  Checked: [VERIFIED: tests/lib/html-doc/model-store.test.ts:10-12,83].

**High**

- **Task 6 Step 2 [v2-REGRESSION]: the shared mock-factory replacement breaks the integration file’s existing assertions.**  
  The plan tells the engineer to add the same delegating mock factory to both `serve-doc-mapping.test.ts` and `serve-doc-materialize.test.ts`, with default generated lead `'GEN'`. That is fine for the mapping file, whose reserved-path assertion expects `'GEN'`, but the integration file’s current mock returns `'L'` and multiple existing tests assert that generated/persisted lead is `'L'`. Literal result: after following the snippet in the integration file, existing assertions fail at lines 142, 149, 176, and 266.  
  Checked: [VERIFIED: tests/lib/html-doc/serve-doc-mapping.test.ts:14-17,121], [VERIFIED: tests/integration/serve-doc-materialize.test.ts:11-14,142,149,176,266].

- **Task 6 Step 3: the timeout tests use 5-second production budgets and can fail on Jest’s default timeout.**  
  The new reserve-timeout and settle-retry tests hang an RPC builder and rely on production `SERVE_RESERVE_RPC_TIMEOUT_MS` / `SERVE_SETTLE_RPC_TIMEOUT_MS`, both planned as `5_000`. The unit file has no `jest.setTimeout`, and the repo has no global unit timeout override. Literal result: the reserve timeout test can hit Jest’s default 5000ms timeout before `callRpcBounded` returns `busy`; the settle retry test also burns one full 5s timeout before the retry. The plan needs fake timers or mocked small serve-budget constants.  
  Checked: [VERIFIED: docs/superpowers/plans/2026-08-10-serve-path-bounding.md:107-113,875-888], [VERIFIED: tests/lib/html-doc/serve-doc-mapping.test.ts:1-124], repo search for `testTimeout` / `jest.setTimeout`.

- **Task 6 Step 3: `CLOUD_GEMINI_RELEASE_VERIFIED` leaks from the new unit test.**  
  The settle-retry test sets `process.env.CLOUD_GEMINI_RELEASE_VERIFIED = 'true'` and never restores it. `serve-doc-mapping.test.ts` currently has only `beforeEach(() => mockClear())`, no env cleanup. Literal result: later tests in the same worker can observe the release gate as open when they did not request it. Existing files that set this env generally restore it with `afterEach`.  
  Checked: [VERIFIED: docs/superpowers/plans/2026-08-10-serve-path-bounding.md:883-887], [VERIFIED: tests/lib/html-doc/serve-doc-mapping.test.ts:81], [VERIFIED: tests/integration/serve-doc-materialize.test.ts:275-276], [VERIFIED: tests/lib/gemini-failure.test.ts:55-57].

**Medium**

- **Task 6 Step 3: the snippet asserts on `generateMagazineModelForServe` but never clears that mock.**  
  Step 2 imports the wrapper mock, but the existing `beforeEach` still only clears `generateMagazineModel`. After production switches to the wrapper, any prior reserved-path test call can leave `generateMagazineModelForServe` dirty. Literal result: `expect(generateMagazineModelForServe).not.toHaveBeenCalled()` can fail depending on where the engineer inserts the new tests.  
  Checked: [VERIFIED: tests/lib/html-doc/serve-doc-mapping.test.ts:81,116-122], [VERIFIED: docs/superpowers/plans/2026-08-10-serve-path-bounding.md:861-867].

- **Task 6 Step 3: the “run failing tests” command still points at the wrong file.**  
  The plan says the timeout/retry tests moved into `tests/lib/html-doc/serve-doc-mapping.test.ts`, then Step 3 tells the engineer to run only `npx jest tests/integration/serve-doc-materialize -v` and expects reserve-timeout / settle-retry failures. Literal result: the new tests are not run at the red step, so the TDD gate does not verify the tests it just added.  
  Checked: [VERIFIED: docs/superpowers/plans/2026-08-10-serve-path-bounding.md:841-847,911-914].

- **Task 7 Step 1: read-then-restore is not exception-safe.**  
  `.single()` is correct for the singleton `guardrail_config` row, but the restore is not in a `finally`. A thrown `expect` after setting the floor skips cleanup. Literal result: a failed assertion can leave `lease_ttl_seconds` at `SERVE_FLOOR_SECONDS`, contaminating later integration tests in the shared DB.  
  Checked: [VERIFIED: tests/integration/serve-config-invariant.test.ts:1-18], [VERIFIED: docs/superpowers/plans/2026-08-10-serve-path-bounding.md:1033-1040].

**Checked OK**

- Task 5’s revised `fakeRpcBuilder` type-checks under `--strict`; `Promise.resolve(builder)` and `await builder` work with the planned `then` signature. The `attempt` IIFE folds synchronous throws and rejected thenables into `{ ok:false, reason:'error' }`, and the losing promise has a catch path, so I do not see an unhandled-rejection defect there.
- Task 6’s delegating wrapper does route through `(generateMagazineModel as jest.Mock).mockImplementationOnce(...)`; the problem is the integration fixture value change, not the delegation.
- Task 7 migration idempotency and regex look acceptable: the loop drops all matching check constraints before adding the new one, `raise warning` is valid PL/pgSQL, and the regex matches the actual `check (lease_ttl_seconds >= 156)` occurrence rather than the `>= 1` comment.

NOT CONVERGED
