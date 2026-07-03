# Stage 1C Spec — Codex Adversarial Review

**Date:** 2026-07-02
**Spec reviewed:** `docs/superpowers/specs/2026-07-02-stage-1c-supabase-adapters-design.md`
**Produced by:** Codex CLI (gpt-5.5)
**Context files read:** `docs/superpowers/specs/2026-07-01-cloud-publishing-architecture-design.md`, `supabase/migrations/0001_core_schema.sql`, `0005_reorder_helper.sql`, `0006_grants.sql`, `lib/storage/metadata-store.ts`, `lib/storage/local/local-metadata-store.ts`, `lib/storage/resolve.ts`, `lib/storage/principal.ts`, `lib/pipeline.ts` (lines 270–420)
**Tokens used:** 74,208

---

## Summary

Codex identified **4 Blocking**, **5 High**, and **2 Medium** findings.
The most severe cluster: the `writeIndex:417 → reorderVideos` mapping silently drops three JSONB
fields that are currently written at that call site; `max(position)+1` is not safe under concurrent
inserts; "regenerate on missing" is explicitly wrong for source-of-truth blobs (MD/slides);
and blob isolation is untestable end-to-end in 1C because auth→principal route wiring is deferred
while Supabase backend is enabled.

**Open-question answers** (spec §10):
- **Q1** (backfill-titles/playlistUrl threading): Finding 8 supersedes it — route principal wiring
  is the prerequisite gap. Backfill-titles/playlistUrl threading is secondary.
- **Q2** (regenerate-on-missing for expensive source blobs): **No** — Finding 7 rules this out.
  Source blobs must surface a repair state, not trigger a Gemini call.
- **Q3** (single bucket sufficiency): **Yes, single bucket is fine for 1C**, but the Storage RLS
  policy enforcing that isolation does not yet exist and must be a 1C deliverable (Finding 9).

---

## Finding 1: Async Conversion Proof Is Too Weak

**Severity:** High
**Spec section:** §1.1 decision 2, §3.3, §7

**Problem:** The spec says all ~20 call chains become awaited and that the local unit suite staying green proves regression safety. That does not prove async correctness because the local impl resolves immediately around synchronous code. Existing consumers use synchronous value access patterns — `store.readIndex(...).videos.map(...)`, `.find(...)`, destructuring, and `for (... of store.readIndex(...).videos)`. A missed `await` may be caught by TypeScript if all call sites are type-checked, but a green local runtime suite does not exercise delayed DB behavior, interleaving, or stale reads.

**Fix:** Add a deliberately delayed async fake `MetadataStore` in consumer tests, run `tsc --noEmit` as a required gate, and add lint/tests that fail on un-awaited `MetadataStore` promises. Include pipeline-specific tests around reads at lines 283, 290, 317, 388, and 406.

---

## Finding 2: Pipeline Read Sequence Has Stale-Read Races

**Severity:** High
**Spec section:** §3.3, §8 cases 2-3

**Problem:** `pipeline.ts` repeatedly re-reads the index across awaited work. In particular, serial assignment at line 317 reads current videos, then summary generation and blob writes happen before `upsertVideo`. With a real async/cloud backend, another job can insert during that window, causing duplicate `serialNumber`, duplicate filenames, or inconsistent `playlistIndex`. Local `job-registry` only guards by output folder in-process; it is not a distributed lock.

**Fix:** Move serial/filename allocation into a transactional method, e.g. `claimNextVideoSlot(principal, videoId, desiredSlug)` or a playlist-scoped advisory lock/row lock. Define whether concurrent ingestions for one playlist are rejected, serialized, or idempotently joined.

---

## Finding 3: `writeIndex` Mapping Drops Required Field Updates

**Severity:** Blocking
**Spec section:** §3.3 table, §3.1 interface

**Problem:** The spec maps `pipeline.ts:417` to `reorderVideos(order)`, but that call site does more than reorder. It rewrites every video's `playlistIndex`, write-once `videoPublishedAt`, and write-once `addedToPlaylistAt` fields. `reorderVideos` only updates the relational `position` column via the `reorder_videos` RPC; it does not merge those JSONB fields into `videos.data`. Cloud behavior would silently lose metadata that is currently persisted by the local write.

**Fix:** Add an explicit method such as `bulkUpdateVideoFields(principal, patches)` or `syncPlaylistMetadata(principal, items)` that atomically updates `position` and the three JSONB fields together. The spec's method table and the consumer conversion table must both be corrected. Test that line-417 behavior preserves all three fields for skipped/already-indexed videos.

---

## Finding 4: Reconcile Loop Is Not Atomic

