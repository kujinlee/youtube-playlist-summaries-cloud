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

### A0. Real-title helper (`fetchPlaylistTitleOrNull`) — resolves the fake-title defect

**Review H1 (Codex M3 + Claude H1):** `fetchPlaylistTitle` returns the raw **list-id** as a
fallback when YouTube responds 200-with-no-items (private/deleted/title-less playlist). Persisting
that makes the row **non-null** with a cryptic `PLxxxx` "title" — the backfill (null-only) never
retries it and the `'Untitled playlist'` fallback never fires.

Add to `lib/youtube.ts`:

```ts
/** Real title, or null when YouTube returns no playlist item (private/deleted/absent). */
export async function fetchPlaylistTitleOrNull(playlistId: string, apiKey: string): Promise<string | null> {
  const yt = google.youtube({ version: 'v3', auth: apiKey });
  const res = await yt.playlists.list({ part: ['snippet'], id: [playlistId] });
  return res.data.items?.[0]?.snippet?.title ?? null;   // no list-id fallback
}
// existing fetchPlaylistTitle stays for local callers: `return (await fetchPlaylistTitleOrNull(id, key)) ?? id;`
```

Both A1 and A2 use `fetchPlaylistTitleOrNull` and **persist only a non-null real title**; a miss
leaves the row null (→ `'Untitled playlist'`, retriable). Network/quota errors *throw* (distinct
from a clean "no item") and are caught → left null for a bounded retry (A2).

### A1. Forward fix (persist title at ingest)

In `enqueuePlaylist` (`producer.ts`), after `resolvePlaylistId` succeeds, fetch and persist the
title. `extractPlaylistId(playlistUrl)` (already imported and called for validation) yields the
list-id; `apiKey` is already in scope.

```ts
const playlistId = await sessionBundle.metadataStore.resolvePlaylistId(principal, playlistUrl);
// BUG-6: persist the human-readable title (best-effort; never fail ingest on a title miss)
try {
  const listId = extractPlaylistId(playlistUrl);
  const playlistTitle = await fetchPlaylistTitleOrNull(listId, apiKey);
  if (playlistTitle) await sessionBundle.metadataStore.setPlaylistMeta(principal, { playlistUrl, playlistTitle });
} catch { /* leave title null; backfill will retry */ }
```

- **Best-effort:** a title fetch failure must **not** fail ingestion (videos still enqueue). The
  row keeps `playlist_title = NULL` and the backfill path (A2) retries later.
- Only persists a real title — a "no item" miss leaves the row null (no fake `PLxxxx` name).
- `setPlaylistMeta` upserts on `(owner_id, playlist_key)`, so it updates the row `resolvePlaylistId`
  just created (same key) without clobbering `playlist_url`.
- Idempotent: re-ingesting the same playlist re-sets the same title.

### A2. Backfill existing null-title rows

New owner-scoped route **`POST /api/playlists/backfill-titles`** (cloud branch):

1. Read `YOUTUBE_API_KEY` once (500 if unset).
2. List the caller's playlists (RLS-scoped session client); select those with `playlist_title`
   null, **capped at `BACKFILL_MAX_PER_CALL` (25)** rows/call (bounds YouTube quota per request).
3. For each, `fetchPlaylistTitleOrNull(playlist_key, apiKey)`. On a **non-null** real title,
   persist with a **conditional update** (see below). A null (no item) or a thrown
   network/quota error skips that row — per-playlist try/catch, never 500s the batch.
4. Return `{ updated: number, attempted: number }`.

**Conditional persist (review M-race, Codex M2 + Claude M1):** do **not** use the `setPlaylistMeta`
upsert here — it unconditionally overwrites `playlist_title` (clobbering a title a concurrent
ingest just wrote) and re-supplies `playlist_url` (which the backfill would have to re-read to
satisfy the NOT NULL column). Instead add `MetadataStore.setPlaylistTitleIfNull(p, listId, title)`
→ `update playlists set playlist_title = $title where owner_id = auth.uid() and playlist_key = $listId
and playlist_title is null`. Owner-scoped, only fills nulls, touches no other column.

**Trigger (decision D1 — default: auto, bounded):** `PlaylistSidebar`, after loading playlists,
if **≥1** has a null `playlistTitle`, fires `backfillPlaylistTitles()` **once**, then re-fetches
the list so names appear. Bounding (review H2, Codex H2 + Claude H2 — prevents an unbounded
backfill→refetch loop when a row stays null because its playlist is private/deleted or YouTube is
rate-limiting):

