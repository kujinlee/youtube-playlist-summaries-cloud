# Task 7 Review — integration suite (Approved, converged after 1 fix round)

Task review of `382af0f` (base `ecce5fe`); test-vacuity fixes `5de5ce5`.
Diff: `tests/integration/dig-cloud.test.ts` (new, 8 scenarios), `tests/integration/helpers/seed.ts` (+durationSeconds/youtubeUrl).

Test-authoring task → single Claude task-reviewer (sonnet), mandate = hunt vacuous money/idempotency assertions (these tests are the slice's end-to-end proof). Runs against REAL local Supabase; mocks only `@/lib/gemini`, `@/lib/transcript-source`, `generateDig`.

## Claude task-reviewer — verdict Needs fixes → converged after fixes
Confirmed all 8 scenarios present and correctly scoped; verified `jest.integration.config.ts:7` matches `tests/integration/**` (the suite is genuinely discovered, not silently skipped); `seedPromotedVideo` extension additive (existing callers unaffected). Praised: real blob-content reads, `SupabaseClient.prototype.rpc` spy filtered to `enqueue_job`, before/after DB snapshots, owner-isolation asserting 404 AND `enqueue` not called, suite-level money determinism (`beforeAll` pins ceilings+quota, `beforeEach` clears ledger/usage).

### Two ⚠️ (out-of-diff) — resolved by controller
- Owner-isolation 404 is real RLS (not a param short-circuit): confirmed in the T5 review — `loadSummaryForServe`→`resolveOwnedPlaylistKey` owner-asserts via the session client; the test uses a real non-owner `signInAs` session.
- Version-bump `'dig-0'` genuinely older than `digJobVersion()`: `DIG_GENERATOR_VERSION=9` (confirmed in T2), so `digJobVersion()='dig-9'` and `'dig-0'` is older.

## Findings & dispositions — all FIXED (`5de5ce5`, test-only)

### Important #1 — dedup test didn't verify its own `spend_ledger` claim
The test title/comment claimed "ledger + usage unchanged" but only snapshotted `usage_counters`; a spurious `spend_ledger` write on the 200-ready path (bypassing usage + the RPC) would have passed. **Fixed:** snapshot `spend_ledger` before/after and assert unchanged, alongside the usage snapshot. Still green → the dedup path writes neither table.

### Important #2 — version-bump test could pass for the wrong reason
`admin.from('jobs').insert(...)` used a bare `await`; supabase-js *resolves* `{data:null,error}` on insert failure (RLS/constraint/NOT-NULL), it doesn't reject. A silently no-op'd `'dig-0'` precondition would make the assertions (`202` + `used===1`) identical to a fresh enqueue — green, but no longer proving non-dedup-across-versions. **Fixed:** both direct `jobs.insert()` calls (version-bump + §9.2) now capture `{error}` and `throw`, guaranteeing the precondition lands (matching the seed helpers' convention).

### Minor — concurrency proved key-separation, not content-separation
Only `blob.exists()` per section; a swap bug (section 0's body under 132's key) would pass. **Fixed:** now `blob.get()` + `toContain('sectionId: 0')` / `'sectionId: 132')`.

### Deferred (Minors, rolled up)
- `as any` on `res.body` (lines 88/159) — bypasses response-shape typing; low-value, deferred.
- `beforeAll`/`beforeEach` setup mutations don't check `{error}` — brief-provided, consistent; harden in a future pass.

## Disposition
Converged after 1 fix round. Both Important vacuity gaps + the Minor closed; fixes are test-only strengthenings that still pass. No re-review dispatch — mechanical assertion additions on already-passing tests, authored and verified by the controller (8/8 green under the integration config, tsc clean). Full unit suite 2122, integration seed-helper regression 156/156 across 16 files.
