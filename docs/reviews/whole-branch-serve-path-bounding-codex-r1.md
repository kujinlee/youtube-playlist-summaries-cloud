<!-- codex-review: model=gpt-5.5 -->

**Blocking**
None.

**High**
None.

**Medium**
None.

**Low**
1. Migration 0024 drops any check constraint whose definition mentions `lease_ttl_seconds`, including operator-added constraints unrelated to this floor.
`supabase/migrations/0024_lease_covers_serve.sql:27`

Failure scenario: a live DB has an additional policy check like `lease_ttl_seconds <= 3600`; migration 0024 runs; the loop drops it because it matches `%lease_ttl_seconds%`; only the new lower-bound check is recreated, so the upper-bound guard is lost.

Premises:
`[VERIFIED: supabase/migrations/0024_lease_covers_serve.sql:27] "for v_name in"`
`[VERIFIED: supabase/migrations/0024_lease_covers_serve.sql:28] "select conname from pg_constraint"`
`[VERIFIED: supabase/migrations/0024_lease_covers_serve.sql:30] "and pg_get_constraintdef(oid) ilike '%lease_ttl_seconds%'"`
`[VERIFIED: supabase/migrations/0024_lease_covers_serve.sql:32] "execute format('alter table guardrail_config drop constraint %I', v_name);"`
`[VERIFIED: supabase/migrations/0024_lease_covers_serve.sql:49] "alter table guardrail_config"`
`[VERIFIED: supabase/migrations/0024_lease_covers_serve.sql:50] "add constraint guardrail_config_lease_ttl_covers_serve check (lease_ttl_seconds >= 156);"`

Caller reaching state: migration deployment/replay against a live database with an extra `lease_ttl_seconds` check.

Proposed fix: drop only the known old constraint and this migration’s own constraint, or recreate/preserve non-floor constraints after tightening the lower bound.

**Guard Classification**
`callRpcBounded` timeout: SEQUENCE/infrastructure, reconciled as `{ ok:false, reason:'timeout' }`, not success. `[VERIFIED: lib/serve-rpc.ts:48] "if (raced.kind === 'timeout') {"` `[VERIFIED: lib/serve-rpc.ts:50] "return { ok: false, reason: 'timeout' };"`

Reserve timeout: SEQUENCE, reconciled to retryable `busy`, not raw rejection after possible spend. `[VERIFIED: lib/html-doc/serve-doc.ts:84] "if (!reserve.ok) {"` `[VERIFIED: lib/html-doc/serve-doc.ts:90] "return { status: 'busy' };"`

Reserve returned error: SHAPE/system error, rejected before generation. `[VERIFIED: lib/html-doc/serve-doc.ts:85] "if (reserve.reason === 'error') throw reserve.cause;"`

Serve budget wrapper: SHAPE/caller contract, TypeScript-required positional budget. `[VERIFIED: lib/gemini.ts:601] "export async function generateMagazineModelForServe("` `[VERIFIED: lib/gemini.ts:604] "budget: ServeBudget,"`

Migration floor: SHAPE/config wrong, rejects unsafe config. `[VERIFIED: supabase/migrations/0024_lease_covers_serve.sql:50] "add constraint guardrail_config_lease_ttl_covers_serve check (lease_ttl_seconds >= 156);"`

Write timeout: SEQUENCE, caller-side wait bound only; failed put is classified through the catch path and kept if metered. `[VERIFIED: lib/html-doc/model-store.ts:81] "await Promise.race(["` `[VERIFIED: lib/html-doc/model-store.ts:82] "blobStore.put(principal, MODEL_KEY(base), bytes, 'application/json'),"` `[VERIFIED: lib/html-doc/model-store.ts:76] "() => reject(new DOMException(\`model put exceeded ${timeoutMs}ms\`, 'TimeoutError')),"`

Settle retry: SEQUENCE, retries only refund; failed settle returns false and is not treated as success by callers. `[VERIFIED: lib/html-doc/serve-doc.ts:168] "const attempts = released ? 2 : 1;"` `[VERIFIED: lib/html-doc/serve-doc.ts:176] "if (out.ok) return true;"` `[VERIFIED: lib/html-doc/serve-doc.ts:179] "return false;   // caller must NOT claim a refund it could not apply"`

**Attacked And Held**
Refund rule held: `[VERIFIED: lib/html-doc/serve-doc.ts:145] "const released = releaseGateOpen()"` `[VERIFIED: lib/html-doc/serve-doc.ts:146] "&& classifyGeminiFailure(err, signal) === 'release'"` `[VERIFIED: lib/html-doc/serve-doc.ts:147] "&& !billing.metered;"`. 429/503 still classify release. `[VERIFIED: lib/gemini-failure.ts:5] "const RELEASE_STATUSES = new Set([429, 503]);"` `[VERIFIED: lib/gemini-failure.ts:81] "if (e instanceof GoogleGenerativeAIFetchError && RELEASE_STATUSES.has((e as { status?: number }).status ?? -1)) {"`

Local generation held: `[VERIFIED: lib/html-doc/generate.ts:40] "const model = await generateMagazineModel("` omits serve budget, while default `generateJson` timeout remains `[VERIFIED: lib/gemini.ts:267] "timeoutMs = REQUEST_TIMEOUT_MS,"` and `REQUEST_TIMEOUT_MS` is `[VERIFIED: lib/gemini.ts:105] "const REQUEST_TIMEOUT_MS = 60_000;"`.

Residual window is real and named: `writeModelEnvelopeWithin` bounds wait, not upload. `[VERIFIED: lib/storage/supabase/supabase-blob-store.ts:22] "async put(p: Principal, key: string, bytes: Buffer, contentType: string): Promise<void> {"` `[VERIFIED: lib/storage/supabase/supabase-blob-store.ts:23] "const { error } = await this.b().upload(this.objectKey(p, key), bytes, { contentType, upsert: true });"` The residual is late put after timeout until it lands; another producer can be admitted after lease expiry if no fresh model is visible. This is accepted and pinned, not closed.

Validation run:
`npx tsc --noEmit` passed.
`npm test -- --runInBand` passed: 262 suites, 2638 tests.
`npm run test:integration -- serve-config-invariant` passed.
`npm run test:integration -- serve-model-unreadable` passed.
`npm run test:integration -- serve-doc-materialize` passed when run sequentially.
`npm run test:integration -- reservation-release` passed when run sequentially.
Mutation: changed refund settle attempts to `1`; `tests/lib/html-doc/serve-doc-mapping.test.ts` failed on `Expected: 2, Received: 1`; restored and reran green.

Verdict: `CONVERGED`
