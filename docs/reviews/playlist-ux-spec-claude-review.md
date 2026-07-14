# Adversarial Review — Playlist Sidebar UX Design Spec (Claude)

**Spec:** `docs/superpowers/specs/2026-07-13-playlist-sidebar-ux-design.md`
**Reviewer:** Claude (independent adversarial pass)
**Scope:** Feature A (BUG-6 naming: forward-fix + backfill) and Feature B (full hard-delete: composite cascade FK, recursive `deletePrefix`, cancel-first, owner-scoped DELETE route, UI).
**Method:** every factual claim in §3 Grounding verified against code; FK/reference graph re-derived from all 18 migrations; delete interleavings and RLS/storage isolation traced.

## Verdict

**No Blocking findings. Two High, three Medium, several Low.**

The core architecture is sound and the §3 grounding facts are accurate. The composite cascade FK is constructible (`playlists` has `unique (id, owner_id)` at `0001:18`) and owner-safe; the DB-before-blobs delete ordering is correct (residue is invisible orphans, never visible breakage); storage RLS (`0007:12-15`) authorizes the session-client blob cleanup. The two High items are in Feature A (naming), not delete.

---

## Blocking

None.

Cross-tenant isolation holds throughout: the parent `DELETE playlists` is RLS-guarded (`owner_id = auth.uid()`, `0002:4-5`); the cascade only removes children whose `(playlist_id, owner_id)` match the deleted playlist, so only the caller's own videos/jobs/share_tokens go; blob cleanup is scoped to `<auth.uid()>/…` by storage RLS. No path lets one owner delete or read another's playlist, blobs, or share tokens.

---

## High

### H1. `fetchPlaylistTitle`'s list-id fallback defeats the null-retry AND the `'Untitled playlist'` safety net; persists a cryptic list-id as a sticky title

`fetchPlaylistTitle` (`lib/youtube.ts:114-118`) returns `res.data.items?.[0]?.snippet?.title ?? playlistId` — it **never returns null and only throws on an API/network error**. A successful call for a private / deleted / non-existent / title-less playlist returns HTTP 200 with an empty `items` array, so the function returns the raw **list-id** (e.g. `"PLxxxx…"`), not an error.

Consequences, both contradicting the spec's stated invariants:
- **Forward-fix (§4 A1, lines 71-77):** the spec claims a title miss "leaves title null; backfill will retry." False. The `try` block only reaches `catch` on a thrown error; the empty-items case returns the list-id, and `setPlaylistMeta` persists `playlist_title = "PLxxxx"` (non-null).
- **Backfill (§4 A2) + read fallback (§4 A2, line 96 / sidebar `?? 'Untitled playlist'`, `PlaylistSidebar.tsx:92`):** backfill only touches *null-title* rows, so a row that got the list-id is **never retried and never falls back to `'Untitled playlist'`**. The user sees a cryptic `PLxxxx` string as the playlist name, permanently — arguably worse than the "Untitled playlist" bug being fixed.

**Scenario:** ingest a playlist that is private/region-blocked to the API key → YouTube returns 200 empty items → title persisted as `"PL9tQ6...abcd"` → sidebar shows `PL9tQ6...abcd` forever; backfill skips it (non-null).

**Fix:** treat "no real title" as a miss. Either (a) have callers detect `title === listId` (or add a `fetchPlaylistTitleOrNull` that returns `null` on empty items) and **skip the persist** so the row stays null → backfill + `'Untitled playlist'` fallback both keep working; or (b) explicitly persist `null` on that case. Add a unit test for the empty-items path (currently untested — see L4).

### H2. Auto-backfill-on-mount can become an unbounded backfill→refetch loop (YouTube quota burn) if not ref-guarded

§4 A2 / §6 D1: "`PlaylistSidebar`, after loading playlists, if ≥1 has a null `playlistTitle`, fires `backfillPlaylistTitles()` **once per mount**, then re-fetches the list." "Once per mount" is the correct intent but is underspecified for a React effect. If the trigger is expressed as an effect gated only on "≥1 null title" with `playlists` in its dependency array, the post-backfill refetch calls `setPlaylists`, which re-runs the effect; if **any** row is still null (a YouTube error path — `fetchPlaylistTitle` *throws* under 403 quota / 429 / network, leaving the row null), the "≥1 null" condition is still true → backfill fires again → refetch → loop. The failure mode is worst exactly when it hurts most: an already rate-limited/quota-exhausted API key gets hammered.

Secondary: React 18 StrictMode double-invokes effects in dev → two concurrent backfills / double YouTube calls on first mount.

