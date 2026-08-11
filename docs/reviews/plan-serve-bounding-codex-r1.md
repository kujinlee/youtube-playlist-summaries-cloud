<!-- codex-review: model=gpt-5.5 -->

**Blocking**

- **Task 5, Step 3: bounded RPC timeout handling is wrong.**  
  The plan assumes `.abortSignal(AbortSignal.timeout(...))` throws into the surrounding `catch`. In installed `@supabase/postgrest-js` 2.109.0, awaiting a builder without `.throwOnError()` catches fetch aborts and resolves `{ error, data: null, status: 0 }` instead. I checked `node_modules/@supabase/postgrest-js/src/PostgrestBuilder.ts:388-456`.  
  Literal result:
  - Reserve timeout does **not** enter the `catch`, so it reaches `if (error) throw error` instead of returning `{ status: 'busy' }`.
  - Settle timeout does **not** enter `settleBounded`’s `catch`; because the snippet never checks `{ error }`, it returns `true`, does not retry the refund, and may report/assume a settle that never happened.

- **Task 5, Step 1/3: the settle retry tests cannot exercise the planned implementation as written.**  
  The tests pass `settle = jest.fn(async () => ...)`, but the implementation calls `supabaseClient.rpc(...).abortSignal(...)`. A bare async mock returning `{ data, error }` has no `.abortSignal`. The existing seam fake in `tests/lib/html-doc/serve-doc-mapping.test.ts:30-33` is also a bare async `rpc`, so Task 5 will break existing seam tests unless all fakes are upgraded to return a chainable thenable builder. The plan does not say to update them.

**High**

- **Task 5, Step 3: `settleBounded` drops existing RPC error semantics on the kept path.**  
  Existing code at `lib/html-doc/serve-doc.ts:126` and `:133` awaits `supabaseClient.rpc(...)`; PostgREST non-throwing errors are returned in `{ error }`, and the old code also failed to check them. The new helper claims to bound/retry, but because it neither destructures nor checks `error`, any PostgREST error response, including timeout, is treated as success. That violates the plan’s own “refund decision AND outcome” coverage claim.

- **Task 5, Step 1: the “both release settles fail” test asserts an output shape that `resolveMagazineModel` does not have.**  
  The plan says Task 5 “produces no new exports; `resolveMagazineModel`’s existing return union is unchanged,” but the test expects `res.refundConfirmed`. Existing `ResolveResult` in `lib/html-doc/serve-doc.ts:29-35` has no such field, and generation failure paths rethrow at `serve-doc.ts:134`. An engineer following the test literally must either invent an unplanned helper return contract or change the public union, contradicting the task.

- **Task 3, Step 1: the new test references undeclared/unexported helpers and constants.**  
  `mockModel`, `okResponse`, `generateMagazineModelForServe`, `generateMagazineModel`, and `SERVE_CAPS` are used but not imported or defined in the code block. `SERVE_CAPS` is currently a private `const` in `lib/html-doc/serve-doc.ts:20`, not exported from `gemini.ts` or the budget module. This is not a minor omission: the test cannot compile as written.

**Medium**

- **Task 4, Step 1: the model-store tests reference helpers that do not exist in the file.**  
  The plan uses `stubStore`, `validEnvelope`, and `principal`. The existing test file has `ENVELOPE`, `principal`, and local fake stores, but no `stubStore` or `validEnvelope` (`tests/lib/html-doc/model-store.test.ts:1-104`). An engineer must infer replacements before the test can compile.

- **Task 6, Step 3: the migration’s constraint drop query is broader than the intended old constraint.**  
  It drops the first check constraint on `guardrail_config` whose definition contains `lease_ttl_seconds`. Today `rg` shows only the inline `lease_ttl_seconds >= 1` check in `0012`, so it probably works on the current schema. But it is not robust: if a future or partially-applied schema has another check mentioning that column, `select conname into v_name` can either drop the wrong constraint or fail with “more than one row.” The plan states this as a safe generated-name lookup; it is only safe against the current single-constraint state.

**Low**

- **Task 3, Step 3: the retry arithmetic is correct, but the plan should explicitly preserve call-site reachability.**  
  I checked `generateJson`’s loop at `lib/gemini.ts:256`: `for (let attempt = 0; attempt <= retries; attempt++)`, so `budget.attempts - 1` gives exactly `budget.attempts` calls. The 8th positional `timeoutMs` is reachable by passing `undefined` for the optional `opts`; existing call sites remain compatible. No defect there.

- **Task 4, Step 3: `DOMException(..., 'TimeoutError')` matches the planned test.**  
  In Node 22, `new DOMException('...', 'TimeoutError').name` is `TimeoutError`, so `rejects.toMatchObject({ name: 'TimeoutError' })` is sound.

NOT CONVERGED
