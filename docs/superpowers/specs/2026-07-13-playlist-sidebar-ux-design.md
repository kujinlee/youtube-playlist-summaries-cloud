# Playlist Sidebar UX — Design Spec

**Date:** 2026-07-13
**Branch:** `feat/playlist-sidebar-ux`
**Status:** Draft (Phase 1) — pending dual adversarial review + user review
**Slice after:** cloud dig-generation (PR #15) + cloud-run-blockers fix (PR #16)

---

## 1. Goal

Make the cloud playlist sidebar usable by fixing two defects the first live run surfaced:

1. **Naming (BUG-6):** cloud playlists render "Untitled playlist" because the cloud ingest
   path never fetches/persists the playlist title. Fix forward (persist at ingest) **and**
   backfill existing null-title rows so the user's current playlists get real names.
2. **Delete:** there is no way to remove a playlist. Add a **full hard-delete** (user-chosen
   scope): DB rows + Storage blobs + share tokens gone, in-flight jobs quiesced, owner-scoped,
   RLS-safe, behind a confirmation.

Both are **cloud-only** (the sidebar lives in `components/cloud/`; `STORAGE_BACKEND=supabase`).

## 2. Non-goals

- Paged/batched ingestion for playlists > 50 (separate spec).
- Soft-delete / trash / undo. The user explicitly chose **full hard-delete** — deletion is
  irreversible by design.
- Renaming a playlist to an arbitrary user string (title comes from YouTube).
- Deleting individual videos from a playlist (only whole-playlist delete).
- Local-backend playlist delete UI (local flow is filesystem-based and out of scope).

## 3. Grounding (verified against code)

| Fact | Source |
|---|---|
| Cloud ingest sets only `owner_id, playlist_key, playlist_url` | `lib/storage/supabase/supabase-metadata-store.ts:182` `resolvePlaylistId` |
| `playlist_title` column: `text`, nullable, no default | `supabase/migrations/0001_core_schema.sql:14` |
| Title fetch fn: `fetchPlaylistTitle(listId, apiKey): Promise<string>` (falls back to listId) | `lib/youtube.ts:114` |
| Title persist fn: `setPlaylistMeta(p, {playlistUrl, playlistTitle?})` upsert on `(owner_id, playlist_key)` | `supabase-metadata-store.ts:65` |
| Producer has `apiKey = process.env.YOUTUBE_API_KEY` + `extractPlaylistId(url)` in scope | `lib/job-queue/producer.ts:44,45,90` |
| Sidebar fallback `p.playlistTitle ?? 'Untitled playlist'` | `components/cloud/PlaylistSidebar.tsx:92` |
| `videos.(playlist_id, owner_id) → playlists(id, owner_id) ON DELETE CASCADE` | `supabase/migrations/0001` videos block |
| `jobs.(playlist_id, owner_id) → playlists(id, owner_id) ON DELETE CASCADE` | `0009` |
| Artifact metadata lives in `videos.data` JSONB (no separate table) — cascades with videos | `0007` `merge_video_data` |
| **`share_tokens.playlist_id` has NO FK** (plain column); table is service-role-only | `0013_share_tokens.sql:10,16-18` |
| `authenticated` has `select, insert, update, delete on playlists` | `0006_grants.sql:17` |
| RLS `playlists_owner for all using (owner_id = auth.uid())` | `0002_rls_policies.sql:4-5` |
| Blob object key: `<owner_id>/<playlist_key>/<logical-key>` (playlist_key = list-id) | `supabase-blob-store.ts:11-14` |
| `BlobStore` has `delete(one key)` — **no list, no prefix/bulk delete** | `lib/storage/blob-store.ts:7-14` |
| Dig blobs nest: `dig/<base>/<sectionId>.rV.md` → cleanup must **recurse** | `lib/dig/cloud/dig-blob-key.ts:22` |
| Cancel RPC `request_cancel_job(p_job_id)` (owner-guarded, queued→cancelled/active→flagged) | `0010_cancel_job_rowcount.sql:7-20` |
| Playlist-wide cancel loop already exists | `app/api/jobs/cancel/route.ts:29-34`, `SupabaseJobQueue.listByPlaylist/requestCancel` |
| Route pattern: `cookies()` → `createServerSupabase` → `getUser()` (401) → `getStorageBundle({supabaseClient})` | `app/api/playlists/route.ts` |
| Modal template (focus trap, Esc, returnFocus, submit guard) | `components/cloud/NewPlaylistModal.tsx` |

## 4. Feature A — Playlist naming (BUG-6)

### A1. Forward fix (persist title at ingest)

In `enqueuePlaylist` (`producer.ts`), after `resolvePlaylistId` succeeds, fetch and persist the
title. `extractPlaylistId(playlistUrl)` (already imported and called for validation) yields the
list-id; `apiKey` is already in scope.

```ts
const playlistId = await sessionBundle.metadataStore.resolvePlaylistId(principal, playlistUrl);
// BUG-6: persist the human-readable title (best-effort; never fail ingest on a title miss)
try {
  const listId = extractPlaylistId(playlistUrl);
  const playlistTitle = await fetchPlaylistTitle(listId, apiKey);
  await sessionBundle.metadataStore.setPlaylistMeta(principal, { playlistUrl, playlistTitle });
} catch { /* leave title null; backfill will retry */ }
```

- **Best-effort:** a title fetch failure must **not** fail ingestion (videos still enqueue). The
  row keeps `playlist_title = NULL` and the backfill path (A2) retries later.
- `setPlaylistMeta` upserts on `(owner_id, playlist_key)`, so it updates the row `resolvePlaylistId`
  just created (same key) without clobbering `playlist_url`.
- Idempotent: re-ingesting the same playlist re-sets the same title.

### A2. Backfill existing null-title rows

New owner-scoped route **`POST /api/playlists/backfill-titles`** (cloud branch):

1. List the caller's playlists (RLS-scoped session client); select those with `playlist_title` null.
2. For each, `fetchPlaylistTitle(playlist_key, YOUTUBE_API_KEY)` and persist via `setPlaylistMeta`.
   Per-playlist try/catch — a YouTube failure skips that row (retried next time), never 500s the
   batch.
3. Return `{ updated: number, attempted: number }`.

**Trigger (decision D1 — default: auto-on-mount):** `PlaylistSidebar`, after loading playlists,
if **≥1** has a null `playlistTitle`, fires `backfillPlaylistTitles()` **once per mount**, then
re-fetches the list so names appear. Self-healing, no manual step, no cost when all titles present.

- Idempotent (only touches null-title rows); safe to call repeatedly.
- Fully null-safe: read path unchanged; the `?? 'Untitled playlist'` fallback still covers a row
  whose title genuinely can't be fetched.

## 5. Feature B — Delete a playlist (full hard-delete)

### B1. What must be removed

| Target | Mechanism |
|---|---|
| `videos` rows (+ artifact JSONB in `videos.data`) | DB cascade from `playlists` |
| `jobs` rows | DB cascade from `playlists` |
| **`share_tokens` rows** | **New composite cascade FK (B2)** — currently orphans |
| Storage blobs `<owner>/<playlist_key>/**` (summary md/pdf/html + `dig/**`) | New recursive `deletePrefix` (B3) |
| In-flight jobs (queued/active) | Best-effort cancel-first (B4) |
| `playlists` row | Session-client `DELETE` (RLS owner-guarded) |

Not playlist-scoped, untouched: `serve_model_charge`, `serve_owner_budget`, `spend_ledger`,
`usage_counters` (day/owner-keyed, expire on their own).

### B2. DB — migration `00NN_share_tokens_cascade.sql`

Add the same composite cascade FK the codebase already uses for `videos`/`jobs`, so a single
`DELETE playlists` cascades **all** DB state atomically (one transaction, no RPC):

```sql
-- remove any pre-existing orphans so the constraint can be added
delete from share_tokens st
  where not exists (select 1 from playlists p
                    where p.id = st.playlist_id and p.owner_id = st.owner_id);
alter table share_tokens
  add constraint share_tokens_playlist_owner_fk
  foreign key (playlist_id, owner_id) references playlists(id, owner_id) on delete cascade;
```

- Composite `(playlist_id, owner_id)` (not bare `playlist_id`) matches `videos`/`jobs` and keeps
  the cross-tenant guarantee (a share token's owner always equals its playlist's owner).
- **Decision D2 (default: cascade-FK, chosen).** Alternative considered — a `delete_playlist`
  SECURITY DEFINER RPC — rejected: the cascade FK is idiomatic here (mirrors videos/jobs), needs
  no new RPC surface, and `authenticated` already holds `delete on playlists`.

### B3. Blobs — recursive prefix delete

Add to the `BlobStore` interface:

```ts
/** Delete every object under a logical prefix (recursively). Best-effort, idempotent:
 *  absent objects are not an error. `prefix === ''` targets the whole playlist root. */
deletePrefix(p: Principal, prefix: string): Promise<void>;
```

- **Supabase impl:** recursively `.list('<owner>/<playlist_key>/<prefix>')` (paginating past the
  100-object default; recurse into folder entries, i.e. entries with `id === null`), collect full
  object paths, `.remove(batch)` in chunks (≤ ~1000). Tolerate empty listings.
- **Local impl:** `fs.rm(join(indexKey, prefix), { recursive: true, force: true })` (ENOENT-safe).
- `assertLogicalKey('')` passes (no leading `/`, no `..`, no `\0`), so `prefix === ''` is legal.

### B4. In-flight jobs — cancel-first

Before deleting, reuse the existing playlist-wide cancel to quiesce the worker: over
`queue.listByPlaylist(id)`, `requestCancel` each non-terminal job. This stops **queued** jobs from
being claimed (and starting new paid Gemini work) during the delete window. An **active** job
whose row is then cascade-deleted keeps running to completion but its lease-fenced
`complete_job`/`fail_job` (WHERE `status='active'`) no-op against the missing row — no crash.

### B5. Delete sequence + failure semantics

`DELETE /api/playlists/[id]` (cloud branch), session-scoped client:

1. `getUser()` → 401 if unauthenticated.
2. Read the playlist (RLS-scoped) to obtain its `playlist_key` **and confirm ownership** →
   **404** if not found / not owned (RLS makes another owner's row invisible).
3. **Cancel-first (best-effort):** cancel non-terminal jobs (B4). Failures logged, not fatal.
4. **DB delete:** `supabase.from('playlists').delete().eq('id', id)` — RLS owner-guarded; cascades
   videos (+artifact JSONB), jobs, share_tokens (via B2). This is the **commit point**: once it
   succeeds the playlist is gone from the user's world.
5. **Blob cleanup (best-effort, after commit):** `blobStore.deletePrefix(principal, '')` for the
   captured `playlist_key`. If this fails, **log and still return 200** — orphaned blobs are
   invisible (no DB row references them), a bounded storage-cost residue, not user-facing breakage.
6. Return `{ deleted: true }`.

**Ordering rationale:** DB row deleted *before* blobs so the only partial-failure residue is
invisible orphaned blobs (safe), never a listed playlist whose summaries 404 (visible breakage).
`playlist_key` is captured in step 2 because after step 4 the row is gone.

**Accepted residual (documented):** an active worker that writes a blob in the window between
steps 4–5 can leave one orphan the cleanup misses. Invisible; a future storage sweeper can reap
it. Synchronous worker quiescence is over-engineering for a delete.

**Idempotency:** a second DELETE of the same id returns 404 (row already gone) — the client
treats 404 on delete as success (already deleted).

### B6. API surface

- New `MetadataStore.deletePlaylist(p, playlistId): Promise<void>` (session-client delete;
  local impl: recursive fs remove of the playlist dir, or no-op if out of scope for local).
- New `lib/client/api.ts` → `deletePlaylist(id): Promise<void>` and
  `backfillPlaylistTitles(): Promise<{updated:number}>`. `deletePlaylist` treats HTTP 404 as
  success (already gone); throws `UnauthorizedError` on 401.

### B7. UI — sidebar delete control + confirm modal

- **Control:** each sidebar `<li>` (`PlaylistSidebar.tsx:83-97`) gets a delete affordance (trash
  icon button, `aria-label="Delete playlist <name>"`), visible on row hover/focus, that opens the
  confirm modal. Clicking it must **not** navigate (stop propagation from the row `<Link>`).
- **Confirm modal** (model on `NewPlaylistModal`: focus trap, Esc, returnFocus, submit guard):
  - Copy: **"Delete "<title>"? This permanently removes the playlist, all its summaries, PDFs,
    and any share links. This cannot be undone."**
  - Buttons: **Cancel** (default focus) and **Delete** (destructive).
  - **Decision D3 (default: simple confirm, chosen):** a single Delete button, not type-to-confirm.
    Proportional to a per-playlist action; the explicit modal + destructive styling is the guard.
  - **Async op (non-blocking-elsewhere; modal-local pending):** on Delete → button shows
    "Deleting…", both buttons + dismissal disabled. On success → modal closes, playlist removed
    from the list (optimistic refetch), and if the deleted playlist was the active one, navigate
    to `/` (no `?playlist=` param). On error → modal stays open, shows an inline error, re-enables.

#### Overlay Dismissal table (delete confirm modal)

| Mechanism | Enabled when | Expected result |
|---|---|---|
| Cancel button | not deleting | Close modal, no delete, focus returns to trigger |
| Escape key | not deleting | Same as Cancel |
| Backdrop click | not deleting | Same as Cancel |
| Close (✕) button | not deleting | Same as Cancel |
| (all of the above) | **deleting in progress** | **No-op** (disabled) — prevents dismiss mid-delete |
| Delete button → success | — | Modal auto-closes, list refreshes, nav to `/` if active deleted |
| Delete button → error | — | Modal stays open, inline error, buttons re-enabled |

#### URL Contracts table

| Component | Link/Action | Full URL / method |
|---|---|---|
| Sidebar delete button | DELETE playlist | `DELETE /api/playlists/<playlistUUID>` |
| Sidebar (on mount, null titles present) | backfill | `POST /api/playlists/backfill-titles` |
| Active-playlist deletion | navigate home | `/` (no `?playlist=` param) |
| Existing row link (unchanged) | open playlist | `/?playlist=<playlistUUID>` |

## 6. Enumerated design decisions (flagged for user review)

All have sensible defaults chosen so the AFK run can proceed; the user may override any on return.
None move the goal (real names + full hard-delete).

| # | Decision | Default (chosen) | Alternatives |
|---|---|---|---|
| D1 | Backfill trigger | Auto on sidebar mount when ≥1 null title, once/mount | Manual "fix names" button; on-ingest only |
| D2 | Delete DB mechanism | Composite cascade FK on `share_tokens` + session-client delete | `delete_playlist` SECURITY DEFINER RPC |
| D3 | Delete confirmation | Simple confirm modal (Cancel/Delete) | Type-to-confirm playlist name |
| D4 | In-flight jobs | Cancel-first best-effort, then cascade-delete | Skip cancel (rely on cascade + lease no-op) |
| D5 | Blob cleanup failure | Log + return 200 (orphans accepted) | Fail the delete / retry inline |

## 7. Testing strategy

Per `docs/dev-process.md` TDD policy + mocking boundaries (mock `lib/youtube.ts`, `lib/gemini.ts`;
E2E mocks at route level).

- **A1 forward fix (unit):** producer persists title after resolve; title-fetch throw does NOT
  fail ingest (videos still enqueue); `setPlaylistMeta` called with fetched title.
- **A2 backfill (unit + integration):** route selects only null-title rows; per-row failure
  isolated; returns counts; idempotent (second call updates 0). Integration against real local
  Supabase: null-title row → titled after call.
- **B2 migration (integration):** adding a share_token then deleting its playlist removes the
  share_token (cascade); pre-existing orphan cleanup runs; cross-owner FK holds.
- **B3 deletePrefix (unit + integration):** removes flat + nested (`dig/**`) objects; paginates
  past 100; empty prefix = whole playlist; absent = no error. Local impl: recursive fs remove,
  ENOENT-safe.
- **B4/B5 route (integration):** full round-trip — seed playlist+videos+jobs+share_token+blobs →
  DELETE → all gone (DB via SQL, blobs via list); non-owner gets 404 and nothing deleted
  (isolation); blob-cleanup failure still returns 200 (mock storage error); second delete → 404.
- **B7 UI (component + E2E):** trash button opens modal without navigating; each dismissal path
  (Cancel/Esc/backdrop/✕) closes without deleting; dismissal disabled while deleting; success
  refreshes list + navigates home when active deleted; error keeps modal open. E2E fixtures
  include a null-title playlist and a titled one (conditional-render coverage per dev-process).

## 8. Adversarial-review triggers (this spec REQUIRES iterative re-review to convergence)

Per `docs/dev-process.md` → Adversarial Review → Iterative Re-Review, this slice hits multiple
mandatory triggers: **schema change** (new FK), **multi-tenant isolation** (owner-scoped delete),
**an irreversible path** (hard-delete), and **a non-transactional multi-effect sequence** (cancel
→ DB cascade → blob cleanup with defined partial-failure semantics). Dual review (Claude + Codex)
iterates until a full round returns no new Blocking/High.

## 9. Open questions for the user (non-blocking)

Defaults above will be implemented; flag on return if any should change:
1. D1 — is auto-backfill-on-mount acceptable, or prefer an explicit button?
2. D3 — is a simple confirm modal enough for an irreversible delete, or want type-to-confirm?
3. D5 — accept invisible orphaned blobs on cleanup failure, or must delete be all-or-nothing?