- The one-shot is a **`useRef` guard**, NOT derived from `playlists` state — so the post-backfill
  refetch (which may still contain null rows) cannot re-fire it. React 18 StrictMode double-invoke
  is absorbed by the ref.
- Additionally gated by a **`sessionStorage` flag** (`backfilledTitles`) so it runs **at most once
  per browser session** across mounts/navigations, not once per mount.
- Server-side row cap (step 2) is the backstop even if a client ignores both guards.

- Idempotent (only fills null rows); safe to call repeatedly.
- Fully null-safe: read path unchanged; the `?? 'Untitled playlist'` fallback still covers a row
  whose title genuinely can't be fetched (private/deleted playlist).

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

**Intentionally retained (review M1, Codex M1 + Claude Low):** `serve_model_charge` *is*
playlist-scoped (its `doc_key = '<playlist_id>/<video_id>'`, `0012:53`) and does **not** expire —
but it is an **immutable spend/billing-audit ledger**: the money was actually spent, so a delete
must not erase it. A re-ingested playlist gets a fresh UUID, so old `doc_key`s never collide and
the retained rows are inert. `serve_owner_budget`, `spend_ledger`, `usage_counters` are
owner/day-keyed accounting and likewise retained by design. This retention is a deliberate
decision, not an oversight; it is **not** a leak (owner-scoped, never re-matched).

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
-- cascade deletes scan children by playlist_id; index it (review Low, Claude)
create index if not exists share_tokens_playlist_id_idx on share_tokens (playlist_id);
```

- Composite `(playlist_id, owner_id)` (not bare `playlist_id`) matches `videos`/`jobs` and keeps
  the cross-tenant guarantee (a share token's owner always equals its playlist's owner).
- **RI actions bypass RLS** (review M3, Claude): the `ON DELETE CASCADE` fires even though
  `share_tokens` is force-RLS with no authenticated policy — same mechanism already relied on for
  `videos`/`jobs`. Correct but load-bearing and non-obvious → the B2 cascade integration test (§7)
  is **mandatory**, not optional.
- **Decision D2 (default: cascade-FK, chosen).** Alternative considered — a `delete_playlist`
  SECURITY DEFINER RPC — rejected: the cascade FK is idiomatic here (mirrors videos/jobs), needs
  no new RPC surface, and `authenticated` already holds `delete on playlists`. (Note: a separate
  cancel RPC is still added in B4 — that is orthogonal to the delete cascade.)

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
- **Local impl:** `assertLogicalKey(prefix)` **first** (review M2, Claude — the interface takes an
  arbitrary caller string; `''` is safe but `'..'` must be rejected before it reaches `fs.rm`),
  then `fs.rm(join(indexKey, prefix), { recursive: true, force: true })` (ENOENT-safe).
- **Supabase impl** likewise calls `assertLogicalKey(prefix)` before building the storage prefix.
- `assertLogicalKey('')` passes (no leading `/`, no `..`, no `\0`), so `prefix === ''` is legal.

### B4. In-flight jobs — cancel-first (all kinds)

**Review H1 (Codex H1):** the existing playlist cancel (`app/api/jobs/cancel/route.ts` →
`SupabaseJobQueue.listByPlaylist`) filters `job_kind = 'summary'`, so it would **miss `dig`
jobs** — a queued dig could still be claimed and spend, an active dig keeps spending. The delete
must cancel **all kinds**.

Add a SECURITY DEFINER RPC to the same migration (B2):

```sql
create or replace function request_cancel_playlist_jobs(p_playlist_id uuid)
returns int language plpgsql security definer set search_path = public as $$
declare n int;
begin
  update jobs
     set cancel_requested = true,
         status = case when status = 'queued' then 'cancelled' else status end,
         updated_at = now()
   where playlist_id = p_playlist_id and owner_id = auth.uid()
     and status in ('queued','active');           -- ALL kinds (no job_kind filter)
  get diagnostics n = row_count; return n;
