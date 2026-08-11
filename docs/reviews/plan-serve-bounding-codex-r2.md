<!-- codex-review: model=gpt-5.5 -->

**Blocking**

- **Task 5 Step 3 [v2-REGRESSION]: `callRpcBounded` does not compile with its own `fakeRpcBuilder`.**  
  What I checked: the planned fake at `docs/superpowers/plans/2026-08-10-serve-path-bounding.md:714-724` against the planned `callRpcBounded(make: ... PromiseLike<...>)` signature at `:678-681`. I type-checked the snippet under `--strict`; `fakeRpcBuilder(...).abortSignal(s)` is not assignable to `PromiseLike<{data; error}>` because the custom `then<A,B>` signature does not match `PromiseLike.then`.  
  Literal result: `tests/lib/serve-rpc.test.ts` cannot compile before it can test the race.

- **Task 6 Step 4 [v2-REGRESSION]: switching production to `generateMagazineModelForServe` breaks existing Jest module mocks.**  
  What I checked: production currently imports `generateMagazineModel` in [serve-doc.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/html-doc/serve-doc.ts:9), while both [serve-doc-mapping.test.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/tests/lib/html-doc/serve-doc-mapping.test.ts:11) and [serve-doc-materialize.test.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/tests/integration/serve-doc-materialize.test.ts:11) mock `@/lib/gemini` with only `generateMagazineModel`.  
  Literal result: after Task 6 changes `serve-doc.ts` to import/call `generateMagazineModelForServe`, those tests receive `undefined` from the mock and fail with a TypeError unless the mocks are upgraded too. The plan only upgrades the Supabase fake.

- **Task 6 Step 2 [v2-REGRESSION]: the planned tests rely on a nonexistent `runServe` harness.**  
  What I checked: full [serve-doc-materialize.test.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/tests/integration/serve-doc-materialize.test.ts:1). There is no `runServe`, and the file uses real seeded Supabase clients plus a module-level Gemini mock.  
  Literal result: adding the snippet at plan lines `791-843` does not compile. Extending “the existing harness” is impossible because it is not there.

**High**

- **Task 5 Step 3 [v2-REGRESSION]: `callRpcBounded` does not return the promised error union for thrown/rejected RPC construction.**  
  What I checked: `Promise.resolve(make(ctrl.signal))` at plan line `690`. `make(ctrl.signal)` is evaluated before `Promise.resolve`; a synchronous throw rejects `callRpcBounded` directly. A rejecting thenable also rejects the raced await directly. Neither becomes `{ ok:false, reason:'error', cause }`.  
  Literal result: callers written per Task 6 only handle `!reserve.ok`; a construction error or rejected PostgREST promise bypasses the union and throws from the seam, contradicting the “honest outcome” contract.

- **Task 3 Step 1 [v2-REGRESSION]: the new test imports `CloudGeminiCaps` from a nonexistent module.**  
  What I checked: plan line `336` imports from `@/lib/gemini-caps`; the real type is exported from [gemini-cost.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/gemini-cost.ts:64), and current code imports it from `@/lib/gemini-cost`.  
  Literal result: `tests/lib/gemini-serve-budget.test.ts` fails module resolution.

- **Task 3 Step 1 [v2-REGRESSION]: `okResponse` is not a valid magazine model.**  
  What I checked: plan lines `343-346` return one bullet; the real magazine schema requires 3-7 bullets, and existing tests/builders use three bullets.  
  Literal result: the “passes the serve per-attempt timeout” test reaches Zod parsing and throws instead of succeeding, even when the timeout is passed correctly.

- **Task 6 Step 2 [v2-REGRESSION]: the planned 429 refund test does not actually reach the refund path.**  
  What I checked: existing refund tests in [serve-doc-materialize.test.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/tests/integration/serve-doc-materialize.test.ts:278) set `process.env.CLOUD_GEMINI_RELEASE_VERIFIED = 'true'`; the planned test does not. It also uses `GeminiHttpError`, while the file imports `GoogleGenerativeAIFetchError`.  
  Literal result: even after inventing a harness, the test either does not compile or asserts `p_released: true` while `releaseGateOpen()` is false, so the code would keep rather than refund.

- **Task 7 Step 1 [v2-REGRESSION]: the planned invariant tests use `admin`, but the file defines `svc`.**  
  What I checked: plan lines `961-971`; existing [serve-config-invariant.test.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/tests/integration/serve-config-invariant.test.ts:3) defines `const svc = adminClient();`, no `admin`.  
  Literal result: pasted tests fail to compile.

**Medium**

- **Task 4 Step 1: the v2 “verified” fixture claim is still false.**  
  What I checked: plan lines `496-503` claim [model-store.test.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/tests/lib/html-doc/model-store.test.ts:1) defines `fakeBlobStore`. It does not; there is only a local `const fakeBlobStore` inside one existing test, not in scope for new tests.  
  Literal result: the new tests reference `fakeBlobStore` out of scope and fail to compile.

- **Coverage table: `§5 every bounded term aborts | 2, 4, 5, 6` is false for Task 4.**  
  What I checked: Task 4 explicitly says the upload race “does NOT cancel the upload” at plan lines `492` and `537-539`.  
  Literal result: the plan’s self-review overclaims coverage. The put wait is bounded, but the underlying put is not aborted.

**Low**

- **Task 5 Step 3: the losing RPC promise is handled after timeout.**  
  What I checked: `Promise.race` attaches handlers to the `Promise.resolve(make(...)).then(...)` entry. A later rejection should be observed by the race machinery, so this is not an unhandled-rejection defect. The real Task 5 defects are compile shape and thrown/rejected conversion.

- **Task 7 Step 3: SQL idempotency and regex look acceptable.**  
  What I checked: the DO block drops all matching check constraints before adding `guardrail_config_lease_ttl_covers_serve`, so re-apply removes its own prior constraint first. `raise warning` is valid in PL/pgSQL. The regex `/lease_ttl_seconds\s*>=\s*(\d+)\s*\)/` matches the `check (lease_ttl_seconds >= 156)` occurrence, not the nearby `>= 1` comment.

NOT CONVERGED
