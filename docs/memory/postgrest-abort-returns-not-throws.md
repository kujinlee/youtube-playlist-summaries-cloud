---
name: postgrest-abort-returns-not-throws
description: "FIRES-WHEN: using .abortSignal() with postgrest-js — supabase postgrest-js returns an aborted request as {error}, it does NOT throw — so try/catch around .abortSignal() is dead code, and AbortSignal.timeout's TimeoutError does not even match its abort branch"
metadata: 
  node_type: memory
  type: reference
  originSessionId: 85db654d-d23e-47f5-b2ea-89104f89cb42
  modified: 2026-08-11T01:33:01.845Z
---

**Verified 2026-08-10 against the installed `@supabase/postgrest-js` 2.109.0.**

`.abortSignal(signal)` exists and is chainable on `.rpc()`
(`node_modules/@supabase/postgrest-js/dist/index.d.mts:5246-5254`, `:1408`). What it does on timeout
is the trap:

- `shouldThrowOnError` is **`false` by default** (`dist/index.mjs:145`, `:152`).
- The fetch promise is `.catch()`-ed (`:326`) and an aborted request is **returned** as
  `{ data: null, error: { message: "AbortError: …", … }, status: 0 }` (`:345-362`).
- **It only throws if you call `.throwOnError()`** (`:171`).

**So `try { await client.rpc(...).abortSignal(...) } catch { … }` is dead code.** A settle wrapped
that way returns "success" for an RPC that never happened — which, on a refund path, means reporting
a refund you did not apply.

**Second trap.** `AbortSignal.timeout(ms)` aborts with a **`TimeoutError`** DOMException, but
postgrest's abort special-case (`:345`) tests `name === 'AbortError' || code === 'ABORT_ERR'`. A
`TimeoutError` matches neither, so it does not even get the "Request was aborted" hint — it falls
through to the generic error branch. Any detection keyed on postgrest's abort *shape* silently misses
the exact case you generate.

**The fix that survives both:** do not infer the failure from the client's error shape. Race the call
against your own timer, pass `.abortSignal()` as well so the request is genuinely cancelled, and
return an honest union — `{ok:true,data} | {ok:false,reason:'timeout'} | {ok:false,reason:'error',cause}`
— mirroring `BlobRead` (`lib/storage/blob-store.ts:10-13`). A caller must not be able to collapse
"timed out" into "returned an error" when the two have different money consequences. Implemented as
`lib/serve-rpc.ts`.

Found by the plan-gate review AND by reading the library — an instance of
[[quote-the-code-dont-characterise-it]]: the API being *offered* said nothing about what it *does*.
Related: [[serve-path-bounding-merged]].