end $$;
revoke all on function request_cancel_playlist_jobs(uuid) from public;
grant execute on function request_cancel_playlist_jobs(uuid) to authenticated, service_role;
```

Mirrors the per-job `request_cancel_job` (`0010`) but scoped to a whole playlist, owner-guarded via
`auth.uid()`. The DELETE route calls it once (best-effort). This stops **queued** jobs (any kind)
from being claimed during the delete window. An **active** job whose row is then cascade-deleted
keeps running to completion but its lease-fenced `complete_job`/`fail_job` (WHERE `status='active'`)
no-op against the missing row — no crash.

### B5. Delete sequence + failure semantics

`DELETE /api/playlists/[id]` (cloud branch), session-scoped client:

1. `getUser()` → 401 if unauthenticated.
2. Read the playlist (RLS-scoped) to obtain its `playlist_key` **and confirm ownership** →
   **404** if not found / not owned (RLS makes another owner's row invisible).
3. **Cancel-first (best-effort):** `rpc('request_cancel_playlist_jobs', { p_playlist_id: id })`
   (B4, all kinds incl. dig). Failures logged, not fatal.
4. **DB delete:** `supabase.from('playlists').delete().eq('id', id).eq('owner_id', user.id)` — RLS
   already owner-guards, but the explicit `owner_id` predicate is defense-in-depth (review Low,
   Claude). Cascades videos (+artifact JSONB), jobs, share_tokens (via B2). This is the **commit
   point**: once it succeeds the playlist is gone from the user's world.
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
  confirm modal. The trash `<button>` is a **sibling** of the row `<Link>`, **not nested inside it**
  (review Low, Codex — a button inside an `<a>` is invalid interactive nesting and can still
  navigate); the `<li>` holds `[<Link>, <button>]`. The button also `stopPropagation`/
  `preventDefault` for good measure.
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
| D1 | Backfill trigger | Auto, once/session (`useRef` + `sessionStorage`), capped 25 rows/call | Manual "fix names" button; on-ingest only |
| D2 | Delete DB mechanism | Composite cascade FK on `share_tokens` + session-client delete | `delete_playlist` SECURITY DEFINER RPC |
| D3 | Delete confirmation | Simple confirm modal (Cancel/Delete) | Type-to-confirm playlist name |
| D4 | In-flight jobs | Cancel-first via all-kinds `request_cancel_playlist_jobs` RPC, then cascade-delete | Skip cancel (rely on cascade + lease no-op) |
| D5 | Blob cleanup failure | Log + return 200 (orphans accepted) | Fail the delete / retry inline |

## 7. Testing strategy

Per `docs/dev-process.md` TDD policy + mocking boundaries (mock `lib/youtube.ts`, `lib/gemini.ts`;
E2E mocks at route level).

- **A0 `fetchPlaylistTitleOrNull` (unit):** returns the snippet title when present; returns
  **null** (not the list-id) when `items` is empty; `fetchPlaylistTitle` still returns the list-id
  fallback (local callers unchanged).
- **A1 forward fix (unit):** producer persists a real title after resolve; a **null** (no-item)
  result persists **nothing** (row stays null — no fake `PLxxxx`); a title-fetch throw does NOT
  fail ingest (videos still enqueue).
- **A2 backfill (unit + integration):** route caps at 25 rows/call; selects only null-title rows;
  persists via `setPlaylistTitleIfNull` (conditional `WHERE playlist_title IS NULL` — a concurrent
  real title is NOT clobbered); a null/thrown fetch skips that row; returns counts; idempotent
  (second call updates 0). Integration against real local Supabase: null-title row → titled after
  call; a row whose fetch returns null stays null.
- **A2 trigger (component):** the `useRef` one-shot fires backfill at most once even when the
  post-backfill refetch still contains null rows (no loop); the `sessionStorage` flag suppresses a
  second run on remount; StrictMode double-invoke fires it once.
- **B2 migration (integration):** adding a share_token then deleting its playlist removes the
  share_token (cascade); pre-existing orphan cleanup runs; cross-owner FK holds.
- **B3 deletePrefix (unit + integration):** removes flat + nested (`dig/**`) objects; paginates
  past 100; empty prefix = whole playlist; absent = no error. Local impl: recursive fs remove,
  ENOENT-safe.
- **B2 cascade (integration — MANDATORY):** insert a share_token for a playlist → delete the
  playlist → the share_token row is gone (proves the RLS-bypassing RI cascade); pre-existing
  orphan cleanup runs; a cross-owner share_token is untouched.
- **B4 cancel RPC (integration):** a queued **dig** job and a queued summary job for a playlist are
  BOTH `cancelled` by `request_cancel_playlist_jobs` (all-kinds); another owner's job is untouched
  (owner-guard); returns the row count.
- **B4/B5 route (integration):** full round-trip — seed playlist+videos+jobs(summary+dig)+
  share_token+blobs → DELETE → all gone (DB via SQL, blobs via list); non-owner gets 404 and
  nothing deleted (isolation); blob-cleanup failure still returns 200 (mock storage error); second
  delete → 404.
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
