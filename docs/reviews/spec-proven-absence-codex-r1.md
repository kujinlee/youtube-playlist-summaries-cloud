<!-- codex-review: model=gpt-5.5 -->

**Blocking**

None found.

**High**

1. `docs/superpowers/specs/2026-08-11-serve-path-proven-absence-design.md:91` — D2 is not airtight under realistic policy skew. The repo’s current policy is owner-prefix-wide (`supabase/migrations/0007_storage_and_rpcs.sql:12-17`), but the spec’s proof assumes that remains the only authenticated path forever. Concrete failure: owner policy is dropped/broken, but an emergency/read-only markdown policy remains, e.g. allow `*.md` under owner prefix. Then the control markdown read succeeds, the model read is still hidden as 404, and the serve path spends on a model that exists. The control read proves “this user may read this markdown object,” not “this user may read all objects in this folder,” unless the policy set is itself asserted.

2. `docs/superpowers/specs/2026-08-11-serve-path-proven-absence-design.md:107-109` — the proposed control read is an unbounded full `download`, not a cheap existence check. `SupabaseBlobStore.tryGet` calls `.download(...)` and buffers the full object (`lib/storage/supabase/supabase-blob-store.ts:44-52`). There is no read timeout alongside the reserve/put/settle budgets (`lib/html-doc/serve-doc.ts:11-14`). Concrete failure: a large markdown or Storage slowdown lets `loadSummaryForServe` succeed once (`lib/html-doc/serve-summary-core.ts:66-67`) but the second full read hangs or times out at the platform/request layer before reserve. Every first serve of a never-generated model repeats that extra read, so the document can sit in a 503/hang loop while the model is genuinely absent.

3. `docs/superpowers/specs/2026-08-11-serve-path-proven-absence-design.md:57-60` — “not produced by 5xx, timeout or transport failure” is overclaimed for the actual money proof. The code classifies *any* Storage error with `statusCode === '404'` as absent (`lib/storage/supabase/supabase-blob-store.ts:47-50`), and there is no test proving Supabase never uses 404-shaped errors for non-RLS/non-absence cases. Current unit coverage does not exercise `tryGet` at all; it only has a `get` test whose mocked error lacks `statusCode` (`tests/lib/storage/supabase-blob-store.test.ts:121-125`). A Storage-layer edge that returns 404 for “row visible but backing object temporarily unavailable/path backend miss” would pass the control read and spend.

**Medium**

1. `docs/superpowers/specs/2026-08-11-serve-path-proven-absence-design.md:92` contradicts `docs/superpowers/specs/2026-08-11-serve-path-proven-absence-design.md:95`: D3 says no caller obligation, but D6 relies on `parsed.sourceMd` being caller-mutated correctly. Production does that (`lib/html-doc/serve-summary-core.ts:101-105`), but `resolveMagazineModel`’s signature does not carry `mdKey`, so direct callers can pass stale/wrong `sourceMd`. Existing direct tests build `sourceMd: 'v.md'` and do not seed an MD blob because today none is needed (`tests/integration/serve-doc-materialize.test.ts:27-35`, call at `:70`). Literal implementation makes that branch fail closed unless all direct callers/tests are rewritten.

2. `lib/storage/supabase/supabase-blob-store.ts:39-43` contains a false code claim: it says Supabase 404 “IS provable absence” and RLS denial is `unreadable`. The spec’s measured defect says the opposite for RLS-shaped 404s (`docs/superpowers/specs/2026-08-11-serve-path-proven-absence-design.md:39-49`). Leaving that comment in place will mislead the next money-path edit.

3. `docs/superpowers/specs/2026-08-11-serve-path-proven-absence-design.md:155-157` is accurate but incomplete: dig serve does not reserve or generate. Verified: `loadDigForServe` calls `loadSummaryForServe`, parses bytes, reads cached envelope, lists/gets dig blobs, then returns (`lib/dig/cloud/load-dig-for-serve.ts:24-55`); only caller renders it (`app/api/html/[id]/route.ts:50-62`). No money hole found there. The spec should state that envelope read failures degrade rendering because `readModelEnvelope` null-collapses (`lib/html-doc/model-store.ts:105-112`), but no charge follows.

**Low**

1. `docs/superpowers/specs/2026-08-11-serve-path-proven-absence-design.md:93` — D4 is okay for current implementations. Local only reports `absent` on `ENOENT` (`lib/storage/local/local-blob-store.ts:27-33`), and in-memory read faults become `unreadable` (`lib/storage/testing/in-memory-blob-store.ts:121-127`). Residual: there is no contract test that `provesAbsence === true` forbids non-absence `absent` results.

2. `docs/superpowers/specs/2026-08-11-serve-path-proven-absence-design.md:168-175` — B7 can pass vacuously unless the fake records object identity and exact principal per call. Write it with a decorator store that logs `{ thisStoreId, principalObject, key }` from inside `tryGet`, then assert both model and control entries share the same store id and same principal object/value.

3. `docs/superpowers/specs/2026-08-11-serve-path-proven-absence-design.md:177-180` — the mutation check is too narrow. Reverting the whole block only proves B3 is load-bearing. A subtler mutation, “control read uses `get` instead of `tryGet`,” can survive if the fake only scripts `tryGet` and leaves `get` returning bytes/null conveniently. The tests must fail on any unexpected method call and must distinguish absent vs unreadable through the same API production uses.

Share path: verified no charge. `app/s/[token]/route.ts` imports only read/render helpers, wraps the store as `ReadOnlyBlobStore`, and never imports `serve-doc` or calls reserve (`app/s/[token]/route.ts:1-15`, `:44-58`, `:102-110`).

PDF path: same precondition as HTML. It calls `loadSummaryForServe` before `resolveAndParse`, so markdown is read first (`app/api/pdf/[id]/route.ts:44-49`).
