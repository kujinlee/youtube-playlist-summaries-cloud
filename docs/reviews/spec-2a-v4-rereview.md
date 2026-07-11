# Round-4 Spot Re-Review — Stage 2a spec v4 (CONVERGENCE)

**Date:** 2026-07-10 · **Target:** spec v4 (`1b1ebb2`) · **Reviewers:** Codex (gpt-5.5) + Claude opus · **Scope:** the `update_video_annotations` RPC security model only (I1/I2/I3)

## Verification (both passes agree)
- **I1 — FIXED.** `update_video_annotations(p_playlist_id uuid, p_video_id text, p_set jsonb, p_clear text[])` pinned `SECURITY INVOKER SET search_path = public`; owner from `auth.uid()` (no client `p_owner`); guard `owner_id = auth.uid() and playlist_id = p_playlist_id and video_id = p_video_id`. Matches all four `0007` write RPCs (`security invoker set search_path=public`, `0007:22,53,82,103`); `videos` RLS (`0002:6` `owner_id = auth.uid()`) filters an INVOKER UPDATE → a wrong/foreign `p_playlist_id` yields **0 rows, never another owner's row** (RLS + explicit predicate, belt-and-suspenders). Strictly safer than precedent (drops the service-role pre-check in favor of `row_count=0→404`, correct because annotation writes are session-client-only per §7.3).
- **I2 — FIXED.** `p_set`/`p_clear` sliced in SQL to `{personalScore, personalNote, archived}` — even a route passing extra keys can't mutate non-annotation `data`. Exact SQL deferred to plan; the security invariant is pinned.
- **I3 — FIXED.** "Always issue the UPDATE even if the allowlist empties the payload" → existing row + no-op still matches WHERE → `row_count=1`; missing/foreign → 0 → 404. Correct Postgres row-count semantics.

## Consistency (no new contradiction)
- §7.3 session-client-only holds: the key→UUID hop uses `requirePlaylistId` on the **session** client (RLS-scoped; `supabase-metadata-store.ts:176-190`) — the "never `playlist_key`" rule (`resolve.ts:66`) targets *service-role* workers, not the session path.
- §12 cross-owner denial doubly satisfied: route `resolveOwnedPlaylistKey`→null→404 before the RPC, and RLS+owner-guard→0 rows→404 at the RPC.
- §13 `SECURITY DEFINER`-rejection rationale consistent with the INVOKER choice.

## Findings
- **New Blocking: none. New High: none. New Medium: none.**
- **Low (fixed in v4):** a `0007` line-number citation was off by ~4 (`26,56,85,107` → `22,53,82,103`); corrected.

## Convergence verdict
**CONVERGED.** Both passes return **0 new Blocking / 0 new High** this round — the §8 diminishing-returns stop condition is met. Trajectory: R1 (6 Blocking + 10 High) → R2 (1 High, N1) → R3 (1 High, I1) → **R4 (0/0)**. All findings across all rounds are codebase-verified and genuinely fixed. Spec is user-approved and ready for `writing-plans` (Phase 2).
