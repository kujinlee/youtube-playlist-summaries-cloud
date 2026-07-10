# Task 6 review — `resolveMagazineModel` serve-side materialize helper

**Commits:** `0cd5175` (impl) → `93f7b30` (money-path test depth)
**Gate:** single round Claude + Codex (money-adjacent, not a §8 trigger). Execution: SDD.

## Reviews — implementation SOUND (both); reviewers diverged on test depth (resolved by adding it)
**Claude task-review — Approved.** Verified against source: freshness gate `isFresh = order-sensitive title equality AND generatorVersion === GENERATOR_VERSION` (fresh → `ok`, no reserve, no Gemini); only `reserved` falls through to generate; all 5 RPC statuses mapped + `default` throws; `at_capacity` PJ004 returned as a value (not error → `if(error) throw` won't misfire); `reserved` branch **unconditionally** generates+`writeModelEnvelope`s (no re-charge-next-view); corrupt/schema-invalid cache → `readModelEnvelope` null → regenerate (not 500); AbortSignal threaded; `SERVE_CAPS` carries both magazine fields (won't fail closed); session-client-only (no service_role import). **F6 money proof genuine:** asserts the on-disk overwrite landed (`persisted.generatorVersion===GENERATOR_VERSION` + fresh `lead`, impossible under create-if-absent) AND the second resolve serves from cache with generate NOT called + `attempt_count===1`.

**Codex adversarial — implementation SOUND; tests need money-path proof depth.** Same implementation points verified. **Important (test-only):** B1 fresh-cache test asserted no-Gemini but not no-charge; status mapping only partially covered at the helper seam (`in_flight`/`attempts_exhausted`/`denied` untested). **Minor:** B4 corrupt-degrade not locked at the seam.

**Adjudication:** code sound (both agree); on a money-adjacent path the tests are the regression guard and the status-mapping seam is where a future edit could silently make a non-`reserved` status generate/charge → added the depth.

## Test-depth fix (`93f7b30`, test-only)
1. **B1 no-charge** strengthened — forces the lease to look expired before the fresh-cache re-resolve (closes a false-negative: a live lease would silently no-op a spurious reserve without bumping `attempt_count`), then asserts `attempt_count` stays 1. Fails if the `isFresh()` short-circuit were removed.
2. **Status-mapping seam** — new `tests/lib/html-doc/serve-doc-mapping.test.ts` (fake `supabaseClient.rpc` + fake `blobStore` + mocked generate): `denied`, `attempts_exhausted`, `in_flight`→busy (not landed), `in_flight`→ok (landed on re-read), + `reserved`-only-generates. Each fails if its guard breaks.
3. **B4 corrupt-cache** — malformed blob at `models/{base}.json` → `ok`, regenerate exactly once (no throw), persisted envelope now valid/fresh.

## Carry-forward → Task 7 (#21)
- **`base`/`videoId` coupling (Claude Minor):** the reserve RPC keys the charge on `p_video_id=videoId` while the cache reads/writes on `base`. In tests `base===videoId`; Task 7 must ensure `base` derives from `videoId` (else a doc could re-charge despite a cached model under a different base) — add an assertion/doc at the Task 7 call site.
- **`in_flight` full concurrency:** the landed→ok vs still-in-flight→busy sub-cases are now seam-tested with a fake client; Task 7's concurrent-caller test should still cover the real two-caller race.

## Result
Tests: RED→GREEN, unit 1727, integration 178 (2 pre-existing skips), `tsc` clean. Money path: only `reserved` spends, always upserts, all statuses mapped, self-heal proven, corrupt degrades. **Task 6 COMPLETE.**
