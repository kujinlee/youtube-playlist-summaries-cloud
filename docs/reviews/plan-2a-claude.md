# Claude (opus) Adversarial Review — Stage 2a Implementation Plan

**Reviewer:** Claude opus (independent) · **Date:** 2026-07-10 · **Target:** plan `24abf72`

**Verdict:** 0 Blocking · 1 High · 4 Medium · 5 Low. SQL/RLS/auth/ordering **sound** (converges with Codex).

## Confirmations
- T7 SQL valid; **parens load-bearing** (`-` binds tighter than `||`). `GET DIAGNOSTICS row_count` = 1 on matched-but-unchanged row (BEFORE trigger returns NEW) → I3 holds. `returns integer` round-trips as scalar. T1 trigger harmless/no-recursion. Ordering T1(0015)→T7(0016) correct (tip `0014`). `signInAs()` + per-file `STORAGE_BACKEND='supabase'` make the RLS/cross-owner tests implementable. Callback default `/library`→`/` fix is real.

## High
- **H1 — T3 local `listPlaylists` not implementable (same as Codex H1):** `listRecentPlaylists(root)` needs a root; returns `PlaylistOption` where `id` is the YouTube list-id (not `playlist_key`) and exposes no `createdAt` (mtime is used for sort then discarded). Local sidebar is never rendered in 2a; local `store.listPlaylists` is exercised only by its own unit test. **Fix (a, recommended):** local `listPlaylists` = `throw new Error('cloud-only')` (mirroring `LocalFsMetadataStore.resolvePlaylistId:45`); drop the local unit test; T4 local branch calls `listRecentPlaylists(root)` directly.

## Medium
- **M1 — T7 migration omits `revoke … from public; grant execute … to authenticated`** (`0007:43,73,97,121`; no blanket default-privilege revoke). Grant-less → **anon/public gets EXECUTE**; T7's §8 RLS review will flag it. Add the hardening to 0016.
- **M2 — T5/T6/T7/T8 omit UUID-format validation of `?playlist` before the DB call.** Exemplar guards it (`html/[id]/route.ts:37` `UUID_RE` → 400). Without it a malformed UUID reaches `.eq('id', <bad>)` → Postgres `invalid input syntax for type uuid` → **500 not 400**. Add the guard.
- **M3 — T2 test-churn underestimated:** `index-store.updateVideoFields`/`upsertVideo` are called by review route, `reconcilePlaylistMembership`, `bulkUpdateVideoFields`, pipeline, backfill, `claimVideoSlot`. Audit **all** suites asserting exact video JSON, not just local-store snapshots.
- **M4 — spec §8.1 "no videos yet" empty state has no task.** Add render + test to T15's CloudApp wiring.

## Low
- **L1** cloud `/api/videos` must return `{videos, playlistUrl, playlistTitle}` (same shape as local `videos/route.ts:115`) or the CloudApp header title blanks.
- **L2** T13 should assert the sidebar nav href `/?playlist=<uuid>` (URL-contract row).
- **L3** T1/T5/T7 test steps should note `process.env.STORAGE_BACKEND='supabase'` (`beforeAll`) + `signInAs()` so a subagent doesn't write a cloud test that never hits the cloud path.
- **L4** local `updateVideoAnnotations` (T7) is dead in 2a (local review keeps `updateVideoFields`; local archive keeps `archiveVideo` file-move) — interface-shape only. Acceptable; note it.
- **L5** redundant UUID round-trip (route resolves UUID→key, store `requirePlaylistId` resolves key→UUID) — owner-safe under session RLS, matches merge precedent; harmless.

**Sync note:** empty-payload annotation write still bumps whole-record `updated_at` (no-op advances the clock) — intended per I3.
