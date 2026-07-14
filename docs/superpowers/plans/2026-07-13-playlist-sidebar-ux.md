# Playlist Sidebar UX Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cloud playlists show real YouTube titles (BUG-6, forward + backfill) and can be fully hard-deleted (DB cascade + blobs + share tokens + job cancel) from the sidebar.

**Architecture:** Two features on the cloud path (`STORAGE_BACKEND=supabase`). Naming = a null-safe title fetch persisted at ingest + a bounded backfill route auto-fired once/session by the sidebar. Delete = a migration completing the FK/cancel surface, a recursive blob prefix-delete, an owner-scoped `DELETE` route orchestrating cancel→cascade-delete→blob-cleanup, and a sidebar trash button + confirm modal.

**Tech Stack:** Next.js 16 App Router, Supabase (Postgres RLS + Storage), TypeScript, jest + ts-jest (unit), @testing-library/react (component), Playwright (E2E), real local Supabase (integration).

**Spec:** `docs/superpowers/specs/2026-07-13-playlist-sidebar-ux-design.md` (converged, 0 Blocking/0 High dual review). Section refs (§A0…§B7) below point into it.

## Global Constraints

- **Cloud-only.** All new behavior is under the `STORAGE_BACKEND==='supabase'` branch; local backend keeps current behavior (local `MetadataStore` methods that are cloud-only `throw`; local `deletePrefix` is real but the delete *route/UI* is cloud-only).
- **Owner isolation is non-negotiable.** Every DB/blob mutation is confined to `auth.uid()` via the RLS-scoped session client (`createServerSupabase(cookieStore)`), never the service-role client, except where a `SECURITY DEFINER` RPC self-guards with `auth.uid()`. Never widen a query to another owner.
- **TDD, Iron Law.** No production code without a failing test watched first. Mock `lib/youtube.ts` and `lib/gemini.ts` at the lib boundary in unit tests; E2E mocks at the route level. Integration tests hit real local Supabase.
- **Persist only real titles.** Never persist the list-id as a `playlist_title` (that is the BUG-6 defect). A missing YouTube item ⇒ leave the row null.
- **Delete failure ordering:** DB row deleted before blobs; blob-cleanup failure still returns 200 (invisible orphans accepted, §B5/D5). `playlist_key` captured before the DB delete.
- **Migration is `0019_share_tokens_cascade.sql`** (next after `0018_enqueue_dig`).
- **Commit trailers** end with `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>` and `Claude-Session: https://claude.ai/code/session_01VvbM4MyLuP1hdhhfr4JPtf`.
- Run the narrowest test first (`npx jest <name>`), full `npm test` once before each commit.

## File Structure

| File | Responsibility | Task |
|---|---|---|
| `lib/youtube.ts` | add `fetchPlaylistTitleOrNull`; `fetchPlaylistTitle` delegates | T1 |
| `lib/job-queue/producer.ts` | persist real title after `resolvePlaylistId` | T2 |
| `lib/storage/metadata-store.ts` | add `setPlaylistTitleIfNull` + `deletePlaylist` to interface | T3, T8 |
| `lib/storage/supabase/supabase-metadata-store.ts` | cloud impls of the two new methods | T3, T8 |
| `lib/storage/local/local-metadata-store.ts` | local impls (title=update JSON; delete=throw cloud-only) | T3, T8 |
| `app/api/playlists/backfill-titles/route.ts` | POST backfill route (new) | T4 |
| `lib/client/api.ts` | `backfillPlaylistTitles`, `deletePlaylist` client fns | T5, T9 |
| `components/cloud/PlaylistSidebar.tsx` | auto-backfill trigger; trash button + modal wiring | T5, T10 |
| `supabase/migrations/0019_share_tokens_cascade.sql` | cascade FK + index + `request_cancel_playlist_jobs` RPC (new) | T6 |
| `lib/storage/blob-store.ts` | add `deletePrefix` to interface (+ `assertLogicalKey` reuse) | T7 |
| `lib/storage/supabase/supabase-blob-store.ts` | recursive list+remove impl | T7 |
| `lib/storage/local/local-blob-store.ts` | recursive fs remove impl | T7 |
| `lib/storage/supabase/supabase-job-queue.ts` | `requestCancelPlaylist(playlistId)` wrapper on the RPC | T8 |
| `app/api/playlists/[id]/route.ts` | DELETE route orchestration (new) | T9 |
| `components/cloud/DeletePlaylistDialog.tsx` | confirm modal (new) | T10 |

