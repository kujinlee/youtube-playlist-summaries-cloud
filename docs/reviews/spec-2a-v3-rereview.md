# Round-3 Dual Re-Review — Stage 2a spec v3 → v4

**Date:** 2026-07-10 · **Target:** spec v3 (`f6b15f4`) · **Reviewers:** Codex (gpt-5.5) + Claude opus · **Scope:** v2→v3 diff only

## v3 change verification (both passes)
All v3 fixes verified **FIXED**, grounded in real files:
- **N1** — `merge_video_data` genuinely left unchanged everywhere; null-writers real (`regenerate/route.ts:71`, `generate.ts:67`, `consistency.ts:33,39`); §12 regression test added. *(But the new RPC's own security model raised a fresh High — I1.)*
- **N2** — read-only RSC session correct; `createServerSupabase.setAll` (`server.ts:15-18`) writes cookies unconditionally → RSC 500; page-scoped read-only client is the right pattern.
- **N3** — per-video stamping choke points confirmed (`updateVideoFields`/`upsertVideo`); `writeIndex` (`index-store.ts:83`) whole-file rewrite correctly excluded; no leak path (`setPlaylistMeta`/`deleteVideo` need no stamp; membership/bulk route through the stamped methods).
- **N4/N5/N6/L1/`/s/*` wording** — all FIXED, consistent, no new contradiction.

## New finding from the v3 fix

### New Blocking: none.

### New High
- **I1 (Claude; Codex flagged as guidance) — `update_video_annotations` security/owner model ambiguous on an RLS write path → possible cross-tenant write.** v3's signature `(p_owner, p_playlist_key, …)` took a **client-derivable `p_owner`** and looked up by **`playlist_key`** (unique only per-owner — `resolve.ts:66-70` warns against exactly this; every `0007` write RPC instead takes `p_playlist_id uuid` + guards `owner_id = auth.uid()`, `0007:26,56,85,107`). §13 floated "`SECURITY DEFINER` if needed" — under definer (no FORCE RLS) `where owner_id = p_owner` with a spoofed `p_owner` writes another tenant's row. **Fix (v4):** pin `SECURITY INVOKER SET search_path = public`; owner derived from `auth.uid()` inside the function (drop `p_owner`); UUID-addressed (`p_playlist_id`); delete the `SECURITY DEFINER` phrasing from §13.

### Medium
- **I2 — annotation-key allowlist must be enforced in SQL, not only prose/TS.** `data = (data || p_set) - p_clear` persists any key in `p_set`. **Fix (v4):** slice `p_set`/`p_clear` to `{personalScore, personalNote, archived}` inside the function (defense-in-depth).

### Low
- **I3 — `row_count`/404 semantics under the allowlist.** Verified sound: mixed set+clear correct; clearing an absent key is a no-op (`jsonb - text[]` never errors); UPDATE matching an existing row returns `row_count=1` even when key absent/unchanged (trigger bumps `updated_at`) → no false 404; `row_count=0` only for a genuinely missing/foreign video → correct 404. **Guard (v4):** if the allowlist slice empties the payload, still issue the UPDATE so `row_count` reflects row existence, not payload emptiness.

## Convergence status
Round 3: **0 new Blocking, 1 new High (I1) on the RLS/cross-tenant write path.** Loop continues per dev-process §8 (a new High on an auth/RLS path). v4 pins the RPC security model (I1) + SQL allowlist (I2) + empty-payload UPDATE guard (I3). **Round 4 = spot re-review of just `update_video_annotations`.** Everything else genuinely fixed with no new defect — both passes agree the spec is otherwise converged.
