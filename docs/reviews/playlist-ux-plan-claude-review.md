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

---

## Round 2 re-review

**Reviewer:** Claude (adversarial), verified against live code.
**Date:** 2026-07-13
**Scope:** (a) verify each round-1 finding is genuinely fixed, not reworded; (b) hunt for defects the fixes introduced.

### Verdict — CONVERGENCE (0 Blocking, 0 High)

All 2 High / 3 Medium / 4 Low from round 1 are genuinely fixed. Three **Medium** residuals remain — each a mechanical implementation-sketch gap (a `tsc --noEmit` gate would catch all three) rather than an architectural or goal-moving defect. None are Blocking or High. The plan is safe to execute; the three Mediums are worth a one-line tightening each so the executing subagent doesn't hit an avoidable mid-task typecheck failure.

### Round-1 items — FIXED / NOT-FIXED

1. **Integration test runner (Codex B1)** — **FIXED.** Global Constraints (plan:22) now names `npm run test:integration -- <pattern>` and the combined gate `npm test && npm run test:integration && npx tsc --noEmit`. Verified per task: T3 (Step4 `-- backfill-titles`, Step5 full gate), T4 (`-- backfill-titles-route`), T6 (`-- share-tokens-cascade cancel-playlist-jobs`), T7 (`-- supabase-blob-delete-prefix`), T8 (`-- delete-playlist-store`), T9 (`-- delete-playlist-route`) all carry the integration run **and** the full gate. T5/T10 (no integration) correctly use `npm test && npx tsc --noEmit` (+ playwright for T10). `package.json:18` confirms the script; `jest.config.ts` excludes `tests/integration/**`, so the split is real, not cosmetic.

2. **Principal construction (B2/H2)** — **FIXED.** `resolve.ts:93` signature is `getPrincipalFromSession(session:{userId:string|null}, indexKey:string)`. T4 Step3 builds `getPrincipalFromSession({ userId: user.id }, p.playlistKey)` (field name matches `PlaylistSummary.playlistKey`, `supabase-metadata-store.ts:210`); T9 Step3 builds it with the `playlist_key` captured from the pre-delete read. Both call sites match the real 2-arg signature. Global Constraints (plan:23) forbids the ad-hoc object. Genuinely fixed.

3. **`requestCancelPlaylist` on the `JobQueue` interface (Codex B3 / H2)** — **FIXED (design), with a residual — see M-A.** File Structure (plan:41) now lists `lib/storage/job-queue.ts` for T8; T8 interfaces (plan:256) states the method is "added to the `JobQueue` interface … not just the class," and Step1 adds it. Verified `job-queue.ts:22-33` is the interface and `SupabaseJobQueue` is the sole implementer (`resolve.ts:60`), so widening is clean and does **not** force the local bundle (which supplies no `jobQueue` — `resolve.ts:20,53`) or break existing callers (adding a method never breaks callers). The interface fix is real; the *route call site* still lacks the optional-chaining guard the round-1 fix note called for (M-A below).

4. **T5 userId threading + distinct-user test (H1)** — **FIXED (design), with a residual — see M-B.** Plan now threads `session.userId` CloudApp→CloudAppBody→PlaylistSidebar (plan:162,169), lists `CloudApp.tsx` in T5 Files, keys the guard on `backfilledTitles:${userId}`, and adds behavior #5 (distinct users, same tab → distinct keys). Verified CloudAppBody sits inside the `<Suspense>` boundary (`CloudApp.tsx:55-61`) and currently takes no props — passing a prop through a Suspense child is fine, no boundary breakage. The design gap is closed; a null-session type/semantic residual remains (M-B).

5. **T6 migration RED reasoning + orphan-cleanup (Codex H3 / M1)** — **FIXED.** Plan:210 now states the RED is sound because `0019` is genuinely absent, and explicitly reclassifies orphan-cleanup (behavior 1) as **not observable post-FK** → verified indirectly by "the ALTER ADD CONSTRAINT applies cleanly" + a migration comment. Step1 (plan:212) rewrites behavior-1's test as "constraint exists / migration applied," no longer implying a runnable orphan-insert. This is exactly what round-1 M1 asked for.

6. **`setPlaylistTitleIfNull` returns `{updated}`, drops `listId` (Codex M1 / L2)** — **FIXED.** T3 signature (plan:109) is `setPlaylistTitleIfNull(p, title): Promise<{updated:boolean}>`, derives the key from `p.indexKey`, no `listId` param; impl uses `.select('id')`, `updated = (data?.length ?? 0) > 0` (plan:122). T4 counts only real persists: `if (u) updated++` (plan:153). Both the redundant-param and the count-no-ops findings are addressed. (RLS-correctness of `.update().select()` independently verified — see New-issue A: not a defect.)

7. **T9 404 from pre-delete read, not delete rowcount (M2)** — **FIXED.** Plan:299 "404 source" note: 404 comes from `select('id, playlist_key').eq('id',id).maybeSingle()` under the RLS session client returning null, **not** the always-succeeding `.delete()` rowcount; the read also yields `playlist_key` for the blob Principal. Step3 (plan:303) implements exactly this. Verified the read needs no explicit `.eq('owner_id')` because `playlists_owner … for all using (owner_id=auth.uid())` (`0002_rls_policies.sql:4`) scopes it — a non-owner id returns null → 404.