---

### Task 1: `fetchPlaylistTitleOrNull` (real-title helper)

**Files:**
- Modify: `lib/youtube.ts` (add export; `fetchPlaylistTitle` delegates)
- Test: `tests/lib/youtube-playlist-title.test.ts` (new)

**Interfaces:**
- Produces: `fetchPlaylistTitleOrNull(playlistId: string, apiKey: string): Promise<string | null>` — real snippet title, or `null` when YouTube returns no item. `fetchPlaylistTitle(playlistId, apiKey): Promise<string>` unchanged contract (delegates, `?? playlistId`).

**Enumerated Behaviors**

| # | Behavior | Trigger | Expected |
|---|---|---|---|
| 1 | Returns real title | items[0].snippet.title present | that title |
| 2 | Returns null on no item | `items` empty/absent | `null` (NOT the list-id) |
| 3 | `fetchPlaylistTitle` still falls back | no item | returns `playlistId` (local callers unchanged) |
| 4 | Propagates API error | `playlists.list` throws | throws (caller catches) |

- [ ] **Step 1:** Write failing tests for behaviors 1–4. Mock `google.youtube` so `playlists.list` returns `{ data: { items: [...] } }` / `{ data: { items: [] } }` / rejects.
- [ ] **Step 2:** Run `npx jest youtube-playlist-title` → FAIL (`fetchPlaylistTitleOrNull` not exported).
- [ ] **Step 3:** Implement: extract the list call into `fetchPlaylistTitleOrNull` returning `res.data.items?.[0]?.snippet?.title ?? null`; rewrite `fetchPlaylistTitle` as `return (await fetchPlaylistTitleOrNull(playlistId, apiKey)) ?? playlistId;`.
- [ ] **Step 4:** Run tests → PASS. Then `npx jest youtube` to confirm existing youtube tests still green.
- [ ] **Step 5:** Full `npm test`; commit `feat(playlist-ux): add fetchPlaylistTitleOrNull (real title or null)`.

---

### Task 2: Forward-fix — persist title at cloud ingest

**Files:**
- Modify: `lib/job-queue/producer.ts` (after `resolvePlaylistId`, ~line 90)
- Test: `tests/lib/job-queue/producer-title.test.ts` (new) — mock `metadataStore` + `lib/youtube`

**Interfaces:**
- Consumes: `fetchPlaylistTitleOrNull` (T1), `extractPlaylistId` (already imported), `metadataStore.setPlaylistMeta`.

**Enumerated Behaviors**

| # | Behavior | Trigger | Expected |
|---|---|---|---|
| 1 | Persists real title | fetch returns "My List" | `setPlaylistMeta(principal,{playlistUrl, playlistTitle:'My List'})` called |
| 2 | No fake title on miss | fetch returns null | `setPlaylistMeta` NOT called (row stays null) |
| 3 | Title throw ≠ ingest fail | `fetchPlaylistTitleOrNull` throws | enqueue still proceeds; ProducerResult returned; no rethrow |
| 4 | Runs only after resolve | — | called with the resolved `playlistId`'s principal/url after `resolvePlaylistId` |

- [ ] **Step 1:** Write failing tests. Arrange `enqueuePlaylist` with mocked `sessionBundle.metadataStore` (`resolvePlaylistId` returns an id, `setPlaylistMeta` a spy), mocked enqueuer, and `lib/youtube` (`fetchPlaylistTitleOrNull` variants), `YOUTUBE_API_KEY` set. Assert the spy per behaviors 1–3.
- [ ] **Step 2:** Run `npx jest producer-title` → FAIL.
- [ ] **Step 3:** Implement the §A1 block: `try { const listId = extractPlaylistId(playlistUrl); const t = await fetchPlaylistTitleOrNull(listId, apiKey); if (t) await sessionBundle.metadataStore.setPlaylistMeta(principal, { playlistUrl, playlistTitle: t }); } catch { /* leave null */ }` placed immediately after the `resolvePlaylistId` call.
- [ ] **Step 4:** Run tests → PASS; then `npx jest producer` (no regression in existing producer tests).
- [ ] **Step 5:** Full `npm test`; commit `feat(playlist-ux): persist real playlist title at cloud ingest (BUG-6 fwd)`.