**Fix:** gate the trigger on a `useRef(false)` "fired once this mount" flag set **before** the call; never derive the trigger from `playlists` state. Spec should mandate the ref mechanism explicitly (not just the words "once per mount"). Note H1's fallback interacts here: once H1 is fixed so genuine-miss rows stay null, the loop risk becomes *more* real, so H2 must be fixed alongside H1.

---

## Medium

### M1. Backfill must re-supply the existing `playlist_url` to `setPlaylistMeta` or it clobbers a NOT NULL column

§4 A2 step 2 says only "persist via `setPlaylistMeta`." But `setPlaylistMeta` (`supabase-metadata-store.ts:65-83`) upserts `playlist_url: meta.playlistUrl` — the URL is a **required** field of its `meta` arg and the column is `NOT NULL` (`0001:14`). If backfill calls it without the row's existing URL (or with `''`/undefined), it either throws a NOT NULL violation or overwrites `playlist_url` with an empty string. The data is available (`PlaylistSummary.playlistUrl`, `metadata-store.ts`), but the spec step must state it explicitly: pass `{ playlistUrl: row.playlistUrl, playlistTitle }`. Add a test asserting `playlist_url` is unchanged after backfill.

### M2. `deletePrefix` local impl (§B3) omits `assertLogicalKey(prefix)` — path-traversal hole in the interface

The §B3 local snippet is `fs.rm(join(indexKey, prefix), { recursive: true, force: true })` with no key validation, whereas every other local method routes through `abs()` which calls `assertLogicalKey` (`local-blob-store.ts:8`), and the Supabase `objectKey` also asserts (`supabase-blob-store.ts:12`). The delete route only ever passes `prefix === ''` today, so it is not currently exploitable — but `deletePrefix(p, prefix)` is a public interface method; a future caller passing `'..'` or `'../other-key'` would `fs.rm -rf` outside the playlist dir. Add `assertLogicalKey(prefix)` at the top of both impls for symmetry and defense-in-depth. (Note: `assertLogicalKey('')` correctly passes — no leading `/`, no `..`, no `\0` — so the empty-prefix case is legal, as the spec claims.)

### M3. Cascade-through-force-RLS on `share_tokens` is correct but load-bearing and non-obvious — the integration test is mandatory, not optional

`share_tokens` has `force row level security` and **no `authenticated` policy or grant** (service-role only, `0013:16-18`). The spec relies on the `ON DELETE CASCADE` referential action bypassing RLS/grants (Postgres runs RI actions as the table owner, and "foreign key references always bypass row security"). This is **correct** — it is exactly how the existing `videos`/`jobs` cascades already work — but it is subtle enough that a later "cleanup" (e.g. someone swapping the FK for a SECURITY DEFINER RPC, or adding a restrictive policy) could silently break share-token cleanup and leave orphaned share links pointing at a deleted playlist. The §7 B2 integration test ("adding a share_token then deleting its playlist removes it") is therefore **not optional** — it is the only guard on this invariant. Flag it as required-to-keep-green, and add an assertion that the token row is *gone* (queried via service client, since RLS hides it from any session client).

---

## Low

### L1. `serve_model_charge` IS playlist-scoped — §5.1 "not playlist-scoped, untouched" is factually inaccurate
`serve_model_charge.doc_key = p_playlist_id::text || '/' || p_video_id` (`0012:9`, `0012:53`). Rows are per-(owner, playlist, video, day) with no FK to `playlists`, so they are **not** cascade-deleted. Functionally harmless — a deleted+recreated playlist gets a fresh `gen_random_uuid()` id → a new `doc_key` → no false dedup/charge collision, and the rows are invisible day-keyed billing residue. But the §5.1 claim that it is "not playlist-scoped" is wrong; correct the reference-graph statement to "playlist-scoped via `doc_key`, intentionally left as invisible expiring residue." Same nuance applies loosely to any `doc_key`-derived accounting; none causes visible breakage.

### L2. No index on `share_tokens(playlist_id)` → cascade delete does a seq scan
The new FK's cascade must find `share_tokens` rows by `(playlist_id, owner_id)`; the only index is `share_tokens_owner_idx (owner_id)` (`0013:19`). For a small table this is fine, but the migration could add `create index on share_tokens (playlist_id)` (or the composite) to keep the cascade indexed, matching the pattern elsewhere.

