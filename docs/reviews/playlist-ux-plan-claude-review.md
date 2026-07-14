# Adversarial Review — Playlist Sidebar UX Implementation Plan (Claude)

**Artifact:** `docs/superpowers/plans/2026-07-13-playlist-sidebar-ux.md`
**Spec:** `docs/superpowers/specs/2026-07-13-playlist-sidebar-ux-design.md`
**Reviewer:** Claude (adversarial), verified against live code.
**Date:** 2026-07-13

## Verdict

**2 High, 3 Medium, 4 Low. No Blocking.** Spec coverage is complete and task ordering
is sound, but two High findings would stop a subagent following the sketches literally
(a missing `userId` source for the T5 backfill guard, and a missing `JobQueue` interface
method that makes the T9 route not typecheck). Both are small, non-goal-moving fixes.

---

## Coverage & ordering (verified OK)

- **Spec coverage:** every section maps to a task — §A0→T1, §A1→T2, §A2→T3/T4/T5, §B2→T6,
  §B3→T7, §B4→T6(RPC)+T8(wrapper), §B5→T9, §B6→T5/T8/T9, §B7→T10. No requirement is unbuilt.
- **Dependency order:** T1/T3 precede T4; T4 precedes T5; T6/T7/T8 precede T9; T6(RPC) precedes
  T8(wrapper). All producers defined before consumers. No interface used before its defining task
  *except* the two High items below (which are interfaces the plan never assigns to any task).
- **T6 RED soundness (the flagged worry) is actually fine:** migration `0019` does not exist yet,
  so applying migrations gives 0001–0018 only; the cascade FK and `request_cancel_playlist_jobs`
  RPC are genuinely absent → the cascade assertion and the `rpc(...)` call (PGRST202) fail for the
  right reason. Not an unsound RED. (One caveat under Medium re: behavior 1.)
- Storage RLS permits the session-client delete path: `artifacts_owner_rw` is `for all to
  authenticated, anon using (split_part(name,'/',1)=auth.uid())` (`0007:12-15`), so a session-client
  `.list()`/`.remove()` over the owner prefix is allowed — T7/T9's owner-scoped blob delete works
  without service-role. Good.

---

## High

### H1 — T5 backfill guard needs a `userId` the sidebar does not have; per-user sessionStorage key is unbuildable as sketched
**Problem:** T5 Step 3 and behavior #4 key the one-shot on `sessionStorage['backfilledTitles:'+userId]`
(spec §A2 M-b *explicitly rejected* an origin-global key). But `PlaylistSidebar`'s props are
`{ onNewPlaylist? }` only (`PlaylistSidebar.tsx:27-31`) and `listPlaylists()` returns
`PlaylistSummary[]` with no owner id — there is **no `userId`/`user.id` in scope**. `CloudApp` *has*
it (`session.userId`, `CloudApp.tsx:40`) but renders `<PlaylistSidebar onNewPlaylist=… />`
(`CloudApp.tsx:82`) without threading it. A subagent following the sketch literally will either not
compile or silently fall back to a global key — the exact bug the spec forbade.
**Task/step:** T5 Step 3 (and File Structure omits the `CloudApp.tsx` edit).
**Fix:** Add a `userId: string` (or `session`) prop to `PlaylistSidebar`, pass `session.userId` from
`CloudApp.tsx:82`, and list `components/cloud/CloudApp.tsx` in T5's Files. Add a behavior row asserting
the key is namespaced by the passed `userId`.

### H2 — `requestCancelPlaylist` is never added to the `JobQueue` interface; the T9 route will not typecheck
**Problem:** T8 adds `requestCancelPlaylist` only to the `SupabaseJobQueue` *class*
(`supabase-job-queue.ts`); the File Structure has no row for `lib/storage/job-queue.ts` (the
`JobQueue` interface, which today exposes only `listByPlaylist`/`requestCancel`, `job-queue.ts:24-25`).
T9 consumes it via `getStorageBundle(...).jobQueue`, typed `JobQueue | undefined` (`resolve.ts:17`) —
`queue.requestCancelPlaylist(id)` is a TS2339 compile error. (`SupabaseJobQueue` is the only
implementer, so widening the interface is clean.)
**Task/step:** T8 interfaces / File Structure; consumed in T9 Step 3.
**Fix:** Add `requestCancelPlaylist(playlistId: string): Promise<{cancelled:number}>` to the `JobQueue`
interface in T8 and list `lib/storage/job-queue.ts` in T8's Files. Also note T9 must handle
`jobQueue` being optional (`bundle.jobQueue!`, as `app/api/jobs/cancel/route.ts:24` does).

---

## Medium