---

### Task 3: `setPlaylistTitleIfNull` (conditional title update)

**Files:**
- Modify: `lib/storage/metadata-store.ts` (interface), `lib/storage/supabase/supabase-metadata-store.ts`, `lib/storage/local/local-metadata-store.ts`
- Test: `tests/lib/storage/supabase-metadata-store.test.ts` (add), `tests/integration/backfill-titles.test.ts` (new, integration piece)

**Interfaces:**
- Produces: `MetadataStore.setPlaylistTitleIfNull(p: Principal, listId: string, title: string): Promise<void>` — `update playlists set playlist_title=$title where owner_id=auth.uid() and playlist_key=$listId and playlist_title is null`.

**Enumerated Behaviors**

| # | Behavior | Trigger | Expected |
|---|---|---|---|
| 1 | Fills a null title | row has null title | `playlist_title` set; owner+key+`is null` predicate in the query |
| 2 | Does not clobber | row already titled | `is null` predicate ⇒ 0 rows updated, existing title unchanged (integration) |
| 3 | Owner-scoped | — | update filtered by `owner_id`/RLS; never another owner's row |
| 4 | Local impl parity | local backend | updates the JSON index title only when currently absent (or minimal parity) |

- [ ] **Step 1:** Unit test (cloud): mock client `.from().update().eq().eq().is()` chain; assert the update payload `{playlist_title:title}` and the three predicates (`owner_id`, `playlist_key`, `playlist_title is null`). Add the interface method (TS compile fails until impls exist).
- [ ] **Step 2:** Run `npx jest supabase-metadata-store` → FAIL.
- [ ] **Step 3:** Implement cloud method (auth.getUser → ownerId guard, then the scoped conditional update); implement local method (read index, set title only if absent); keep interface + both impls in sync.
- [ ] **Step 4:** Run unit → PASS. Write the **integration** behavior-2 test (real local Supabase): seed a titled row, call `setPlaylistTitleIfNull` → title unchanged; seed a null row → title set. Run `npx jest backfill-titles` (integration) → PASS.
- [ ] **Step 5:** Full `npm test`; commit `feat(playlist-ux): setPlaylistTitleIfNull conditional update (no clobber)`.

---

### Task 4: Backfill route `POST /api/playlists/backfill-titles`

**Files:**
- Create: `app/api/playlists/backfill-titles/route.ts`
- Test: `tests/integration/backfill-titles-route.test.ts` (new) + a unit for cap/isolation logic

**Interfaces:**
- Consumes: `createServerSupabase`, `getStorageBundle`, `listPlaylists`, `setPlaylistTitleIfNull` (T3), `fetchPlaylistTitleOrNull` (T1), `process.env.YOUTUBE_API_KEY`.
- Produces: `POST` → `{ updated: number, attempted: number }`.

**Enumerated Behaviors**

| # | Behavior | Trigger | Expected |
|---|---|---|---|
| 1 | 401 unauthenticated | no session user | 401 |
| 2 | 500 no API key | `YOUTUBE_API_KEY` unset | 500 (read once) |
| 3 | Backfills null rows | owner has null-title rows | each real title persisted via `setPlaylistTitleIfNull`; `{updated,attempted}` counts |
| 4 | Skips null fetch | `fetchPlaylistTitleOrNull` → null | row skipped, counted in attempted not updated, stays null |
| 5 | Per-row error isolation | one fetch throws | other rows still processed; route returns 200 |
| 6 | Row ceiling | > 200 null rows | at most 200 processed (runaway backstop) |
| 7 | Owner isolation | another owner's null rows | never touched (RLS session client) |
| 8 | Local branch | `STORAGE_BACKEND!=='supabase'` | 404/unsupported (cloud-only) |

