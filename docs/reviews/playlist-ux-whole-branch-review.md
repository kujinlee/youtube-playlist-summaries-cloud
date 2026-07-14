# Whole-Branch Review — feat/playlist-sidebar-ux (merge gate)

**Branch:** `feat/playlist-sidebar-ux` · **merge-base:** master @ `1118898` · **reviewed HEAD:** `7d1ca1f` (+ merge-gate fix)
**Date:** 2026-07-14
**Scope:** 12 feature commits (T1–T10 + 2 per-task review-fix commits), 48 files, +3827/−41.

Two cloud-only features:
- **A — BUG-6 playlist naming:** `fetchPlaylistTitleOrNull` → forward-persist at ingest → `setPlaylistTitleIfNull` (conditional) → `POST /api/playlists/backfill-titles` → sidebar auto-backfill once/session/user.
- **B — full hard-delete a playlist:** migration `0019` (composite cascade FK on `share_tokens` + `request_cancel_playlist_jobs` SECURITY DEFINER RPC) → `BlobStore.deletePrefix` (recursive) → `deletePlaylist` + `requestCancelPlaylist` → `DELETE /api/playlists/[id]` → sidebar trash button + `DeletePlaylistDialog`.

## Process trail
- Spec: dual adversarial review to convergence (2 rounds, 0 Blocking/0 High) — `docs/reviews/playlist-ux-spec-claude-review.md` + `scratchpad/codex-spec-*`.
- Plan: dual review to convergence (2 rounds; round 1 caught 3 Blocking that would have failed `tsc`/skipped integration tests) — `docs/reviews/playlist-ux-plan-claude-review.md`.
- Per-task: coordinator review for low-risk tasks (pure fn / best-effort / owner-scoped store methods with passing isolation tests); **full dual adversarial review** for the risk-bearing tasks — T6 (migration + SECURITY DEFINER RPC) and T9 (irreversible + isolation-critical DELETE route). Both converged after one fix round each.

## Whole-branch dual review (this gate)

### Codex (gpt-5.5): 0 Blocking, 1 High, 1 Medium, 1 Low
- Confirmed: delete-path coherence (blob prefix matches every write site incl. nested `dig/**`), no tenant-isolation break, migration 0019 coherent, interfaces compile.
- **High — backfill starvation:** `slice(0,200)` re-selects the same unfillable prefix every session; fillable rows past position 200 could be permanently starved. → **FIXED** (see Resolution).
- Medium — cloud delete E2E skip-gated (pre-existing harness gap). → tracked follow-up.
- Low — backfill unsupported→404 (vs delete's 501). → **FIXED**.

### Claude (opus): MERGEABLE — 0 Blocking, 0 High
- Independently traced both features end-to-end: delete blob-cleanup prefix provably matches every write path (summary/PDF/HTML/model/dig-nested/`_staging`); BUG-6 converges with no stuck loop; migration 0019 safe (composite FK backed by `unique(id,owner_id)`; `create_share_token` guarantees FK-satisfying inserts; profile-delete dual cascade paths deduped by Postgres); tenant isolation maintained (session-client only; owner-guarded RPC); feature interactions degrade to 0-row no-ops; all interface widenings have real + local impls, tsc 0.
- Rated the backfill unfillable-row case "bounded and harmless" (not a blocker).
- Lows: orphan-adoption-on-same-key-re-ingest corollary; backfill 404→501; backfill ref not reset on in-place account switch; skip-gated E2E.

## Reviewer split + Resolution
The two reviewers split on ONE finding — the backfill starvation: **Codex High (not mergeable)** vs **Claude non-blocking**. Assessment: Codex is mechanically correct that a fixed `slice(0,200)` starves fillable rows past position 200 behind a ≥200 permanently-unfillable prefix; Claude is correct that this is practically unreachable (needs >200 null-title playlists, 200+ permanently unfillable). Rather than ship a disputed High, it was **fixed**:

**Merge-gate fix commit** (`30caf2e`):
1. **Backfill processes ALL of the owner's null-title rows per call** (the once/session + per-user sidebar guard is the real bound); `BACKFILL_SANITY_MAX = 1000` kept only as a defensive abuse ceiling with a `console.warn`. Eliminates the fixed-prefix starvation for every realistic/near-pathological backlog. Regression test added (behavior 6c): several early unfillable rows + one later fillable → the later row is filled — the exact scenario Codex requested.
2. **Backfill unsupported backend → 501** (was 404), matching the delete route (both agreed Low).
3. **`backfillFiredRef` reset at the start of the `[userId]` effect** so an in-place account switch (A→B, no remount) gives B its own one-shot; verified it does not reintroduce the within-session refetch loop (behavior 9 test).

Post-fix: full unit suite green, `npm run test:integration -- backfill-titles` 6/6, `tsc --noEmit` clean.

## Verdict: MERGEABLE
No unresolved Blocking/High. The disputed High is fixed with a direct regression test; both reviewers' substantive coherence/isolation/migration checks passed.

## Tracked post-merge follow-ups (non-blocking)
1. **Post-delete deferred blob re-sweep** (or UUID-scoped blob namespace) to close the orphan-adoption-on-same-key-re-ingest corollary (spec §D5 already accepts invisible orphans; the residual is a straggler a later same-URL re-ingest could serve via an idempotent `exists()` short-circuit). Precise worker-race + re-ingest required.
2. **Stand up the cloud Playwright harness** (`STORAGE_BACKEND=supabase` project/webServer) and un-skip `tests/e2e/playlist-delete.spec.ts` (project-wide gap; delete is covered by real-Supabase integration tests + 25 component tests).
3. Minor: a leftover local `next dev` on :3001 blocks the Playwright webServer (local-env only).

## Merge
Merge is a **human gate**. The branch is clean to authorize: push `feat/playlist-sidebar-ux` → PR → merge via `superpowers:finishing-a-development-branch` (use `--repo kujinlee/youtube-playlist-summaries-cloud`).
