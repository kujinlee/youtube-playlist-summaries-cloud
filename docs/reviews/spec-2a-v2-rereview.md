# Round-2 Dual Re-Review — Stage 2a spec v2 → v3

**Date:** 2026-07-10 · **Target:** spec v2 (`482ac20`) · **Reviewers:** Codex (gpt-5.5) + Claude opus (independent)

## Round-1 fix verification (both passes)
**All round-1 findings — 6 Blocking + 10 High + Mediums/Lows — verified GENUINELY FIXED** (not reworded), each traced to the v2 section that fixes it (middleware model §3.2; OAuth `/library`→`/` §3.2/§9; whole-record `updatedAt` via existing column+trigger §7.1; `listPlaylists` owner filter §4/§7.3; missing-video 404 + clear §4; archive Sync note §7.2; scope-reject §3.4; page.tsx boundary §3.1; quick-view gate §4; terminology §7.1; menu allowlist / +New / tests §5/§12). Full FIXED table in the round-2 agent outputs.

## New findings from the v2 fixes

### New Blocking: none.

### New High
- **N1 (Claude) — A6/A7 mechanism regresses the SHARED `merge_video_data` RPC.** v2 offered "make `merge_video_data` treat JSON-null as delete, or raise on 0 rows." But `merge_video_data` is shared by pipeline/serve callers that legitimately write JSON `null` as *set-null* (`regenerate/route.ts:71` `summaryHtml:null`; `consistency.ts`; `generate.ts`); delete-on-null or raise-on-0-rows silently changes their semantics — the "shared already-merged code" hazard. **Fix (v3):** dedicated `update_video_annotations(p_owner, p_playlist_key, p_video_id, p_set jsonb, p_clear text[])` RPC restricted to annotation keys; `merge_video_data` untouched; §12 regression test that null-writers still store null; drop the §13 "both satisfy" equivalence. *(Clear logic itself was sound — the defect was strictly the shared-RPC blast radius.)*

### New Medium
- **N2 (Claude) — page.tsx (RSC) session read can 500 on token refresh.** `createServerSupabase.setAll` writes cookies (no try/catch); Next.js forbids cookie mutation in RSC render. **Fix (v3, §3.1):** read session read-only (getUser via a page-scoped client with no-op/try-catch setAll); don't reuse the route factory.
- **N3 (Claude) — local `data.updatedAt` stamping underspecified.** If applied at `index-store.writeIndex` (whole-file rewrite) it re-stamps every video per edit, destroying the per-video newer-wins signal. **Fix (v3, §7.1):** per-video stamping inside `updateVideoFields`/`upsertVideo` only; never `writeIndex`.
- **N-Codex — `/s/*` regression wording contradiction.** §12 required anon `/s/*` "still reachable" but §2/§14 freeze its (authenticated) classification. **Fix (v3):** §12 now tests only that the `/login` `PUBLIC_EXACT` edit does not change `/s`/`/try` classification; `/s` gating explicitly out of scope.

### New Low (folded into v3)
- **N4 / Codex-M1** — `listPlaylists` select must include `created_at` (ordered-by + returned). Fixed §4 A2.
- **N5 (Claude)** — anon session satisfies the cloud `/` gate (empty library, no leak). Documented §3.2 rule 3.
- **N6 (Claude)** — the "strip client `updatedAt`" rule doesn't cover the whole-record `upsertVideo` writer (2b scope). Noted §7.1 for 2b.
- **L1 (Codex)** — local JSON tests must use matchers, not exact snapshots (dynamic `updatedAt`). Added §12.

## Convergence status
Round 2: **0 new Blocking, 1 new High (N1).** A new High means the loop continues — v3 fixes N1 (dedicated RPC) + folds N2–N6/L1. **Round 3 required** to confirm no further shared-RPC blast radius and no new Blk/High.
