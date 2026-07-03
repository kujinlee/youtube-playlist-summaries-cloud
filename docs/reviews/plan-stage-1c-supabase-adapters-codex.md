# Adversarial Plan Review — Stage 1C Supabase Adapters

**Produced by:** Codex CLI (gpt-5.5) via `codex exec`
**Date:** 2026-07-02
**Plan reviewed:** `docs/superpowers/plans/2026-07-02-stage-1c-supabase-adapters.md`
**Supporting files read:** `supabase/migrations/0001_core_schema.sql`, `lib/pipeline.ts`, `lib/serial-migrate-exec.ts`, `lib/dig/slides.ts`, `lib/dig/dig-section.ts`, `lib/serial-assign.ts`, `lib/storage/local/local-metadata-store.ts`, `lib/storage/metadata-store.ts`, `lib/storage/resolve.ts`

---

## Summary

**3 Blocking, 2 High, 2 Medium, 1 Low.**

Three findings would cause runtime failures or data corruption if the plan is implemented as written: the `merge_video_data` RPC gap (Task 8 does not define them but Task 9 calls them), the `artifacts` jsonb shallow merge clobbering sibling artifact kinds, and the wrong logical key for dig slide blobs. Both High findings are test and spec gaps that will not be caught by `tsc` alone.

---

## Findings

### 1. Forward Reference Stubs — Task 7 (High)

Task 7 (`resolve.ts`) imports `SupabaseMetadataStore` and `SupabaseBlobStore` from Tasks 9–10, creating an explicit forward reference. The plan note at line 682 says "create minimal stub classes … throwing `not implemented`", but the implementation code at lines 656–664 instantiates these classes inside `getStorageBundle()` and **returns them typed as** `{ metadataStore: MetadataStore; blobStore: BlobStore }`. A constructor-only stub (empty class body) does **not** satisfy these interface types — `tsc --noEmit` will fail because the class does not implement all required methods.

**Fix:** The Task 7 stub must implement every method from the `MetadataStore` and `BlobStore` interfaces, each throwing `new Error('not implemented — stub for Task 7; filled in Task 9/10')`. All 7 `MetadataStore` methods + 6 `BlobStore` methods must be present. The plan should spell this out explicitly.

**Circular import risk:** Low. The proposed Task 9/10 code imports only contracts and helpers (`metadata-store.ts`, `blob-store.ts`, `empty-index.ts`) — not `resolve.ts` — so there is no circular dependency.

---

### 2. Task 4 — Write-Once Semantics Under jsonb `||` (High)

**2a. serial-migrate-exec.ts mapping:** The `runPhaseA` function at `lib/serial-migrate-exec.ts:15-18` reads the index, spreads each video to add `serialNumber`, and calls `store.writeIndex(principal, { ...index, videos })`. This writes the complete, updated video objects. The plan maps this to `bulkUpdateVideoFields` with only `{ serialNumber }`. If `merge_video_data_bulk` uses `data = data || p_fields` (jsonb shallow merge), a patch of `{ serialNumber: N }` overwrites only that top-level key while preserving others. This mapping is **not lossy** — it is actually safer than the full-replace approach.

**2b. videoPublishedAt / addedToPlaylistAt write-once semantics (the real risk):** `lib/pipeline.ts:411-416` computes write-once fields using `??`:
```ts
videoPublishedAt: v.videoPublishedAt ?? publishedMap.get(v.id),
addedToPlaylistAt: v.addedToPlaylistAt ?? addedMap.get(v.id),
```
The plan maps `pipeline:417` to `bulkUpdateVideoFields` with patches containing all three fields — `{ playlistIndex, videoPublishedAt, addedToPlaylistAt }`. If patches are built from `videosWithIndex` (which already applied the `??` logic), the write-once values in the patches are already correct. **However:** the generic `merge_video_data` RPC is planned as `data = data || p_fields`, and jsonb `||` overwrites top-level keys with **right-hand values**. If the patch includes `videoPublishedAt: 'X'` but the row already has `videoPublishedAt: 'Y'` (set on first ingest), the RPC will overwrite `Y` with `X`. The `??` guard only runs in TypeScript, not in the database.

**Fix:** Either (a) add an explicit guard in `merge_video_data` that does not overwrite already-set write-once fields (`p_fields` should not overwrite keys that are already non-null in `data`), or (b) add an integration test that asserts `videoPublishedAt` / `addedToPlaylistAt` are not overwritten on a second sync. Without this test the regression is invisible.

---

### 3. claimVideoSlot CHECK Constraint — Task 8 (Low)

