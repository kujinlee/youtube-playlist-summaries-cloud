# Stage 1C — Supabase Adapters (MetadataStore + BlobStore)

**Date:** 2026-07-02
**Status:** Draft v2 — hardened after grill (terminology) + Codex adversarial review (`docs/reviews/stage-1c-supabase-adapters-spec-codex.md`, 4 Blocking / 5 High / 2 Medium, all resolved below). Ready for implementation plan.
**Parent architecture:** `docs/superpowers/specs/2026-07-01-cloud-publishing-architecture-design.md` (§4.1, §7, §10 item 1C, §130).
**Depends on:** Stage 1A (storage seam — `MetadataStore`), Stage 1B (auth + RLS schema + anonymous auth), both merged (PR #1).
**Glossary:** storage-seam terms (Principal, owner, index key, output folder) live in `CONTEXT.md` → *Storage Seam*.

---

## 1. Goal

Ship the two Supabase-backed capability contracts that make a cloud read/write path real — `SupabaseMetadataStore` (Postgres, on the 1B schema) and `SupabaseBlobStore` (Supabase Storage) — behind **async, transactional** interfaces, with the DB↔blob write-ordering consistency protocol (§130). The author's personal single-user local workflow stays **byte-for-byte unchanged** and remains the **default**; the cloud path is exercised by integration tests against a local Supabase stack, **never through the existing routes** (which still lack auth→principal wiring).

### 1.1 Scope decisions

| # | Decision | Rationale |
|---|---|---|
| 1 | 1C covers **`MetadataStore` + `BlobStore`** + the DB↔blob consistency protocol only. | §4.1 flags the full five-contract bundle as "the single largest refactor"; these two touch Postgres/Storage and the consistency protocol. |
| 2 | **Async-ify the `MetadataStore` interface and convert all consumers.** Local impl wraps sync `index-store` calls in resolved Promises. Regression proof = unit suite green **plus** `tsc --noEmit` gate **plus** a deliberately-delayed async fake in consumer tests (F1). | A green sync-wrapped suite alone does not exercise delayed-DB interleaving; the delayed fake + type gate catch missed `await`s and stale reads. |
| 3 | **Reshape the write interface into targeted transactional methods**; retire whole-index `writeIndex`. `reorderVideos` is **not** in 1C (no consumer — F3); the `reorder_videos` RPC stays in place, unused, for a Stage-2 reorder UI. | §125 forbids mirroring the JSON file's read-modify-write TOCTOU. `pipeline:417` updates jsonb fields, not array order (see §3.4). |
| 4 | **Transactional primitives + a concurrency test.** New-video slot allocation (position **and** serial) happens in one transaction under a **playlist row-lock**; playlist-membership reconcile is a single transaction; the bulk 3-field update is one transaction. An integration test drives concurrent `upsertVideo`/append on one playlist. | Answers F2/F4/F5. This *is* the "transactional metadata, not file-mimicking" the parent §4.1/§125 demanded — not scope creep. |
| 5 | **Consistency = ordered write + non-atomic-`move`-safe `promote` + class-aware read.** Per-blob status lives in `videos.data` jsonb (`pending \| committed \| promoted \| repair_needed`). Missing **source** blob (MD/slides) → `repair_needed` surfaced, **never** silent regeneration; missing **derived-cache** blob (HTML/PDF) → regenerate. Background reconciliation sweep **deferred**. | Answers F6/F7. Supabase Storage `move` is copy+delete (not atomic); MD regen re-invokes Gemini (cost + drift), slides can't be recaptured on a hosted Stage-1 server. |
| 6 | **Slice = adapters + env selection + integration tests** against a local Supabase stack. App stays **local-default**; routes stay on the local principal. A `getPrincipalFromSession()` contract **hard-fails** if `STORAGE_BACKEND=supabase` but no auth context, so the cloud backend can never activate through an unwired route (F8). | Smallest safe spine proving cloud CRUD + consistency + RLS isolation without a risky app-wide cutover. |

### 1.2 Explicitly out of scope (later slices)

`SettingsStore`, `ExportTarget` (Obsidian/download), `TempWorkspace` (incl. `slide-crop-cache`, `.cache` scratch), the background reconciliation sweep, signed URLs (Stage-1 default is app-streaming, §149), auth→principal wiring **on routes** (a `getPrincipalFromSession()` *contract* is defined here, but routes are not converted), the reorder UI, and any hosted deployment. The app default remains local.

---

## 2. Module layout

Mirrors the 1A `lib/storage/` pattern:

```
lib/storage/
  metadata-store.ts            # interface — async + transactional (edited)
  blob-store.ts                # NEW interface
  principal.ts                 # Principal.outputFolder → indexKey (edited)
  resolve.ts                   # getStorageBundle() singleton + getPrincipalFromSession() (edited)
  empty-index.ts               # NEW — shared emptyPlaylistIndex(principal) (F10)
  local/
    local-metadata-store.ts    # methods become async (wrap sync) (edited)
    local-blob-store.ts        # NEW — wraps current -data FS layout, temp→rename atomicity
  supabase/
    supabase-metadata-store.ts # NEW — Postgres via the 1B schema
    supabase-blob-store.ts     # NEW — Supabase Storage, owner-scoped keys
    consistency.ts             # NEW — ordered-write + idempotent promote helper
supabase/migrations/
  0007_storage_bucket_rls.sql  # NEW — private bucket + storage.objects RLS policy (F9)
```

**Selection is a single enforced seam (F11):** `resolve.ts` exports **`getStorageBundle(): { metadataStore, blobStore }`** — reads `STORAGE_BACKEND` (`local` default | `supabase`) **once**, validates all Supabase env vars atomically when cloud is selected, and is the **only** production path to a store. A mixed local-metadata + cloud-blob pairing is structurally impossible. Direct imports of concrete store classes are test-only (barrel/ESLint convention).

---

## 3. `MetadataStore` — async, transactional interface

### 3.1 Interface

```ts
interface MetadataStore {
  readIndex(p: Principal): Promise<PlaylistIndex>;
  setPlaylistMeta(p: Principal, meta: { playlistUrl: string; playlistTitle?: string }): Promise<void>;

  // NEW-video allocation: one transaction under a playlist row-lock, assigns position
  // (=max+1) AND serial (=maxSerial+1) atomically and reserves the row. (F2/F5)
  claimVideoSlot(p: Principal, videoId: string): Promise<{ position: number; serial: number }>;

  upsertVideo(p: Principal, video: Video): Promise<void>;                 // finalize/replace; position preserved
  updateVideoFields(p: Principal, id: string, fields: Partial<Video>): Promise<void>;

  // pipeline:417 — merge exactly {playlistIndex, videoPublishedAt, addedToPlaylistAt}
  // across many videos in ONE transaction; array order / position untouched. (F3)
  bulkUpdateVideoFields(p: Principal, patches: { videoId: string; fields: Partial<Video> }[]): Promise<void>;

  // pipeline:388-398 — membership-driven archive/restore in ONE transaction. (F4)
  reconcilePlaylistMembership(p: Principal, currentPlaylistIds: string[]): Promise<void>;
}
```

Whole-index `writeIndex` and `reorderVideos` are **not** in the interface. `Principal.id` → `owner_id`; `Principal.indexKey` → `playlist_key`.

### 3.2 Postgres mapping (1B schema)

Schema recap: `playlists(id, owner_id, playlist_key, playlist_url, playlist_title, …)`, unique `(owner_id, playlist_key)`; `videos(playlist_id, owner_id, video_id, position, data jsonb, …)`, PK `(playlist_id, video_id)`, deferrable-unique `(playlist_id, position)`. DB `position` = **array/insertion order** (0001 comment), decoupled from the `Video.playlistIndex` jsonb field (§3.4).

| Method | SQL / RPC |
|---|---|
| `readIndex` | Resolve playlist by `(owner_id, playlist_key)`; `SELECT … FROM videos WHERE playlist_id=$1 ORDER BY position`; reassemble. **No playlist row → `emptyPlaylistIndex(principal)`** (§3.3). |
| `setPlaylistMeta` | `INSERT … ON CONFLICT (owner_id, playlist_key) DO UPDATE SET playlist_url=EXCLUDED.playlist_url, playlist_title=COALESCE(EXCLUDED.playlist_title, playlists.playlist_title)`. |
| `claimVideoSlot` | One transaction: `SELECT … FROM playlists WHERE id=$1 FOR UPDATE` (serializes appends for this playlist); compute `position=COALESCE(max(position)+1,0)` and `serial=COALESCE(max((data->>'serial')::int)+1,1)`; `INSERT` a reservation row (`data={id:videoId, serial}`) satisfying the id CHECK. Return `{position, serial}`. Implemented as a `SECURITY INVOKER` RPC so the lock+insert are atomic under caller RLS. |
| `upsertVideo` | Existing/reservation row: `UPDATE videos SET data=$data WHERE (playlist_id, video_id)` — **position preserved**. (New rows always arrive via `claimVideoSlot` first, so `upsertVideo` never allocates a position.) |
| `updateVideoFields` | `UPDATE videos SET data = data \|\| $fields::jsonb WHERE playlist_id=$1 AND video_id=$2`. |
| `bulkUpdateVideoFields` | One transaction: for each patch `UPDATE videos SET data = data \|\| $fields::jsonb …`. Position untouched. |
| `reconcilePlaylistMembership` | One transaction / RPC: set `data = data \|\| '{"archived":true,"removedFromPlaylist":true}'` for videos **not** in `currentPlaylistIds`, and the restore variant for those that are. |

All writes are owner-scoped by RLS (user client). `claimVideoSlot`/`reconcilePlaylistMembership` RPCs carry an explicit owner guard mirroring `reorder_videos` (defense-in-depth over caller-RLS).

### 3.3 Empty-read parity (F10)

Local `index-store.readIndex` returns `{ playlistUrl: '', outputFolder, videos: [] }` for an absent file — but `PlaylistIndexSchema.playlistUrl` is `z.string().url()`, which **rejects `''`**. Resolution:

- Add a shared **`emptyPlaylistIndex(p: Principal): PlaylistIndex`** returning `{ playlistUrl: '', outputFolder: p.indexKey, videos: [] }`, used by **both** local and cloud impls (guarantees identical shape).
- **Relax `PlaylistIndexSchema.playlistUrl`** to accept `''` for the absent case (or a nullable variant). This is a shared-`types` change and gets its own behavior test.

### 3.4 The two orderings (grill + F3)

- **DB `position` column** = array/insertion order in `PlaylistIndex.videos`; append-only (`claimVideoSlot`), never reshuffled by 1C.
- **`Video.playlistIndex`** = a *field inside* `videos.data` = the video's position in the **YouTube playlist**; re-derived each sync, write-preserved for removed videos.

`pipeline:417` maps over videos **preserving array order**, updating only the three jsonb fields → it is a **bulk field update**, not a reorder → `bulkUpdateVideoFields`. The UI sorts client-side, so `readIndex` must return **insertion order** (parity with local).

### 3.5 Consumer conversion

| Call site | Today (`writeIndex`/sync) | 1C |
|---|---|---|
| `pipeline.ts:284` | `writeIndex({…playlistUrl, playlistTitle})` | `await setPlaylistMeta({ playlistUrl, playlistTitle })` |
| `playlists/backfill-titles.ts:36` | `writeIndex({…playlistTitle})` | `await setPlaylistMeta({ playlistUrl, playlistTitle })` (threads existing `playlistUrl`) |
| `pipeline.ts:317` (serial alloc) + `:358` (new upsert) | `nextSerial(readIndex().videos)` then `upsertVideo` | `await claimVideoSlot(videoId)` → build video with returned `serial` → `await upsertVideo` |
| `pipeline.ts:388-398` (reconcile loop) | `for … upsertVideo({…archived})` | `await reconcilePlaylistMembership(currentPlaylistIds)` |
| `pipeline.ts:417` | `writeIndex({…videos: videosWithIndex})` | `await bulkUpdateVideoFields(patches)` |
| `serial-migrate-exec.ts:18` | `writeIndex({…videos})` | one transactional bulk update (variant of `bulkUpdateVideoFields`) |

All ~20 `MetadataStore` call chains become `await`ed. Local impl wraps existing sync `index-store` calls in `Promise.resolve(...)`; behavior is unchanged and the unit suite + `tsc` + delayed-async fake are the regression proof.

---

## 4. `BlobStore` — contract + owner-scoped keys

### 4.1 Interface

Blobs are addressed by a **logical relative key**; each impl maps it to physical storage. Signing omitted (Stage-1 default is app-streaming, §149).

```ts
type BlobStatus = 'pending' | 'committed' | 'promoted' | 'repair_needed';
interface StagedRef { principal: Principal; tempKey: string; finalKey: string; }

interface BlobStore {
  put(p: Principal, key: string, bytes: Buffer, contentType: string): Promise<void>;
  get(p: Principal, key: string): Promise<Buffer | null>;      // null = absent
  exists(p: Principal, key: string): Promise<boolean>;
  delete(p: Principal, key: string): Promise<void>;
  // consistency protocol (§5):
  putStaged(p: Principal, key: string, bytes: Buffer, contentType: string): Promise<StagedRef>;
  promote(ref: StagedRef): Promise<void>;   // idempotent; tolerates non-atomic move (F6)
}
```

### 4.2 Key scheme + isolation (F8/F9)

| | Logical key (callers unchanged) | Physical location |
|---|---|---|
| Local | `${baseName}.md`, `models/${id}.json`, `${videoId}/slide-01.png`, `${htmlFilename}`, `${baseName}.pdf` | `path.join(outputFolder, key)` — **byte-for-byte today's `-data` layout** |
| Supabase | same logical key | private bucket, object key `${owner_id}/${playlist_key}/${key}` |

- The `${owner_id}` segment is taken from the **server-side principal**, never client input. The logical key is validated (no `..`, no leading `/`) before composition.
- **Isolation is enforced, not conventional (F9):** `0007_storage_bucket_rls.sql` creates the private bucket and a `storage.objects` RLS policy requiring the **first key segment = `auth.uid()`** for authenticated/anon users; `service_role` gets explicit access. Integration tests exercise cross-user read/write/list/move/delete denial.

### 4.3 Extraction

Source-of-truth blob writes route through `BlobStore`: summary MD (`pipeline:103`), model JSON (`html-doc/model-store`), HTML (`html-doc/generate`, `rerender`), PDF (`pdf/generate-doc-pdf`), slide images (`dig/slides`). **Scratch/cache stays direct FS** (`slide-crop-cache`, `.cache`) — deferred `TempWorkspace`. Local `BlobStore.put` keeps temp→rename atomicity internally.

---

## 5. DB↔blob write-ordering consistency (§130)

A blob and its metadata must never diverge. Per-blob status lives in `videos.data` (e.g. `data.artifacts.summaryMd = { key, status }`).

**Ordered write** for an artifact-producing op:
1. `putStaged` → upload to a **temp key** (`${owner_id}/${playlist_key}/_staging/…`).
2. **Verify** the upload (byte length / `exists`).
3. **Commit** the DB row: `updateVideoFields(… artifacts.X = { key, status:'committed' })`.
4. `promote` → move temp→final; on success set `status:'promoted'`.

**`promote` is idempotent and non-atomic-safe (F6):** Supabase Storage `move` is copy+delete, so after a crash both temp and final may exist, or only one. `promote` re-checks the final object, tolerates temp-still-present (GC sweep — deferred — cleans it), and only advances status to `promoted` once the final object is confirmed.

**Class-aware read (F7):** for a row whose blob `get` returns `null`:
- **Derived cache** (HTML, PDF): treat as regenerable — re-render from MD (no Gemini). Safe.
- **Source of truth** (MD, slides): set/surface **`repair_needed`**; **never** re-invoke Gemini (cost + content drift) or attempt slide recapture (impossible on a hosted Stage-1 server). The reader/UI (later slice) shows a repair state.

**Deferred:** the background sweep that GCs orphaned `_staging/` blobs and repairs dangling rows. A crashed staging blob is inert (private, non-final).

Local `BlobStore`'s temp→rename already satisfies ordering; `consistency.ts` makes the sequence + idempotent promote shared across impls.

---

## 6. Config & selection

- `getStorageBundle()` (F11): reads `STORAGE_BACKEND` once (`local` default | `supabase`), returns `{ metadataStore, blobStore }` from one bundle. When `supabase`, **fail-fast** on any missing Supabase env var (URL, anon key, bucket) at startup — no silent local fallback.
- Supabase impls use the **authenticated/anon** client (RLS applies), per §192.
- **`getPrincipalFromSession()` (F8):** the cloud principal derives from the Supabase Auth session. It **hard-fails** if `STORAGE_BACKEND=supabase` but no auth context is present. Routes are **not** converted in 1C; they keep `getPrincipal(indexKey)` (local sentinel). Cloud adapters are reachable **only** via the integration test harness, which injects a real user JWT. This makes it structurally impossible to activate the cloud backend through an unwired route with `id:'local'`.

---

## 7. Testing strategy

| Layer | Coverage |
|---|---|
| **Unit** | Local impls: async wrappers preserve behavior. **Delayed-async fake `MetadataStore`** in consumer tests (F1) — resolves after a tick to expose missed `await`s / stale reads; pipeline reads at :283/:290/:317/:388/:406 specifically covered. Supabase impls: mock the client; assert SQL/RPC shape, key derivation, empty-read shape. **`tsc --noEmit` is a required gate.** |
| **Integration** (local Supabase stack, 1B harness, `--runInBand`) | Real Postgres + Storage with injected JWT. Cloud CRUD; `claimVideoSlot`/`reconcilePlaylistMembership`/`bulkUpdateVideoFields`; **RLS isolation** for rows **and** blobs (cross-user read/write/list/move/delete denial, F9); empty-read parity; owner-scoped keys; `setPlaylistMeta` create-then-update. |
| **Concurrency** (F2/F4/F5) | Concurrent `claimVideoSlot`/append on one playlist → no duplicate `position`/`serial`, no lost row (row-lock serializes); concurrent reconcile is atomic (no partial membership state). |
| **Consistency** (F6/F7) | Failure injected between commit (3) and promote (4): derived-cache missing → regenerates; **source missing → `repair_needed`, no Gemini call**; `promote` idempotent across a simulated copy-succeeded/delete-failed crash. |

**TDD:** adapters are external-API-boundary + data-integrity code → TDD **yes** (`dev-process.md`). Each task's plan file enumerates behaviors + edge cases (missing input, each external-call failure, mid-chain failure) before tests.

### 7.1 Mocking boundaries

| Boundary | Mocked in |
|---|---|
| Supabase client (`@supabase/supabase-js`) | Unit tests for the Supabase impls |
| Real Postgres + Storage | Not mocked — integration suite hits the local stack |
| `lib/index-store` (FS) | Not mocked for local-impl parity (existing suite covers it) |

---

## 8. Enumerated risks / edge cases (seed for task behavior tables)

| # | Case | Expected |
|---|---|---|
| 1 | `readIndex`, no playlist row | `emptyPlaylistIndex(principal)` (shape parity; schema accepts `playlistUrl:''`). |
| 2 | `claimVideoSlot`, concurrent callers, one playlist | Row-lock serializes; each gets a distinct `position`+`serial`; no unique-constraint failure. |
| 3 | `upsertVideo` on a reservation/existing row | Data replaced, **position preserved**; never allocates position. |
| 4 | `updateVideoFields` partial merge | Untouched jsonb keys preserved (`data \|\| fields`). |
| 5 | `bulkUpdateVideoFields` (pipeline:417) | All three fields (`playlistIndex`, `videoPublishedAt`, `addedToPlaylistAt`) preserved for every video, one txn; position untouched. |
| 6 | `reconcilePlaylistMembership` fails midway | Whole txn rolls back — no partial archive/restore. |
| 7 | User A targets user B's `playlist_key` | RLS + RPC owner guard → no row/write; isolation test asserts. |
| 8 | `setPlaylistMeta` first then second call | INSERT then UPDATE; `playlist_url` NOT NULL satisfied both times. |
| 9 | Blob `get`, absent key | `null` (not throw). |
| 10 | Crash after commit, before promote — **derived cache** | Reader regenerates from MD; no broken link. |
| 11 | Crash after commit, before promote — **source blob** | `repair_needed`; **no** Gemini/slide regeneration. |
| 12 | `promote` after copy-succeeded/delete-failed crash | Idempotent: final confirmed, status→`promoted`, stray temp tolerated (GC later). |
| 13 | Cross-user blob access (read/write/list/move/delete) | Denied by `storage.objects` RLS (first segment ≠ `auth.uid()`). |
| 14 | `STORAGE_BACKEND=supabase`, missing env | Fail-fast at startup. |
| 15 | `STORAGE_BACKEND=supabase` reached via a route (no session) | `getPrincipalFromSession()` hard-fails; never runs with `id:'local'`. |
| 16 | Local impl after async reshape | Identical to pre-1C (unit suite + delayed-fake green). |

---

## 9. Success criteria

1. `MetadataStore` is async + transactional; `writeIndex`/`reorderVideos` gone; all consumers `await`; **unit suite + `tsc` + delayed-async fake green**.
2. `BlobStore` extracted; source-of-truth writes route through it; local layout **byte-for-byte unchanged**; scratch stays direct FS.
3. `SupabaseMetadataStore` + `SupabaseBlobStore` pass the integration suite on a local stack: CRUD, transactional slot/reconcile/bulk methods, RLS isolation (rows **and** blobs via `0007`), empty-read parity, owner-scoped keys.
4. Concurrency test green (no duplicate position/serial, atomic reconcile).
5. Consistency verified: ordered write, idempotent non-atomic-safe `promote`, source→`repair_needed` / cache→regenerate.
6. `getStorageBundle()` is the sole store path; default `local`; fail-fast on missing cloud env; `getPrincipalFromSession()` hard-fails without auth; routes unchanged.
7. App default remains local; personal workflow unaffected. No route/auth wiring, no background sweep, no signed URLs, no reorder UI (all deferred).

---

## 10. Resolved review questions

- **Q1** (backfill-titles `playlistUrl` threading): resolved — `setPlaylistMeta` threads the existing `playlistUrl` (read from the index backfill already loads) to satisfy the `NOT NULL` column on the ON-CONFLICT insert. Secondary to F8 per Codex.
- **Q2** (regenerate-on-missing for source blobs): **No** (F7). Source blobs surface `repair_needed`; only derived caches regenerate.
- **Q3** (single bucket sufficiency): **Yes** for 1C — but the `storage.objects` RLS policy (`0007`) is a first-class 1C deliverable, not an implied future step (F9).

Full adversarial review: `docs/reviews/stage-1c-supabase-adapters-spec-codex.md`.
