# §8 Dual Review — Stage 2a Task 7 (update_video_annotations RPC + review cloud branch)

**Date:** 2026-07-11 · **Diff:** `de34502..9ed2a4a` · **§8 money/RLS task** · Convergence: round 1, 0 new Blocking/High both passes.

## Security invariants — ALL HOLD (both passes, traced against live code)
- **SECURITY INVOKER SET search_path=public** (`0016:14`), never DEFINER. Forced RLS on `videos` (`0001:41`) + `owner_id=auth.uid()` policy (`0002:6`) → foreign `p_playlist_id` yields 0 rows, never a cross-owner update. Double-protected (RLS + explicit WHERE).
- **Owner guard** `where playlist_id=p_playlist_id and video_id=p_video_id and owner_id=auth.uid()` (`0016:22`); **no `p_owner`** in signature `(uuid,text,jsonb,text[])`; store sends only playlist/video/set/clear (`supabase-metadata-store.ts:222`). Un-spoofable.
- **In-SQL key allowlist** `{personalScore,personalNote,archived}` on BOTH `p_set` (`jsonb_object_keys` + `k=any(allow)`, `0016:16-18`) and `p_clear` (`where c=any(allow)`, `0016:21`). Claude traced every bypass: nested-key injection (top-level shallow merge only), `data||v_set` order, case-sensitivity → **fail-closed both directions**. `summaryMd`/`docVersion`/`artifacts` cannot be set or cleared.
- **`revoke all from public` + `grant execute to authenticated`** with exact signature (`0016:23-24`) — anon cannot execute; stricter than `merge_video_data` (no `service_role`).
- **`merge_video_data` UNCHANGED** (`0007` not in diff); test (f) proves `summaryHtml:null` still stores null (set-null).
- **row_count/404:** UPDATE always issued → row_count = existence-under-ownership; missing/foreign → 0 → 404; no-op existing → 1 (no false 404). Store maps `>0`→found.
- **`assertVideoId` dropped from serveCloud — safe:** id flows only as parameterized `p_video_id` RPC arg; never a path/SQL string; bad id → no WHERE match → 404. Matches T5/T6 precedent.
- **Route flow:** getUser 401 → UUID_RE 400 pre-DB → outputFolder 400 → validateBody bounds 400 → resolveOwnedPlaylistKey 404 → set/clear mapping (null score/`""` note → clear) → found:false 404. Local branch behavior-preserved (validateBody extraction same checks/order/messages; assertVideoId retained local-only).
- **Cross-owner tests genuine:** RPC test — B signs in, calls with A's REAL playlist UUID → `data===0` + A's row re-read UNCHANGED; route test → 404 + A unmodified. Allowlist test — `summaryMd` unchanged after a forbidden `p_set`. `signInAs`+`STORAGE_BACKEND='supabase'`.

## Findings (no Critical/Important/Blocking/High)
- **Low (Codex, deferred → whole-branch): value-domain validation.** The RPC allowlists KEYS not VALUE DOMAINS, so a direct `authenticated` caller (bypassing the route) could write out-of-range values (`personalScore:999`, note >500 chars, non-boolean `archived`) to **their own** row. NOT a tenant/RLS break; consistent with the codebase posture (route validates; `merge_video_data` also doesn't re-validate value domains at the DB); out of converged spec/plan scope. Optional hardening: validate value domains in the RPC.
- **Minor (Claude, cosmetic): ** M1 redundant UUID→key→UUID round-trip (RLS-safe, matches store contract); M2 allowlist test asserts `not.toBe('hacked.md')` (would also pass if deleted — RPC can't delete it anyway); M3 `archived` writable in the RPC allowlist but route doesn't send it (deliberate headroom, own-row only).

**Disposition:** §8 CONVERGED round 1 — 0 new Blocking/High both passes; security model sound and proven by genuine real-Supabase cross-owner + allowlist tests. Task 7 complete. Deferred: value-domain Low + cosmetic Minors → whole-branch. Impl `9ed2a4a`: tsc 0, npm test 1817, integration 301/303, new files 20/20.