- [ ] **Step 1:** Write failing tests: unit for behaviors 1,2,4,5,6 (mock the store `listPlaylists`/`setPlaylistTitleIfNull` and `lib/youtube`); integration for 3,7 (real Supabase, two owners). 
- [ ] **Step 2:** Run `npx jest backfill-titles-route` → FAIL (route missing).
- [ ] **Step 3:** Implement route (cloud branch): getUser→401; apiKey→500; `listPlaylists(user.id)`; filter null-title; slice(0,200); for-each `try { const t = await fetchPlaylistTitleOrNull(p.playlistKey, apiKey); if (t) { await store.setPlaylistTitleIfNull(principal, p.playlistKey, t); updated++; } } catch {} ; attempted++`. Return counts.
- [ ] **Step 4:** Run tests → PASS.
- [ ] **Step 5:** Full `npm test`; commit `feat(playlist-ux): POST /api/playlists/backfill-titles (bounded, isolated)`.

---

### Task 5: Sidebar auto-backfill trigger + client fn

**Files:**
- Modify: `lib/client/api.ts` (add `backfillPlaylistTitles`), `components/cloud/PlaylistSidebar.tsx`
- Test: `tests/components/cloud/PlaylistSidebar.backfill.test.tsx` (new)

**Interfaces:**
- Consumes: backfill route (T4).
- Produces: `backfillPlaylistTitles(): Promise<{updated:number; attempted:number}>`.

**Enumerated Behaviors**

| # | Behavior | Trigger | Expected |
|---|---|---|---|
| 1 | Fires when null titles present | loaded list has ≥1 null title | one POST to backfill, then a re-fetch of the list |
| 2 | Does NOT loop | post-backfill refetch still has null rows | backfill NOT fired again (`useRef` one-shot, not state-derived) |
| 3 | Skips when all titled | no null titles | no backfill call |
| 4 | Once per session | remount with flag set | `sessionStorage['backfilledTitles:'+userId]` present ⇒ no call |
| 5 | StrictMode safe | double-invoke effect | fires once |

- [ ] **Step 1:** Write failing component tests. Mock `lib/client/api` (`listPlaylists`, `backfillPlaylistTitles`). Render sidebar with a null-title fixture; assert one backfill call + refetch (behavior 1); re-render with still-null refetch (behavior 2); titled fixture (3); pre-set sessionStorage (4).
- [ ] **Step 2:** Run `npx jest PlaylistSidebar.backfill` → FAIL.
- [ ] **Step 3:** Add `backfillPlaylistTitles` to `lib/client/api.ts`. In the sidebar, add a `useRef(false)` one-shot guard + per-user `sessionStorage` key (`backfilledTitles:${userId}`); in the load effect, after fetching, if `!ref.current && !sessionStorage.get(key) && list.some(p=>!p.playlistTitle)` → set both guards, `await backfillPlaylistTitles()`, re-fetch list.
- [ ] **Step 4:** Run tests → PASS.
- [ ] **Step 5:** Full `npm test`; commit `feat(playlist-ux): sidebar auto-backfill titles once/session (BUG-6)`.

---

### Task 6: Migration `0019_share_tokens_cascade.sql`

**Files:**
- Create: `supabase/migrations/0019_share_tokens_cascade.sql`
- Test: `tests/integration/share-tokens-cascade.test.ts`, `tests/integration/cancel-playlist-jobs.test.ts` (new)

**Interfaces:**
- Produces (DB): FK `share_tokens_playlist_owner_fk` (composite, ON DELETE CASCADE) + `share_tokens_playlist_id_idx`; RPC `request_cancel_playlist_jobs(p_playlist_id uuid) returns int` (SECURITY DEFINER, owner-guarded, all kinds).

**Enumerated Behaviors**

| # | Behavior | Trigger | Expected |
|---|---|---|---|
| 1 | Orphan cleanup | pre-existing share_token with no matching playlist | deleted by the pre-ALTER cleanup so the FK can be added |
| 2 | Cascade on delete | delete a playlist that has a share_token | share_token row gone |
| 3 | Cross-owner integrity | — | FK is `(playlist_id, owner_id)`; a token's owner must equal its playlist's owner |
| 4 | Cancel all kinds | queued summary + queued dig for a playlist | both → `cancelled`; returns rowcount |
| 5 | Cancel owner-guard | another owner calls for a playlist not theirs | 0 rows; nothing changed |
| 6 | Terminal untouched | a `completed`/`failed` job | left unchanged |

