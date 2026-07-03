# Stage 1C — Supabase Adapters (MetadataStore + BlobStore)

**Date:** 2026-07-02
**Status:** Draft v1 — for grill + Codex adversarial review, then implementation plan.
**Parent architecture:** `docs/superpowers/specs/2026-07-01-cloud-publishing-architecture-design.md` (§4.1, §7, §10 item 1C, §130).
**Depends on:** Stage 1A (storage seam extraction — `MetadataStore`), Stage 1B (auth + RLS schema + anonymous auth), both merged (PR #1).

---

## 1. Goal

Ship the two Supabase-backed capability contracts that make a cloud read/write path real — `SupabaseMetadataStore` (Postgres, on the 1B schema) and `SupabaseBlobStore` (Supabase Storage) — behind **async** interfaces, with the DB↔blob write-ordering consistency protocol (§130). The author's personal single-user local workflow stays **byte-for-byte unchanged** and remains the **default**; the cloud path is exercised by integration tests against a local Supabase stack, not yet through a live route.

### 1.1 Scope decisions (resolved during brainstorming 2026-07-02)

| # | Decision | Rationale |
|---|---|---|
| 1 | 1C covers **`MetadataStore` + `BlobStore`** + the DB↔blob consistency protocol only. | §4.1 flags the full five-contract bundle as "the single largest refactor"; these two are the ones that touch Postgres/Storage and the consistency protocol. Smallest coherent cloud read/write path. |
| 2 | **Async-ify the `MetadataStore` interface and convert all consumers within 1C.** Local impl wraps sync `index-store` calls in resolved Promises. | A Postgres impl is inherently async. Clean end state in one mechanical sweep; the existing unit suite staying green is the regression proof. |
| 3 | **Reshape the write interface into targeted transactional methods**; retire whole-index `writeIndex`. | Spec §125 forbids the cloud impl from mirroring the JSON file's read-modify-write TOCTOU behavior — reconcile logic must be conditional `UPDATE`s. Reuses 1B's `reorder_videos` RPC. |
| 4 | **Consistency = write-ordering (temp→verify→commit row→promote) + read-time tolerance** for a dangling row. **Background reconciliation sweep deferred.** | Ordered write prevents committing a row that points at a missing/partial blob; read-time tolerance handles the rare crash window. The sweep is operational hardening, and a crashed staging blob is inert (not user-visible). |
| 5 | **Slice = adapters + env selection + integration tests** against a local Supabase stack. App stays **local-default**; **auth→principal route wiring deferred**. | Smallest safe spine that proves cloud CRUD + consistency + RLS isolation without a risky app-wide cutover. Avoids re-expanding toward the over-scoping §4.1 warns against. |

### 1.2 Explicitly out of scope (later slices)

`SettingsStore`, `ExportTarget` (Obsidian/download), `TempWorkspace` (incl. `slide-crop-cache`, `.cache` scratch), the background reconciliation sweep, signed URLs (Stage-1 default is app-streaming, §149), auth→principal wiring on routes, and any hosted deployment. The app default remains local.

---

## 2. Module layout

Mirrors the 1A `lib/storage/` pattern:

```
lib/storage/
  metadata-store.ts            # interface — becomes async (existing, edited)
  blob-store.ts                # NEW interface
  principal.ts                 # existing, unchanged
  resolve.ts                   # env-selects local vs supabase bundle (edited)
  local/
    local-metadata-store.ts    # existing — methods become async (wrap sync) (edited)
    local-blob-store.ts        # NEW — wraps current -data FS layout, temp→rename atomicity
  supabase/
    supabase-metadata-store.ts # NEW — Postgres via the 1B schema
    supabase-blob-store.ts     # NEW — Supabase Storage, owner-scoped keys
    consistency.ts             # NEW — temp→verify→commit→promote helper, shared protocol
```

**Selection:** `resolve.ts` reads `STORAGE_BACKEND` (`local` | `supabase`, default `local`). `getMetadataStore()` and `getBlobStore()` return the **matching** bundle together — never a mixed local/cloud pair. No consumer knows which backend is live.

---

## 3. `MetadataStore` — async reshape + Postgres mapping

### 3.1 Interface (async, intent-specific)

```ts
interface MetadataStore {
  readIndex(p: Principal): Promise<PlaylistIndex>;
  setPlaylistMeta(p: Principal, meta: { playlistUrl: string; playlistTitle?: string }): Promise<void>;
  upsertVideo(p: Principal, video: Video): Promise<void>;
  updateVideoFields(p: Principal, id: string, fields: Partial<Video>): Promise<void>;
  reorderVideos(p: Principal, order: { video_id: string; position: number }[]): Promise<void>;
  bulkUpsertVideos(p: Principal, videos: Video[]): Promise<void>;
}
```

Whole-index `writeIndex` is **retired**. `Principal.id` → `owner_id`; `Principal.outputFolder` → `playlist_key`.

### 3.2 Postgres mapping (1B schema)

Schema recap: `playlists(id, owner_id, playlist_key, playlist_url, playlist_title, …)`, unique `(owner_id, playlist_key)`; `videos(playlist_id, owner_id, video_id, position, data jsonb, …)`, PK `(playlist_id, video_id)`, deferrable-unique `(playlist_id, position)`; RPC `reorder_videos(p_playlist_id uuid, items jsonb)` (SECURITY INVOKER, owner-guarded).

| Method | SQL / RPC |
|---|---|
| `readIndex` | Resolve playlist row by `(owner_id, playlist_key)`; `SELECT … FROM videos WHERE playlist_id = $1 ORDER BY position`. Reassemble `PlaylistIndex { playlistUrl, playlistTitle?, outputFolder, videos: [data…] }`. **No playlist row → empty index** in the exact shape `lib/index-store.readIndex` returns for an absent file (empty-read parity, 1B review L3). |
| `setPlaylistMeta` | `INSERT INTO playlists (owner_id, playlist_key, playlist_url, playlist_title) VALUES … ON CONFLICT (owner_id, playlist_key) DO UPDATE SET playlist_url = EXCLUDED.playlist_url, playlist_title = COALESCE(EXCLUDED.playlist_title, playlists.playlist_title)`. Creates the playlist row on first write. |
| `upsertVideo` | Resolve `playlist_id`; `INSERT INTO videos (…, position, data) VALUES (…, $pos, $data) ON CONFLICT (playlist_id, video_id) DO UPDATE SET data = EXCLUDED.data, updated_at = now()`. New video → `position = COALESCE(max(position)+1, 0)` (append). Existing video keeps its position (data-only update). |
| `updateVideoFields` | `UPDATE videos SET data = data || $fields::jsonb, updated_at = now() WHERE playlist_id = $1 AND video_id = $2`. Owner-scoped by RLS. jsonb-merge preserves untouched fields. |
| `reorderVideos` | `reorder_videos(playlist_id, items)` RPC — one transaction; the deferrable position constraint settles at COMMIT. |
| `bulkUpsertVideos` | Single transaction of `upsertVideo`-style upserts (used by serial migration). |

### 3.3 Consumer conversion

The 4 whole-index `writeIndex` call sites are re-expressed:

| Call site | Today | 1C |
|---|---|---|
| `lib/pipeline.ts:284` | `writeIndex({…playlistUrl, outputFolder, playlistTitle})` | `setPlaylistMeta({ playlistUrl, playlistTitle })` |
| `lib/playlists/backfill-titles.ts:36` | `writeIndex({…playlistTitle})` | `setPlaylistMeta({ playlistUrl, playlistTitle })` |
| `lib/pipeline.ts:417` | `writeIndex({…videos: videosWithIndex})` (reorder) | `reorderVideos(order)` |
| `lib/serial-migrate-exec.ts:18` | `writeIndex({…videos})` (bulk serial) | `bulkUpsertVideos(videos)` |

All ~20 `MetadataStore` call chains become `await`ed (`readIndex`, `upsertVideo`, `updateVideoFields` in `pipeline`, `archive`, `summary-audit`, `timestamp-audit`, `timestamp-repair`, `html-doc/*`, `dig/dig-section`, API routes). The local impl wraps existing sync `index-store` calls in `Promise.resolve(...)`, so behavior is unchanged and the unit suite is the regression proof.

**Note on `setPlaylistMeta` `playlistUrl`:** `backfill-titles` currently only sets the title; it must pass the existing `playlistUrl` (read from the index it already loaded) so the `NOT NULL` `playlist_url` column is satisfied on the ON CONFLICT path. Local impl ignores the extra field (title-only merge preserved).

---

## 4. `BlobStore` — contract + owner-scoped keys

### 4.1 Interface

Blobs are addressed by a **logical relative key**; each impl maps it to physical storage. Signing is omitted (Stage-1 default is app-streaming, §149; route wiring deferred).

```ts
interface StagedRef { principal: Principal; tempKey: string; finalKey: string; }

interface BlobStore {
  put(p: Principal, key: string, bytes: Buffer, contentType: string): Promise<void>;
  get(p: Principal, key: string): Promise<Buffer | null>;      // null = absent
  exists(p: Principal, key: string): Promise<boolean>;
  delete(p: Principal, key: string): Promise<void>;
  // consistency protocol (§5):
  putStaged(p: Principal, key: string, bytes: Buffer, contentType: string): Promise<StagedRef>;
  promote(ref: StagedRef): Promise<void>;
}
```

### 4.2 Key scheme

| | Logical key (callers unchanged) | Physical location |
|---|---|---|
| Local | `${baseName}.md`, `models/${id}.json`, `${videoId}/slide-01.png`, `${htmlFilename}`, `${baseName}.pdf` | `path.join(outputFolder, key)` — **byte-for-byte today's `-data` layout** |
| Supabase | same logical key | private bucket; object key `${owner_id}/${playlist_key}/${key}` (§7.2 storage-key isolation) |

The logical key is a relative artifact path. Local impl joins it under `outputFolder` (preserving today's filenames exactly); cloud impl prefixes it with the owner + playlist scope. **Key computation stays in the calling module** (it already computes `baseName`, `htmlFilename`, `videoId`, etc.); the `BlobStore` only maps logical→physical.

### 4.3 Extraction

Source-of-truth blob writes route through `BlobStore`:

| Blob | Site today |
|---|---|
| summary MD | `lib/pipeline.ts:103` |
| model JSON | `lib/html-doc/model-store.ts` |
| HTML doc | `lib/html-doc/generate.ts`, `lib/html-doc/rerender.ts` |
| PDF | `lib/pdf/generate-doc-pdf.ts` |
| slide images | `lib/dig/slides.ts` |

**Scratch/cache stays direct FS** (`lib/dig/slide-crop-cache.ts`, `.cache`) — deferred `TempWorkspace`. Local `BlobStore.put` keeps the existing temp-file→rename atomicity internally, so local durability is unchanged.

### 4.4 Path-safety

The existing `lib/paths/assert-within` guard (home-dir/output-folder containment) still applies to the **local** impl. The cloud impl derives the object key from server-side `owner_id`/`playlist_key`, never a client-supplied absolute path (§149 signed-URL rule spirit: no client-controlled key).

---

## 5. DB↔blob write-ordering consistency (§130)

A blob and its metadata row must never diverge. For any artifact-producing op (e.g. HTML generation writing `videos.data.summaryHtml`):

1. `putStaged` → upload to a **temp key** (`_staging/…`).
2. **Verify** the upload (byte length / `exists`).
3. **Commit** the DB row (`updateVideoFields(… summaryHtml: filename)`) — the row now claims the artifact.
4. `promote` → move temp key → final key.

**Read-time tolerance** covers the crash window between (3) and (4): a committed row whose `get(finalKey)` returns `null` is treated as **not-yet-available**, and the reader regenerates/re-renders (HTML/PDF are derived caches, §109) rather than surfacing a broken link. Source-of-truth blobs that are expensive to reproduce (MD, slides) are committed *before* their row references them via the same ordering, so a missing source blob likewise reads as "regenerate," never a hard error.

**Deferred:** the background sweep that GCs orphaned `_staging/` blobs and repairs dangling rows. A crashed staging blob is inert (not user-visible); GC is a later ops slice.

Local `BlobStore`'s temp→rename already satisfies the ordering; `consistency.ts` makes the sequence explicit and shared so both impls follow one protocol.

---

## 6. Config & selection

- `STORAGE_BACKEND` = `local` (default) | `supabase`, read in `resolve.ts`. `getMetadataStore()`/`getBlobStore()` return the matching bundle together.
- Supabase impls use the **authenticated/anon** client for user ops (RLS applies), per §192 — consistent with 1B. The integration harness drives them with a real user JWT.
- **Fail-fast env validation** (§252): when `STORAGE_BACKEND=supabase`, require the Supabase env vars (URL, anon key, and any bucket name) at startup; missing → hard error, not a silent local fallback.

---

## 7. Testing strategy

| Layer | Coverage |
|---|---|
| **Unit** (existing ~1505-test suite) | Local impls: async wrappers preserve behavior — the suite staying green is the regression proof for the consumer conversion. Supabase impls: mock the client; assert SQL/RPC shape, key computation, and empty-read parity shape. |
| **Integration** (local Supabase stack, 1B harness, `--runInBand`) | Real Postgres + Storage. Cloud CRUD round-trips; `reorderVideos` via the RPC; **RLS isolation** (user A cannot read/write user B's index rows *or* blobs); empty-read parity; owner-scoped blob key layout; `setPlaylistMeta` create-then-update. |
| **Consistency** | Inject a failure between commit-row (3) and promote (4); assert read-time tolerance treats the artifact as regenerable (no broken link), and that no committed row ever points at an unverified blob. |

**TDD:** adapters are external-API-boundary + data-integrity code → TDD **yes** (per `docs/dev-process.md`). Each task's plan file enumerates behaviors + edge cases (missing input, each external-call failure, mid-chain failure) before tests are written.

### 7.1 Mocking boundaries (per dev-process)

| Boundary | Mocked in |
|---|---|
| Supabase client (`@supabase/supabase-js`) | Unit tests for `SupabaseMetadataStore` / `SupabaseBlobStore` |
| Real Postgres + Storage | Not mocked — integration suite hits the local stack |
| `lib/index-store` (FS) | Not mocked for local-impl behavior parity; the existing suite already covers it |

---

## 8. Enumerated risks / edge cases (seed for task behavior tables)

| # | Case | Expected |
|---|---|---|
| 1 | `readIndex` when no playlist row exists | Empty `PlaylistIndex` in local-parity shape (not an error). |
| 2 | `upsertVideo` for a brand-new video | Appended at `max(position)+1`; row `owner_id` = principal. |
| 3 | `upsertVideo` for an existing video | Data replaced, **position unchanged**. |
| 4 | `updateVideoFields` merges partial fields | Untouched jsonb keys preserved (`data || fields`). |
| 5 | `reorderVideos` transiently duplicates a position | Settles valid at COMMIT (deferrable constraint); RLS/owner guard enforced by RPC. |
| 6 | User A calls any method against user B's playlist_key | RLS yields no row / no write; isolation test asserts it. |
| 7 | `setPlaylistMeta` first call then second call | INSERT then UPDATE; `playlist_url` NOT NULL satisfied both times. |
| 8 | Blob `get` for absent key | `null` (not throw). |
| 9 | Crash after commit-row, before promote | Reader sees `null` blob → regenerates; no broken link, no orphaned commit pointing at verified-missing data. |
| 10 | `STORAGE_BACKEND=supabase` with missing env | Fail-fast at startup, no silent local fallback. |
| 11 | Cloud blob key derivation | `${owner_id}/${playlist_key}/${key}`; never client-supplied absolute path. |
| 12 | Local impl behavior after async reshape | Identical to pre-1C (unit suite green). |

---

## 9. Success criteria

1. `MetadataStore` is async and intent-specific; whole-index `writeIndex` is gone; all consumers `await`; **unit suite green** (local behavior preserved).
2. `BlobStore` extracted; source-of-truth blob writes route through it; local layout **byte-for-byte unchanged**; scratch stays direct FS.
3. `SupabaseMetadataStore` + `SupabaseBlobStore` pass the integration suite on a local Supabase stack: CRUD, reorder-via-RPC, RLS isolation (rows **and** blobs), empty-read parity, owner-scoped keys.
4. DB↔blob write-ordering + read-time tolerance verified by a crash-window test.
5. `STORAGE_BACKEND` selects bundles; default `local`; fail-fast on missing Supabase env.
6. App default remains local; personal workflow unaffected. No route/auth-principal wiring, no background sweep, no signed URLs (all deferred).

---

## 10. Open questions for review

- **Q1 (grill/Codex):** `setPlaylistMeta` needs `playlistUrl` for the `NOT NULL` column on first insert; is threading it through `backfill-titles` (title-only intent today) the cleanest, or should the playlist row be guaranteed to exist before backfill runs?
- **Q2 (Codex):** does read-time tolerance need to distinguish an *expensive* missing source blob (MD/slides — expensive to reproduce) from a *cheap* missing cache blob (HTML/PDF), or is "regenerate on missing" uniformly acceptable for 1C given the local default?
- **Q3 (Codex):** is a single private bucket with `${owner_id}/…` key prefixes sufficient isolation for 1C (RLS-on-Storage via bucket policy), or does the spine need per-artifact-type buckets now?