### L3. Backfill route should read `YOUTUBE_API_KEY` once and short-circuit if unset
The producer throws `'YOUTUBE_API_KEY is not set'` (`producer.ts:44-45`). In the backfill route, if the key is missing the per-row try/catch would swallow N failed `fetchPlaylistTitle` calls and return `updated: 0` after wasting N attempts. Read the key once up front; if unset, return `{ updated: 0, attempted: 0 }` (or 500) without looping. The key is a server env var and IS available in the route runtime (same context as the ingest route), so availability itself is not a concern.

### L4. Test coverage gaps
- **(ties to H1)** No test for `fetchPlaylistTitle` returning the list-id on empty items — the exact case that produces a sticky cryptic title. Add it once H1's fix defines the intended behavior.
- **(ties to M1)** No test asserting `playlist_url` is preserved across backfill.
- Otherwise the §7 plan meets the dev-process rules: isolation (non-owner 404 + nothing deleted, §7 B4/B5), null/non-null conditional-render fixtures (§7 B7), and all four dismissal paths incl. disabled-while-deleting (§5 Overlay Dismissal table + §7 B7). These are adequate as written.

### L5. Delete route defense-in-depth
`DELETE` step 4 (`supabase.from('playlists').delete().eq('id', id)`) relies on RLS alone. `listPlaylists` already adds an explicit `.eq('owner_id', ownerId)` as defense-in-depth (`supabase-metadata-store.ts:204`); mirror that on the delete for consistency (RLS already makes it correct, so this is belt-and-suspenders).

---

## Interleaving analysis (delete sequence §B5) — no visible-breakage path found