8. **Spec §B6 + T8 both say local `deletePlaylist` throws cloud-only** — **FIXED / consistent.** Spec `design.md:292` ("Local impl throws cloud-only") and T8 (plan:266,270) agree; matches the existing local pattern (`local-metadata-store.ts:45-49` throws for `resolvePlaylistId`/`listPlaylists`).

### NEW findings (defects the fixes introduced or left)

#### Medium

**M-A — T9 route sketch omits the `bundle.jobQueue!` non-null guard; will not typecheck as written.**
`StorageBundle.jobQueue` is optional (`resolve.ts:17`, `JobQueue | undefined`). T9 Step3 (plan:303) writes `await bundle.jobQueue.requestCancelPlaylist(id)` with **no** `!`. Under strict TS that is a TS18048 "possibly undefined." Round-1 H2's fix note explicitly said "T9 must handle `jobQueue` being optional (`bundle.jobQueue!`)"; the revision added the interface method (the substantive half) but dropped the guard note. The sibling route already does it right: `const queue = bundle.jobQueue!;` (`app/api/jobs/cancel/route.ts:24`). Fix: in T9 Step3, capture `const queue = bundle.jobQueue!` (cloud branch is guaranteed to have it) before calling `requestCancelPlaylist`. One-token gap, but it is the exact typecheck failure H2 was meant to close.

**M-B — Null-session `userId` threading is type-unsafe and can reintroduce the forbidden global key.**
`CloudAppProps.session` is `{ userId; email } | null` (`CloudApp.tsx:40`). The round-1 fix (plan:169) threads `session?.userId`, which is `string | undefined`, into a prop the plan describes as "required-in-cloud `userId: string`" (plan:167). Passing `string | undefined` to a required `string` prop is a typecheck error; a subagent papering over it with `session?.userId ?? ''` would key on `backfilledTitles:` (an origin-global key) — the precise bug spec §A2 M-b forbade. Fix: either narrow before render (`{session ? <CloudAppBody userId={session.userId}/> : …}`) or type the prop `userId: string | undefined` and no-op the backfill when it is absent (an unauthenticated cloud render 401s and redirects anyway, so no-op is safe). The plan must state which, so the key is never built from `undefined`/`''`.

**M-C — T5 does not update the existing `PlaylistSidebar` tests that a required prop breaks.**
`tests/components/playlist-sidebar.test.tsx` renders `<PlaylistSidebar />` / `<PlaylistSidebar onNewPlaylist={…} />` at 8 sites (lines 56–116), none passing `userId`. Making `userId` a **required** prop makes every one of those a typecheck failure, which T5 Step5's `npx tsc --noEmit` gate will trip. T5's Files list and steps don't mention touching that file. Fix: add `tests/components/playlist-sidebar.test.tsx` to T5's Files (update the render calls to pass a `userId`), or make the prop optional with a documented no-op fallback (ties into M-B). `cloud-app*.test.tsx` render `<CloudApp session={…}/>` with a non-null session, so those pass the threading at runtime — only the standalone sidebar test breaks.

#### Low / nits (no action required to proceed)

- **N1 —** `.is('playlist_title', null).select('id')` was checked for the "returning re-evaluates the filter and drops the row" trap: PostgREST applies the `is null` filter to choose rows to update and RETURNING returns those rows regardless of their new values, so `updated:true` is correctly reported. Not a defect — noted because the task asked.

### New-issue checks that came back CLEAN

- **A — `.update(...).select('id')` under the RLS session client returns the updated row to the owner?** Yes. `playlists_owner … for all` (`0002_rls_policies.sql:4`) covers SELECT in the same policy, and the update doesn't change `owner_id` (WITH CHECK still holds). Precedent: `resolvePlaylistId` already does `.upsert(...).select('id').single()` on the session client (`supabase-metadata-store.ts:186-189`). No defect.
- **B — `bundle.jobQueue` undefined in DELETE route?** Real, captured as **M-A** (needs the `!` guard).
- **C — required `userId` prop breaks existing tests?** Real, captured as **M-C**.
- **D — any task referencing a type/interface a later task defines?** None. T9 (consumer) follows T6/T7/T8 (producers); T4 follows T1/T3; T5 follows T4; T10 follows T9; T2 follows T1. All producers precede consumers.

### Convergence statement

A full round-2 re-review found **no new Blocking and no new High**. All round-1 Blocking/High/Medium/Low are genuinely fixed (not reworded). The three residual Mediums (M-A/M-B/M-C) are mechanical, `tsc`-catchable, one-line fixes that do not move the goal or the architecture. Per the dev-process convergence rule this round **is** the gate. Recommend applying M-A/M-B/M-C as pre-execution tightenings (or letting the TDD gates catch them in-task), then proceeding to implementation.