### M1 — T6 behavior #1 (orphan cleanup) has no runnable test and is absent from the RED step
**Problem:** The behaviors table lists "orphan cleanup" (row 1) but Step 1 only writes tests for
rows 2,3 (cascade) and 4,5,6 (RPC). It is **not testable post-migration**: once the composite FK is
applied you cannot insert a pre-existing orphan to prove the pre-ALTER `delete` ran (the FK rejects
it). The load-bearing `delete from share_tokens where not exists(...)` line therefore ships unverified.
**Fix:** Either drop row 1 from the "tested behaviors" claim and document it as inherently
migration-ordering (verified only by "migration applies cleanly on a DB seeded with an orphan before
0019"), or add a dedicated ordering test that seeds an orphan against a pre-0019 schema snapshot.
Do not leave it implied as covered by Step 1.

### M2 — T9 "read the playlist" has no defined mechanism (no `getPlaylistById` store method)
**Problem:** B5/T9 Step 2 must "read the playlist (RLS) → 404 … capture `playlist_key`", but no
`MetadataStore` method returns one playlist by id, and the plan's interfaces don't add one. The route
must inline `supabase.from('playlists').select('playlist_key').eq('id', id).maybeSingle()` on the
session client. Also note the DELETE `.delete().eq('id').eq('owner_id')` returns success on 0 rows —
the 404 for not-owned/second-delete (behaviors 2,6) depends entirely on this read returning null under
RLS, not on the delete rowcount. That's correct but must be stated so it isn't implemented via the
(always-succeeding) delete.
**Fix:** Spell out the inline read in T9 Step 3 (or add a small `getPlaylistById` method), and make
the enumerated behaviors say "404 is driven by the pre-delete read, not the delete rowcount."

### M3 — T7 integration test should run through the SESSION-scoped blob store, not the service client
**Problem:** T9's delete uses the session-client `blobStore.deletePrefix`. T7 Step 4 says "integration
test (real Storage) … deletePrefix(p,'')" without specifying the client. If it seeds and deletes via
the service-role client (which bypasses storage RLS), it passes even if the owner-scoped `.list()`
path regresses. Given owner isolation is non-negotiable and a silent list-returns-empty would orphan
*every* blob, the test must prove the `authenticated` RLS path.
**Fix:** In T7 (and the T9 round-trip), construct `SupabaseBlobStore` on a `signInAs(...)` session
client for the delete/assert; seeding via the service client is fine.

---

## Low / Nits

### L1 — T2 title is not persisted when every video is skipped
`resolvePlaylistId` (and the spec §A1 persist block placed right after it) runs *after* the
`enqueueable.length === 0` early return (`producer.ts:69-74`). A playlist whose items are all
skipped/blocked never gets its title at ingest — left to backfill. Acceptable, but add an
Enumerated-Behaviors note so it isn't mistaken for a bug later.

### L2 — `setPlaylistTitleIfNull(p, listId, title)` has a redundant `listId`
The `Principal` already carries `indexKey === playlist_key` (`principal.ts:7`), and the cloud impl
keys on `auth.uid()` + `playlist_key`. Passing `listId` separately is confusing and invites a
mismatch. Consider `setPlaylistTitleIfNull(p, title)` deriving the key from `p.indexKey`, or document
why both are passed.

### L3 — T4 route must build a per-row `Principal`; not spelled out
Each null-title row needs `principal = { id: user.id, indexKey: p.playlistKey }` to call the store
method. Trivial but unstated in T4 Step 3 — worth a line so the subagent doesn't reach for a wrong
shape.

### L4 — `deletePrefix('')` on the local impl removes the whole index dir
Local `abs(p,key)=join(indexKey,key)`, so `fs.rm(join(indexKey,''),{recursive,force})` removes the
entire `indexKey` directory. Correct for the cloud-only delete semantics, but since the local delete
UI is out of scope, add a one-line comment that the local impl exists only for interface parity /
future use, to avoid a future caller nuking a shared local root.

---

## Notes on things checked and found correct

- `.is('playlist_title', null)` (T3) is valid supabase-js (PostgREST `is.null`).
- Supabase blob recursion sketch (T7) — folder entries have `id === null`, `.list({limit,offset})`
  pagination, `.remove(batch)` — matches the client the store already uses (`supabase-blob-store.ts`).
- `request_cancel_playlist_jobs` mirrors `request_cancel_job` (`0010`) — SECURITY DEFINER +
  `auth.uid()` guard works on the session client; `status in ('queued','active')`, terminal untouched,
  `grant execute to authenticated, service_role`, all-kinds (no `job_kind` filter) — all consistent
  with the existing summary-only `listByPlaylist` gap the spec fixes.
- DB-before-blobs ordering, `playlist_key` captured pre-delete, blob-failure-still-200 (D5) — all
  present in T9's behaviors.
- Route static/dynamic collision: `app/api/playlists/{route,recent,channel}` are static; adding
  `[id]` (dynamic) + `backfill-titles` (static) does not conflict in Next.js.
- Integration helpers used by the plan (`adminClient`, `newUser`, `signInAs`, `seedPlaylist`,
  `seedPromotedVideo`, `seedSummaryBlob`, `ensureGuardrailHeadroom`) all exist and match the described
  usage.