Traced worker/delete races: DB-commit-before-blobs is the correct order. Every partial-failure interleaving leaves only **invisible** residue (orphaned blobs with no referencing row, or day-keyed billing rows), never a listed playlist whose summaries 404. Confirmed:
- Blob cleanup (step 5) failure → 200 + orphaned blobs; playlist row already gone → not listed → no visible breakage. ✔
- Active worker writes a blob after step 5 → orphan (spec's accepted residual). ✔
- Active job's `persist_summary` after the playlist row is deleted → it `raise`s "playlist not owned" (`0009:109-110`) rather than no-oping (the spec §B4 says `complete_job`/`fail_job` no-op, which is true, but `persist_summary` *throws*); the worker's error handling then calls `fail_job` → 0 rows (job row cascade-deleted) → no crash. Behaviorally fine; the spec's §B4 wording slightly understates it (persist raises, not no-ops) — worth a one-line correction but not a defect.
- Concurrent double-DELETE: second request's step-2 read 404s (row gone) → client treats as success. ✔

The `ALTER TABLE ADD CONSTRAINT` (§B2) will not fail on existing data: the orphan-cleanup `DELETE` runs first and removes any row lacking a matching `(id, owner_id)`, and no playlist-delete path exists today so there are effectively no orphans to clean. The cleanup query is owner-safe (matches on both `playlist_id` and `owner_id`).

---

## Round 2 re-review

**Revised spec:** `docs/superpowers/specs/2026-07-13-playlist-sidebar-ux-design.md` (post round-1 fixes)
**Scope:** (a) verify each round-1 fix is genuinely fixed in spec text against real code; (b) hunt for new defects the fixes introduced, with special attention to the all-kinds cancel RPC × cascade-delete × lease-sweep × `complete_job`/`persist_summary` worker interaction.
**Method:** re-read `lib/youtube.ts`, `producer.ts`, `supabase-metadata-store.ts`, `blob-store.ts` (+ local/supabase impls), `dig-blob-key.ts`, `worker-runner.ts`, migrations `0002/0008/0009/0010/0012/0013/0018`, `app/api/jobs/cancel/route.ts`, `supabase-job-queue.ts`, `PlaylistSidebar.tsx`; traced the cancel→cascade→worker path end-to-end.

### Verdict: convergence reached — **no new Blocking, no new High.** All seven round-1 items GENUINELY FIXED. New findings are Low only.

### Round-1 fix verification

**1. H1 fake-title fallback — GENUINELY FIXED.**
`fetchPlaylistTitleOrNull` (§A0) returns `snippet?.title ?? null` (no list-id fallback); A1 (producer) and A2 (backfill) both call it and persist **only** a non-null title, so a 200-empty-items miss leaves the row null → `'Untitled playlist'` fallback + backfill-retry both keep working. **Delegation is safe:** the retained `fetchPlaylistTitle = (await fetchPlaylistTitleOrNull(id,key)) ?? id` is behaviorally identical to today's `?? playlistId`, so the three existing callers — `pipeline.ts:195`, `output-folder.ts:73`, `lib/playlists/backfill-titles.ts:37` — are unchanged. **Remaining list-id-persisting path:** only `lib/playlists/backfill-titles.ts` (the *local-filesystem* backfill) still persists the fallback via the delegated `fetchPlaylistTitle` — but that is the local backend, explicitly out of scope (§2), and it writes local `playlist-index.json`, never a cloud row. No **cloud** path persists a list-id. Fixed for the spec's cloud scope. (See Low N4 for a naming/awareness note on that module.)

**2. H2 auto-backfill loop — GENUINELY FIXED.**
§A2 trigger now mandates a `useRef(false)` one-shot set **before** the call and explicitly *not* derived from `playlists` state, so the post-backfill refetch (which may still hold null rows) cannot re-fire it; React 18 StrictMode's setup→cleanup→setup on the same fiber preserves the ref, absorbing the double-invoke. A `sessionStorage` flag suppresses re-runs across remounts/navigations, and the **25-row server cap** (§A2 step 2) is a hard backstop. The unbounded loop is closed. Residual multi-tab duplication is bounded, not a reintroduced loop — see Low N2.

**3. Dig cancel gap — GENUINELY FIXED.**
Confirmed the gap is real: `SupabaseJobQueue.listByPlaylist` (`supabase-job-queue.ts:28`) filters `.eq('job_kind','summary')`, so the existing route cancel misses `dig`. The new `request_cancel_playlist_jobs` (§B4) is correct SQL: `security definer set search_path = public`; **no `job_kind` filter** (all kinds); `where playlist_id = p_playlist_id and owner_id = auth.uid() and status in ('queued','active')` — owner-guarded, terminal statuses (completed/failed/cancelled/dead_letter) untouched, queued→cancelled / active→flagged, mirroring `request_cancel_job` (`0010`); `revoke all … from public` + `grant execute … to authenticated, service_role` (drops `anon` vs `0010` — least-privilege, and the delete route is authenticated-only, so correct). No injection surface (single uuid param, no dynamic SQL). See the cancel × cascade × worker trace below — no worker error path.

**4. Backfill clobber / NOT NULL — GENUINELY FIXED.**
`setPlaylistTitleIfNull` (§A2) updates only `playlist_title` with predicate `owner_id = auth.uid() and playlist_key = $listId and playlist_title is null`. It never touches `playlist_url`, so the `NOT NULL` column cannot be violated/blanked; the `is null` predicate makes it non-clobbering of a concurrently-written real title. Owner-scoping is correct **even though `playlist_key` is not globally unique** (two owners can share a list-id): the `playlists_owner` RLS policy (`0002:4-5`, `using` **and** `with check` = `owner_id = auth.uid()`) confines a session-client update to the caller's own row. (Minor: the spec writes the predicate in SQL-notation `auth.uid()`; implemented as a session-client `.update().eq('playlist_key',…).is('playlist_title',null)` the owner scope comes from RLS, not a literal `auth.uid()` in JS — same result. Impl-clarity only.)

**5. Path traversal — GENUINELY FIXED.**
`assertLogicalKey(prefix)` is now mandated **first** in both `deletePrefix` impls (§B3). Verified against the real predicate (`blob-store.ts:21-25`): `''` → `startsWith('/')` false, `''.split('/')=['']` no `'..'`, no `\0` → **passes** (empty-prefix legal, as claimed); `'..'`, `'../other'`, `'foo/../bar'` all contain a `'..'` path segment → **throw**. Both impls further run under owner-scoped storage/fs roots, so it is defense-in-depth over an already-scoped path.

**6. `serve_model_charge` retention — GENUINELY ADDRESSED (documented, claim verified true).**
The "never re-matched (fresh UUID)" claim is **factually true**: `resolvePlaylistId` (`supabase-metadata-store.ts:186-191`) upserts on `(owner_id, playlist_key)`; after a delete the row is gone, so re-ingesting the same YouTube playlist **inserts a new row with a fresh `gen_random_uuid()` id** → `doc_key = '<new-uuid>/<video_id>'` can never collide with the old `doc_key`. No false dedup, no double-charge, no cross-tenant read (rows are `owner_id`-scoped, force-RLS, service-role-only). Not a leak. Retention is defensible (immutable billing/audit, same posture as `spend_ledger`/`usage_counters`). Two minor caveats in Low N3 (unbounded across re-create cycles; privacy wording of the "permanent delete" copy).

**7. Round-1 Low items — all PRESENT.**
- `share_tokens(playlist_id)` index: §B2 line 175 `create index if not exists share_tokens_playlist_id_idx …`. ✔
- Delete route `.eq('owner_id', user.id)`: §B5 step 4. ✔
- Trash button **sibling** of `<Link>`, not nested, `<li>` holds `[<Link>,<button>]` + `stopPropagation/preventDefault`: §B7. ✔
- B2 cascade integration test **mandatory** (queried via service client since RLS hides the row): §7 "B2 cascade (integration — MANDATORY)". ✔

### Cancel × cascade × lease-sweep × worker trace (the convergence-critical check)

Traced an **active** dig/summary job whose row is cascade-deleted mid-flight after `request_cancel_playlist_jobs` flags it:
- `complete_job` / `fail_job` / `heartbeat_job` / `set_progress_phase` all key on `id = … and status = 'active'` (`0008`) → row gone → **0 rows** → return `false`/`null`. `worker-runner.ts:56-57` maps `ok=false` → `'lost'`; `:62-66` maps `fail` `ok=false` → `'lost'`; `:67-72` even a *throwing* terminal RPC resolves to `'lost'`. No unhandled rejection.
- `persist_summary` (`0009`) **raises** `'playlist … not owned'` when the playlist row is gone (it `raise`s, it does not no-op — §B4's "no-op" wording understates this, carried Low N5). That raise occurs **inside** the handler, is caught at `worker-runner.ts:58`, and routes to `fail` → `'lost'`. No crash.
- `ctx.isCancelled` → `queue.getStatus(gone-id)` → null → `false`; benign (handler keeps running, terminal write no-ops).
- Queued→cancelled jobs are never claimed (`claim_next_job` filters `status='queued'`), then cascade-deleted — no worker ever touches them.
- `sweep_expired_leases` simply finds no row. Row-lock serialization between the cancel `UPDATE` and `claim_next_job`'s `for update skip locked` prevents any lost-update or deadlock.

**Conclusion:** cancelling then cascade-deleting an active job's row produces **no worker error path** — every terminal write degrades to `'lost'`. The spec's core new-interaction claim holds.

### New findings (Low only)

- **N1 (Low) — migration number placeholder.** §B2/§B4 name the file `00NN_share_tokens_cascade.sql`. The highest existing migration is `0018_enqueue_dig.sql`, so the concrete file must be **`0019_…`**. Trivial, but pin it so the migration actually applies in order.
- **N2 (Low) — `sessionStorage` is per-tab, not per-session-shared.** §A2 says the flag runs backfill "at most once per browser **session** across mounts/navigations." `sessionStorage` is scoped per tab/window, so N tabs = up to N backfill calls. This does **not** reintroduce the H2 loop: each call is capped at 25 rows and is idempotent (only null rows), so once titles fill, further calls do 0 work — the cost is a bounded handful of duplicate YouTube lookups, not an unbounded loop. Reword "per session" → "per tab", or accept as-is; either way bounded.
- **N3 (Low) — retention vs. the "permanent delete" promise.** The confirm copy (§B7) says delete "permanently removes the playlist, all its summaries, PDFs, and any share links. This cannot be undone." Correct for those; but `serve_model_charge` (and `spend_ledger`/`usage_counters`) retain rows whose `doc_key` embeds `playlist_id/video_id` — a per-video record survives the "permanent" delete, and the table grows unbounded across repeated delete→re-ingest cycles (no FK to `playlists`; cascade is only on `profiles`). Defensible as an immutable billing/audit ledger (money was spent), but (a) the growth is worth a future storage/retention sweeper note, and (b) the user-facing "permanently removes … all its summaries" copy slightly overstates vs. retained billing residue — consider a one-line spec note that immutable billing records are intentionally exempt.
- **N4 (Low/info) — existing `lib/playlists/backfill-titles.ts`.** A **local-filesystem** `export async function backfillPlaylistTitles(root, apiKey)` already exists and still persists the list-id fallback (unfixed H1 for local, out of scope). Name overlap with the spec's `lib/client/api.ts → backfillPlaylistTitles()` is in a different module (no collision), but implementers should be aware of the existing symbol and that the local path is deliberately left unchanged.
- **N5 (Low, carried) — §B4 "no-op" wording.** As in round-1: for an active job whose row is cascade-deleted, `persist_summary` **raises** (caught → `fail` → `'lost'`) rather than no-oping; only `complete_job`/`fail_job` literally no-op. Behavior is correct; one-line wording fix only.

### Convergence statement

This is a full re-review round that **verified every round-1 Blocking/High/Medium/Low fix as genuinely applied (not reworded)** and surfaced **no new Blocking or High** — only five Low notes, all with obvious dispositions. Per `docs/dev-process.md` → Iterative Re-Review "Stop (diminishing returns)", this round **is the gate**: the spec has converged. Remaining Low items can be folded into implementation or accepted as documented.
