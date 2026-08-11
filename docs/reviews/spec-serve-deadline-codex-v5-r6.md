<!-- codex-review: model=gpt-5.5 -->

**Blocking [v5-REGRESSION] — Late-`put` overwrite is still unbounded because freshness does not check `sourceMdHash`.**  
Spec: `docs/superpowers/specs/2026-08-10-serve-path-deadline-design.md:284-286`, test claim at `:451-454`.  
Code checked: `lib/html-doc/read-model.ts:20-24`, `:29-38`; `app/s/[token]/route.ts:81-89`; existing regression note in `tests/lib/html-doc/section-identity-after-resummarize.test.ts:98-109`.

Concrete failure: A generates from old MD with titles `['A','B']`; its `put` times out client-side. B later generates from changed MD with the same titles and writes a correct envelope. A’s abandoned upload lands last with `upsert:true`. `readFreshMagazineModel` only checks `sameTitles(...) && generatorVersion === GENERATOR_VERSION`, so owner/share paths serve A’s stale model as fresh. No regeneration is triggered. v5’s H2 fix is false.

**Blocking [v5-REGRESSION] — Settle timeout can silently revoke the existing refund rule.**  
Spec: `docs/superpowers/specs/2026-08-10-serve-path-deadline-design.md:169-171`, `:401-420`.  
Code checked: `lib/html-doc/serve-doc.ts:128-134`; `supabase/migrations/0020_reservation_release.sql:277-298`; refund tests at `tests/integration/serve-doc-materialize.test.ts:278-303`.

Concrete failure: reserve succeeds, Gemini throws a not-metered 503, `released = true`, then `settle_serve_model(..., true).abortSignal(timeout)` times out and the SQL statement does not commit. `serve_owner_budget.spent_cents` and `spend_ledger.reserved_cents` remain +6, `serve_model_charge.release_token` remains set, and the caller loses the token. A later reclaim overwrites that token and charges again; no reaper refunds the intended release. v5 says “refund rule unchanged” and “reservation clears when statement commits, or the lease expires and the row is reclaimed”; that does not reconcile the ledgers when the release settle never commits.

**High [v5-REGRESSION] — `opts.serve?` repeats the optional-boundary propagation failure.**  
Spec: `docs/superpowers/specs/2026-08-10-serve-path-deadline-design.md:177-185`, `:440-445`.  
Code checked: current callers at `lib/html-doc/serve-doc.ts:112-116`, `lib/html-doc/generate.ts:40-43`, `lib/gemini.ts:246-259`, `:499-549`; checklist warning at `docs/process-checklists.md:64-68`.

Concrete failure: implementation adds `generateMagazineModel(..., opts?: { serve?: ... })` and `generateJson(..., timeoutMs?)`, but the serve caller keeps passing only `{ caps, signal, billing }`. TypeScript accepts it, local/default behavior remains unchanged, direct `generateMagazineModel` tests with `opts.serve` pass, but production serve still uses 3 attempts at 60s while the floor assumes 2 attempts at 50s. The serve boundary needs a required serve-specific option or a separate serve wrapper so omission is a compile-time failure.

**Medium — Reserve timeout handling is bounded, but v5 understates the user-visible paid lock.**  
Spec: `docs/superpowers/specs/2026-08-10-serve-path-deadline-design.md:164-168`, `:414-416`.  
Code checked: `supabase/migrations/0020_reservation_release.sql:217-254`, `lib/html-doc/serve-doc.ts:73-99`.

Concrete failure: reserve commits and charges, but the client times out before receiving `release_token`. The user sees `busy`; no producer exists; immediate retries see `in_flight` until lease expiry; retries after expiry can burn another 6¢ and another attempt. This is bounded by `max_serve_attempts` and budget caps, but “single-flight is preserved” is the wrong safety explanation: the system has created an empty paid lease, not one in-flight producer. The spec should state the exact state and retry consequence.

**Medium — §5’s “bounded term aborts” test is wrong for `put`.**  
Spec: `docs/superpowers/specs/2026-08-10-serve-path-deadline-design.md:431-434`.  
Code checked: `lib/storage/supabase/supabase-blob-store.ts:22-24`.

Concrete failure: `blobStore.put` maps to Supabase Storage `upload(..., { upsert: true })` with no signal. v5 correctly says elsewhere the timeout is a caller-side race, but the test section says `put` should “abort at its timeout” and assert error identity. That test either cannot be implemented truthfully or will assert the wrapper timeout, not upload cancellation. This matters because the late-write hazard depends on the upload continuing.

Verified non-findings: installed `@supabase/postgrest-js` is `2.109.0`; `rpc()` returns a `PostgrestFilterBuilder` with `abortSignal(signal): this` in `node_modules/@supabase/postgrest-js/dist/index.d.mts:5246-5254` and `:1408`. The floor/deploy number was consistently updated to `156` in the reviewed spec sections. The migration literal anti-drift assertion is implementable by parsing SQL and importing `SERVE_FLOOR_SECONDS`.

NOT CONVERGED.