The reservation row inserted by `claim_video_slot` has `data = jsonb_build_object('id', p_video_id, 'serialNumber', v_serial)` with `video_id = p_video_id` (plan lines 739-742). The `videos` table CHECK at `supabase/migrations/0001_core_schema.sql:35` requires `data->>'id' IS NOT NULL AND data->>'id' = video_id`. Both conditions are satisfied for any non-null, non-empty `p_video_id`. No fix needed.

---

### 4. merge_video_data RPC Gap — Task 8 (Blocking)

Task 8 is declared to produce only `claim_video_slot` and `reconcile_membership` (plan line 703), and its SQL defines only those two RPCs (lines 724 and 751). Task 9 immediately calls `merge_video_data` and `merge_video_data_bulk` at lines 893 and 899 without them existing in the database. The note at plan lines 917 and 1230 says "go back to Task 8 and add them" — but this makes Task 9 depend on **retroactively editing** a migration that was already committed and applied (`supabase db reset` was run in Task 8's Step 2).

**Fix:** Add `merge_video_data` and `merge_video_data_bulk` to Task 8's migration (`0007_storage_and_rpcs.sql`) explicitly as first-class content. Both should be `SECURITY INVOKER`, owner-guarded via playlist ownership check (matching `claim_video_slot`'s pattern), and granted to `authenticated, service_role`. Task 8's "Interfaces" header should list these RPCs alongside `claim_video_slot` / `reconcile_membership`.

---

### 5. Storage RLS — anon Access and List Operations (Medium)

The owner-prefix RLS policy at plan lines 716-719 is directionally correct: object key `<owner_id>/<indexKey>/<logicalKey>` means `split_part(name, '/', 1) = auth.uid()::text` correctly isolates owners. The `putStaged` tempKey `_staging/<key>` produces full object path `<owner>/<indexKey>/_staging/<key>`, so `split_part` still returns `<owner>` — no bypass on staging paths.

Two secondary issues:

**(a) `anon` access:** The policy grants `for all to authenticated, anon`. When a user is not signed in, `auth.uid()` is null, so `split_part(...) = null` is `UNKNOWN` (not true), denying writes. This is safe but the `anon` grant is noise if the app never supports anonymous sessions — remove it or document why it is intentional.

**(b) List operations:** The plan has no test for bucket listing. Supabase Storage applies RLS to list results, but this is not verified. Add a Task 12 test asserting that a user listing the `artifacts` bucket does not see objects belonging to another user's prefix.

---

### 6. jsonb Shallow Merge Clobbers Sibling Artifacts — Task 10 (Blocking)

`writeArtifact` (plan lines 1016-1029) calls `updateVideoFields` twice:

```ts
// first call
{ artifacts: { [opts.kind]: { key, status: 'committed' } } }
// second call
{ artifacts: { [opts.kind]: { key, status: 'promoted' } } }
```

If `merge_video_data` is implemented as `data = data || p_fields` (plan line 917), PostgreSQL jsonb `||` is a **top-level shallow merge**. The `artifacts` key in `data` is replaced wholesale by the `artifacts` key from `p_fields`. A video that already has:

```json
{ "artifacts": { "summaryMd": { "key": "...", "status": "promoted" }, "html": { ... } } }
```

After `writeArtifact` for `slide`:

```json
{ "artifacts": { "slide": { "key": "...", "status": "promoted" } } }
```

`summaryMd` and `html` entries are silently lost.

**Fix:** Replace `data = data || p_fields` in `merge_video_data` with a deep merge for the `artifacts` sub-object. Use `jsonb_set(data, '{artifacts,<kind>}', value)` for single-kind updates, or `data || jsonb_build_object('artifacts', (data->'artifacts') || p_fields->'artifacts')` for the artifacts sub-merge. The `writeArtifact` helper must be documented as requiring a deep-merge RPC, and this must be tested in Task 10's unit tests.

---

### 7. TDD Realism — pipeline-async.test.ts Underspecified (Medium)

The delayed-async fake at plan lines 381-395 (a 5ms macrotask delay per method) **will** catch missing `await` in the pipeline: reading `.videos` from an unresolved Promise yields a `Promise` object, and any call to `.map()` / `.length` / `.has()` on it would throw at runtime. This covers the main regression risk at `lib/pipeline.ts:290, 317, 388, 406`.

**However,** `pipeline-async.test.ts` is specified only as a prose comment stub at plan lines 399-405 ("Mock lib/gemini + lib/youtube at the lib boundary; inject delayedStore via getStorageBundle…"). It is underspecified for an implementor:

- Which YouTube/Gemini mocks to use, and what they return
- What `getStorageBundle` returns (it still imports singletons in Task 4 — the plan note at line 407 says the mock target changes at Task 7)
- What the final index state should look like (serialNumber, playlistIndex, etc.)
- That `alreadyIndexed` behavior is covered (second call must skip)

**Fix:** Write out the test body in Task 4 with at least 3 concrete assertions (index has videos with correct serialNumber, no duplicate entries on re-run, store call count matches expected). The prose stub may be acceptable if an "enumerate behaviors" table is created first (per the per-task checklist), but that table is currently absent for pipeline-async.

---

### 8. Dig Slides Logical Key — Wrong Path (Blocking)

Plan line 567 says the slide blob logical key is `${videoId}/slide-NN.png`. The actual code:

- `lib/dig/dig-section.ts:67`: `assetsRoot = path.join(outputFolder, 'assets')`
- `lib/dig/slides.ts:158`: asset filename = `` `${sectionId}-${sec}-${end}.jpg` `` (not `slide-NN.png`)
- `lib/dig/slides.ts:163`: asset written to `path.resolve(assetsRoot, videoId, assetName)` = `<outputFolder>/assets/<videoId>/<sectionId>-<sec>-<end>.jpg`
- `lib/dig/slides.ts:175`: markdown reference = `` `assets/${videoId}/${assetName}` ``

For `LocalFsBlobStore` to reproduce the current byte-for-byte layout, the logical key must be:

```
assets/${videoId}/${sectionId}-${sec}-${end}.jpg
```

not `${videoId}/slide-NN.png`. With the wrong key, `LocalFsBlobStore.put(p, key, …)` writes to `path.join(p.indexKey, '${videoId}/slide-NN.png')` = `<outputFolder>/<videoId>/slide-NN.png`, which is neither the current path nor what the HTML renderer (`render-dig-deeper.ts:103`) expects (`assets/` prefix is required for the containment check to pass).

**Fix:** Correct the logical key in plan Task 6 ("Slide logical key: `assets/${videoId}/${assetName}`") and update the Task 6 conversion rule to pass `key = 'assets/' + videoId + '/' + assetName` to `blobStore.put`. The path parity test must verify the physical file lands at `path.join(indexKey, 'assets', videoId, assetName)`.

---

## Summary Table

| # | Area | Rating | Task(s) | File:Line |
|---|------|--------|---------|-----------|
| 1 | Forward reference stubs underspecified | **High** | T7 | plan:682 |
| 2a | serial-migrate-exec bulkUpdateVideoFields mapping | Low | T4 | serial-migrate-exec.ts:15-18 |
| 2b | Write-once jsonb `\|\|` overwrites videoPublishedAt | **High** | T4, T9 | pipeline.ts:411-417, plan:917 |
| 3 | claimVideoSlot CHECK constraint | Low | T8 | 0001_core_schema.sql:35 |
| 4 | merge_video_data RPCs missing from Task 8 migration | **Blocking** | T8, T9 | plan:703, 893, 899 |
| 5 | Storage RLS anon grant + list untested | Medium | T8, T12 | plan:717 |
| 6 | writeArtifact clobbers sibling artifact kinds via shallow merge | **Blocking** | T10 | plan:1022-1028 |
| 7 | pipeline-async.test.ts is a prose stub — underspecified | Medium | T4 | plan:399-405 |
| 8 | Dig slide logical key missing `assets/` prefix, wrong filename format | **Blocking** | T6 | plan:567, dig-section.ts:67 |

---

## Recommended Actions Before Proceeding

**Blocking (must fix before Task 4 begins):**
- Finding 4: Add `merge_video_data` + `merge_video_data_bulk` to Task 8's SQL block as first-class content.
- Finding 6: Replace the shallow-merge RPC design in `writeArtifact` with `jsonb_set`-based deep merge for the `artifacts` sub-object.
- Finding 8: Correct the dig slide logical key to `assets/${videoId}/${assetName}` in Task 6 conversion rules and the local parity test.

**High (must fix; can be addressed in-task but must not be merged without resolution):**
- Finding 1: Expand the Task 7 stub note to list all 13 interface methods that must be present.
- Finding 2b: Add an integration test in Task 11 asserting `videoPublishedAt` / `addedToPlaylistAt` are not overwritten on a second sync.

**Medium (present for user decision):**
- Finding 5: Remove `anon` from the RLS policy or document intent; add a list-isolation test.
- Finding 7: Write out the `pipeline-async.test.ts` body (3+ concrete assertions) before Task 4 implementation begins.