**Severity:** High
**Spec section:** §3.2 `upsertVideo`, §3.3, parent §4.1 "Transactional metadata"

**Problem:** The reconcile block at `pipeline.ts:388-398` performs multiple `upsertVideo` calls in a `for ... of` loop. In cloud mode, each call is its own transaction, so a failure midway leaves some videos auto-archived/restored and others stale. The subsequent read at line 406 then observes a partial reconcile. Parent spec §4.1 explicitly requires transactional metadata — no read-modify-write that mirrors the local JSON file's TOCTOU behavior.

**Fix:** Replace the loop with one transactional method, e.g. `reconcilePlaylistMembership(principal, currentIds)` or a variant of `bulkUpdateVideoFields`, in a single DB transaction. Include conflict/retry semantics.

---

## Finding 5: `max(position)+1` Append Is Race-Prone

**Severity:** Blocking
**Spec section:** §3.2 `upsertVideo`, §8 case 2

**Problem:** New video append uses `COALESCE(max(position)+1, 0)`. Two concurrent inserts for the same playlist can both compute the same max and both attempt to commit the same `position`. The deferrable unique `(playlist_id, position)` constraint defers uniqueness to COMMIT within one transaction; it does not serialize independent transactions. One of the two concurrent commits will fail with a unique constraint violation. The spec defines no retry, lock, or conflict strategy for this case.

**Fix:** Use a playlist row lock (`SELECT ... FOR UPDATE` on the `playlists` row), a serializable transaction with retry, or an RPC that assigns positions server-side under lock. Add an integration test with concurrent `upsertVideo` calls for the same playlist.

---

## Finding 6: Blob `promote` Assumes Atomic Move Semantics

**Severity:** High
**Spec section:** §4.1 `promote`, §5

**Problem:** The spec says `promote` moves temp key to final key but does not define Supabase Storage semantics. The Supabase Storage JS client exposes a `move` method, but this is documented as a copy-plus-delete under the hood — not an atomic rename like a local filesystem `rename(2)`. A crash between copy and delete can leave both temp and final copies, only the temp copy, or only the final copy in inconsistent states.

**Fix:** Treat promote as non-atomic. Make the implementation idempotent: verify the final object exists after promote, tolerate the case where both temp and final exist (cleanup on GC sweep), and record an artifact state field (`pending | committed | promoted`) in Postgres so readers know whether finalization completed. Reference: https://supabase.com/docs/reference/javascript/storage-from-move

---

## Finding 7: "Regenerate Source Blob On Missing" Is Not Acceptable

**Severity:** Blocking
**Spec section:** §5, §10 Q2, parent §4

**Problem:** Section 5 says a committed row whose `get(finalKey)` returns `null` is "treated as not-yet-available, and the reader regenerates/re-renders." This treats all artifact classes uniformly, but the parent architecture's tiering (§4 of the cloud-publishing spec) explicitly distinguishes source-of-truth blobs (MD, slides) from derived caches (HTML, PDF). Regenerating MD means re-invoking Gemini, potentially producing different content, spending money, and making previous Obsidian exports diverge from the new version. For slides, hosted Stage 1 has no server-side pixel capture at all — regeneration is impossible.

**Answer to Q2:** No, "regenerate on missing" is not uniformly acceptable for 1C. Source blobs must surface a repair/error state, not silently trigger re-generation.

**Fix:** Split artifact handling: derived caches (HTML, PDF) may regenerate; source blobs (MD, slides) must surface a `repair_needed` state. Add an artifact status field in the video JSONB or in a separate artifact row (`pending | committed | promoted | missing | repair_needed`), and have the reader surface an error/warning UI rather than re-invoking Gemini on a missing source blob.

---

## Finding 8: Blob Isolation Is Under-Specified And Route Principal Wiring Is Deferred

**Severity:** Blocking
**Spec section:** §1.1 decision 5, §4.2, §4.4, §6, §7

**Problem:** The spec defers auth-to-principal route wiring but simultaneously allows `STORAGE_BACKEND=supabase`. Current routes derive principals from `outputFolder` request input via `getPrincipal(outputFolder)`, which is local-path semantics and returns the fixed `local` sentinel as the owner id. If cloud BlobStore receives a principal with `id = 'local'` and `outputFolder = '/Users/someone/data'`, object keys are constructed as `local/%2FUsers%2Fsomeone%2Fdata/${key}` — wrong owner, and potentially user-controlled path segments in the key. This leaves the cloud path untested end-to-end and silently misattributes ownership.

