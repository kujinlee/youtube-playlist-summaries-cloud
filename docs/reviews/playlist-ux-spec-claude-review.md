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