- [ ] **Step 1:** Write failing integration tests (real local Supabase): behaviors 2,3 in `share-tokens-cascade.test.ts`; 4,5,6 in `cancel-playlist-jobs.test.ts` (seed via service client, invoke RPC via the owner's session client).
- [ ] **Step 2:** Run `npx jest share-tokens-cascade cancel-playlist-jobs` → FAIL (constraint/RPC absent — apply migrations first via `supabase migration up` or the test harness reset).
- [ ] **Step 3:** Write the migration: orphan-cleanup `delete`; `alter table … add constraint … foreign key (playlist_id, owner_id) references playlists(id, owner_id) on delete cascade`; `create index if not exists share_tokens_playlist_id_idx`; the `request_cancel_playlist_jobs` function (verbatim from §B4) + `revoke all … from public` + `grant execute … to authenticated, service_role`. Apply the migration to local.
- [ ] **Step 4:** Run tests → PASS.
- [ ] **Step 5:** Full `npm test` (integration incl.); commit `feat(playlist-ux): 0019 share_tokens cascade FK + request_cancel_playlist_jobs RPC`.

---

### Task 7: `BlobStore.deletePrefix` (recursive)

**Files:**
- Modify: `lib/storage/blob-store.ts` (interface), `lib/storage/supabase/supabase-blob-store.ts`, `lib/storage/local/local-blob-store.ts`
- Test: `tests/lib/storage/blob-store-delete-prefix.test.ts` (unit, both impls' logic) + `tests/integration/supabase-blob-delete-prefix.test.ts`

**Interfaces:**
- Produces: `BlobStore.deletePrefix(p: Principal, prefix: string): Promise<void>`.

**Enumerated Behaviors**

| # | Behavior | Trigger | Expected |
|---|---|---|---|
| 1 | Rejects traversal | `prefix='..'` or `'a/../b'` | throws (via `assertLogicalKey`) before any storage op |
| 2 | Empty prefix = whole playlist | `prefix=''` | targets `<owner>/<playlist_key>/` root |
| 3 | Removes flat objects | `base.md`, `base.pdf` present | removed |
| 4 | Removes nested | `dig/<base>/<n>.rV.md` present | removed (recursive list) |
| 5 | Paginates | >100 objects | all removed (list offset loop) |
| 6 | Absent = no error | prefix empty of objects | resolves, no throw |
| 7 | Local recursive | local backend | `fs.rm(join(indexKey,prefix),{recursive,force})`; ENOENT-safe |

- [ ] **Step 1:** Write failing unit tests: mock the Supabase storage `.list`/`.remove` to assert recursion+pagination+empty-prefix path building and `assertLogicalKey` rejection; local test with a temp dir asserting recursive removal + ENOENT tolerance.
- [ ] **Step 2:** Run `npx jest blob-store-delete-prefix` → FAIL.
- [ ] **Step 3:** Add interface method. Supabase impl: `assertLogicalKey(prefix)`; recursive walk — `list('<owner>/<indexKey>/<prefix>'.replace(/\/$/,''), {limit:100, offset})`, for entries with `id===null` recurse into the sub-path, collect file object paths, `remove(batch)` in ≤1000 chunks; tolerate empties. Local impl: `assertLogicalKey(prefix)` then `fs.rm(join(indexKey, prefix), {recursive:true, force:true})`.
- [ ] **Step 4:** Run unit → PASS. Write + run the integration test (real Storage): put flat + nested objects under a principal, `deletePrefix(p,'')`, assert `.list` returns empty.
- [ ] **Step 5:** Full `npm test`; commit `feat(playlist-ux): BlobStore.deletePrefix recursive (traversal-guarded)`.

---

### Task 8: `MetadataStore.deletePlaylist` + `requestCancelPlaylist` wrapper

**Files:**
- Modify: `lib/storage/metadata-store.ts`, `lib/storage/supabase/supabase-metadata-store.ts`, `lib/storage/local/local-metadata-store.ts`, `lib/storage/supabase/supabase-job-queue.ts`
- Test: `tests/lib/storage/supabase-metadata-store.test.ts` (add), `tests/integration/delete-playlist-store.test.ts` (new)

**Interfaces:**
- Produces: `MetadataStore.deletePlaylist(p: Principal, playlistId: string): Promise<void>` (cloud: `.delete().eq('id',id).eq('owner_id',ownerId)`); `SupabaseJobQueue.requestCancelPlaylist(playlistId: string): Promise<{cancelled:number}>` (calls the RPC).

**Enumerated Behaviors**

| # | Behavior | Trigger | Expected |
|---|---|---|---|
| 1 | Owner-scoped delete | cloud delete | query has `.eq('id')` AND `.eq('owner_id')` |
| 2 | Cascade (integration) | delete playlist w/ videos+jobs+share_token | all child rows gone |
| 3 | Non-owner no-op | delete another owner's id | 0 rows; their data intact |
| 4 | Cancel wrapper | `requestCancelPlaylist(id)` | RPC `request_cancel_playlist_jobs` invoked; returns count |
| 5 | Local delete | local backend | throws cloud-only (delete UI is cloud-only) |

- [ ] **Step 1:** Unit: assert the delete query chain predicates and the queue wrapper's RPC name. Add interface methods.
- [ ] **Step 2:** `npx jest supabase-metadata-store` → FAIL.
- [ ] **Step 3:** Implement cloud `deletePlaylist` (auth guard → scoped delete), queue `requestCancelPlaylist` (`rpc('request_cancel_playlist_jobs',{p_playlist_id})`), local `deletePlaylist` throw.
- [ ] **Step 4:** Unit → PASS. Integration `delete-playlist-store.test.ts`: seed playlist+video+job+share_token, `deletePlaylist` → assert all gone via SQL; non-owner attempt leaves data (isolation).
- [ ] **Step 5:** Full `npm test`; commit `feat(playlist-ux): deletePlaylist store method + requestCancelPlaylist wrapper`.

---

### Task 9: `DELETE /api/playlists/[id]` route + client fn

**Files:**
- Create: `app/api/playlists/[id]/route.ts`
- Modify: `lib/client/api.ts` (add `deletePlaylist`)
- Test: `tests/integration/delete-playlist-route.test.ts` (new) + unit for the failure/ordering branches

**Interfaces:**
- Consumes: `createServerSupabase`, `getStorageBundle` (metadataStore, blobStore, jobQueue), T6 RPC via T8 wrapper, T7 `deletePrefix`, T8 `deletePlaylist`.
- Produces: `DELETE` → `{deleted:true}` | 401 | 404; client `deletePlaylist(id): Promise<void>` (404 treated as success).

**Enumerated Behaviors**

| # | Behavior | Trigger | Expected |
|---|---|---|---|
| 1 | 401 | no session | 401 |
| 2 | 404 not owned/missing | id not the owner's | 404, nothing deleted |
| 3 | Happy path order | valid delete | read key → cancel (all kinds) → DB delete (cascade) → blob deletePrefix('') → 200 |
| 4 | Blob failure ⇒ 200 | `deletePrefix` throws | still 200 `{deleted:true}` (log; invisible orphans) |
| 5 | key captured pre-delete | — | `playlist_key` read before the DB delete (used for blob prefix) |
| 6 | Second delete | already deleted | 404; client maps 404→resolve |
| 7 | Cloud-only | local backend | 404/unsupported |

- [ ] **Step 1:** Write failing tests: integration for 1,2,3,6 (real Supabase — seed, DELETE, assert DB+blobs gone, isolation); unit for 4,5 (mock bundle so `blobStore.deletePrefix` rejects → still 200; assert key read precedes delete call order).
- [ ] **Step 2:** `npx jest delete-playlist-route` → FAIL.
- [ ] **Step 3:** Implement route (cloud branch): getUser→401; read the playlist (RLS) → 404 if absent; capture `playlist_key`; `try{ await queue.requestCancelPlaylist(id) }catch{log}`; `await metadataStore.deletePlaylist(principal, id)`; `try{ await blobStore.deletePrefix(principal,'') }catch{log}`; return `{deleted:true}`. Add client `deletePlaylist` (DELETE; 404→resolve; 401→throw UnauthorizedError).
- [ ] **Step 4:** Run tests → PASS.
- [ ] **Step 5:** Full `npm test`; commit `feat(playlist-ux): DELETE /api/playlists/[id] hard-delete (cancel→cascade→blobs)`.

---

### Task 10: Sidebar trash button + confirm modal

**Files:**
- Create: `components/cloud/DeletePlaylistDialog.tsx`
- Modify: `components/cloud/PlaylistSidebar.tsx`
- Test: `tests/components/cloud/DeletePlaylistDialog.test.tsx`, `tests/components/cloud/PlaylistSidebar.delete.test.tsx`, `tests/e2e/playlist-delete.spec.ts`

**Interfaces:**
- Consumes: `deletePlaylist` (T9). Modal modeled on `NewPlaylistModal` (focus trap, Esc, returnFocus, submit guard).

**Enumerated Behaviors** (modal + button — dismissal rows are mandatory)

| # | Behavior | Trigger | Expected |
|---|---|---|---|
| 1 | Trash opens modal, no nav | click trash button | modal opens; row `<Link>` NOT followed (button is a sibling, `stopPropagation`) |
| 2 | Cancel dismiss | Cancel click (not deleting) | close, no delete, focus returns to trigger |
| 3 | Escape dismiss | Esc (not deleting) | close, no delete |
| 4 | Backdrop dismiss | backdrop click (not deleting) | close, no delete |
| 5 | Close ✕ dismiss | ✕ click (not deleting) | close, no delete |
| 6 | Dismissal disabled mid-delete | Cancel/Esc/backdrop/✕ while deleting | no-op (guarded) |
| 7 | Success | Delete → resolves | "Deleting…" state → modal closes, list refetched, nav to `/` if the active playlist was deleted |
| 8 | Error keeps modal | Delete → rejects | inline error, modal stays open, buttons re-enabled |
| 9 | Copy | — | shows the playlist title + "cannot be undone" |

- [ ] **Step 1:** Write failing component tests for the modal (behaviors 2–9, all four dismissal paths + disabled-mid-delete + success nav + error) and the sidebar (behavior 1: trash is a sibling of `<Link>`, click opens modal without navigation). Mock `deletePlaylist`.
- [ ] **Step 2:** `npx jest DeletePlaylistDialog PlaylistSidebar.delete` → FAIL.
- [ ] **Step 3:** Build `DeletePlaylistDialog` (adapt `NewPlaylistModal`: focus trap, Esc/backdrop/✕/Cancel all gated on `!deleting`; Delete → `setDeleting(true)`, call `deletePlaylist(id)`, on success `onDeleted()`, on error show message + `setDeleting(false)`). Wire into the sidebar `<li>` as a sibling button; `onDeleted` refetches and navigates to `/` when the deleted id is the active one.
- [ ] **Step 4:** Run component tests → PASS. Write the E2E (`playlist-delete.spec.ts`, route-level mock): fixtures include a null-title AND a titled playlist (conditional-render rule); exercise open→each dismissal path→delete→list updates.
- [ ] **Step 5:** Full `npm test` + `npx playwright test playlist-delete`; commit `feat(playlist-ux): sidebar delete button + confirm modal`.

---

## Self-Review (author checklist — done)

- **Spec coverage:** A0/A1 (T1,T2), A2 backend (T3,T4) + frontend (T5), B2 migration (T6), B3 blobs (T7), B5/B6 store+route (T8,T9), B7 UI (T10). All §sections mapped.
- **Type consistency:** `fetchPlaylistTitleOrNull`, `setPlaylistTitleIfNull`, `deletePlaylist`, `requestCancelPlaylist`, `deletePrefix`, `backfillPlaylistTitles(): {updated,attempted}` used identically across producing/consuming tasks.
- **Mandatory categories:** URL-generating (T9 DELETE, T4 POST, T5 nav — exact methods/paths in behaviors); modal dismissal (T10 all four paths + disabled-mid-delete); optional-prop/null render (T5/T10 fixtures include null-title + titled). Isolation tests in T4,T6,T8,T9.
- Placeholder scan: none.