**Fix:** Do not permit `STORAGE_BACKEND=supabase` in app routes until principal derivation reads from Supabase Auth/session. For 1C, keep Supabase adapters exercised through integration tests only (with a test harness that injects a real auth JWT), not through the existing routes. Introduce a `getPrincipalFromSession()` contract that hard-fails when cloud backend is live but auth context is absent.

---

## Finding 9: Storage RLS Policy Is Missing From The Slice

**Severity:** High
**Spec section:** §4.2, §4.4, §7, parent §7.2

**Problem:** Existing migrations (0001–0006) define RLS for `profiles`, `playlists`, and `videos` only. There is no migration creating the private bucket or defining a `storage.objects` RLS policy. The spec says integration tests will cover blob isolation (user A cannot read/write user B's blobs), but there is no Storage policy that makes the `${owner_id}/...` prefix enforceable rather than merely conventional. Any authenticated user with a valid JWT can call the Storage API and attempt to read/write paths under arbitrary prefixes.

**Answer to Q3:** A single private bucket is sufficient for 1C, but the Storage bucket policy enforcing isolation must be a first-class 1C deliverable, not an implied future step.

**Fix:** Add a migration that creates the private bucket and a `storage.objects` policy restricting access so that the first key segment equals `auth.uid()` (for authenticated users) and the service role has explicit write access. Test cross-user read, write, list, move/promote, and delete in the integration suite.

---

## Finding 10: Empty-Read Parity Shape Is Ambiguous And Type-Contradictory

**Severity:** Medium
**Spec section:** §3.2 `readIndex`, §8 case 1

**Problem:** The spec says no-playlist-row returns "empty index in the exact shape `lib/index-store.readIndex` returns for an absent file." The local impl returns `{ playlistUrl: '', outputFolder, videos: [] }` (confirmed at `lib/index-store.ts:77`). However, `PlaylistIndexSchema` at `types/index.ts:1113` requires `playlistUrl: z.string().url()` — an empty string `''` is not a valid URL and will fail Zod validation. Additionally, in the cloud case, `outputFolder` must be derived from `principal.outputFolder` since there is no DB row. Neither the spec nor the schema has resolved this contradiction.

**Fix:** Define the exact empty-read shape as `{ playlistUrl: '', outputFolder: principal.outputFolder, videos: [] }`. Relax `PlaylistIndexSchema.playlistUrl` to accept the empty string for the absent case (or introduce a nullable variant), and add a shared `emptyPlaylistIndex(principal: Principal): PlaylistIndex` helper used by both local and cloud impls to guarantee shape parity.

---

## Finding 11: Backend Co-Selection Is Asserted, Not Enforced

**Severity:** Medium
**Spec section:** §2 module layout, §6 config & selection

**Problem:** The spec asserts that `getMetadataStore()` and `getBlobStore()` "return the matching bundle together — never a mixed local/cloud pair," but two independent getter functions can still read `STORAGE_BACKEND` lazily in separate module initializations, initialize in different orders, or be bypassed by direct imports of concrete stores. A mixed local/cloud pairing would be a data-integrity failure: a DB row pointing to a local file path, or a local file entry not reflected in Postgres.

**Fix:** Export a single `getStorageBundle(): { metadataStore: MetadataStore; blobStore: BlobStore }` singleton from `resolve.ts` that reads and validates `STORAGE_BACKEND` exactly once, validates all required Supabase env vars atomically when the cloud backend is selected, and is the only path for production code to obtain either store. Mark direct imports of concrete store classes as test-only via ESLint or barrel file convention.

---

## Severity Summary

| # | Finding | Severity |
|---|---|---|
| 3 | `writeIndex:417` mapping drops playlistIndex/videoPublishedAt/addedToPlaylistAt | **Blocking** |
| 5 | `max(position)+1` append race under concurrent inserts | **Blocking** |
| 7 | "Regenerate source blob on missing" unacceptable for MD/slides | **Blocking** |
| 8 | Blob isolation untestable end-to-end; route principal wiring deferred while cloud backend enabled | **Blocking** |
| 1 | Async conversion proof relies on local unit suite; no delayed-async test | **High** |
| 2 | Pipeline stale-read races across multiple awaited readIndex calls in main loop | **High** |
| 4 | Reconcile loop (lines 388-398) is not atomic in cloud mode | **High** |
| 6 | `promote` assumes atomic move; Supabase Storage move is copy+delete | **High** |
| 9 | Storage bucket RLS policy not defined in any migration | **High** |
| 10 | Empty-read parity shape ambiguous and contradicts `PlaylistIndexSchema` | **Medium** |
| 11 | Backend co-selection asserted but not enforced; two independent getters | **Medium** |
