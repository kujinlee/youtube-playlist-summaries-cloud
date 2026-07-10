# Claude Task Review — 1F-b Task 6 (getShareServeContext, confused-deputy guard)

**Reviewer:** Claude (opus) · **Date:** 2026-07-10 · Commit `f835cac`.

## (A) Spec compliance: ✅ PASS
- **D15/B19b confused-deputy:** playlist resolved by global `(id, owner_id)` + re-assert (`serve.ts:27-31`); video by `(playlist_id, video_id, owner_id)` + re-assert (`:33-37`); never uses `readIndex`/`playlist_key` for resolution (`playlist_key` only read out of the already-owner-scoped row). Mirrors `getWorkerStorageBundle`.
- **D11 deny-before-read/coarse:** token fetched first; missing/revoked/expired → identical `{status:'denied'}` before any playlist/video read; zero blob reads (Task 7's surface).
- **Promoted gate + mdKey:** `status==='promoted'` required; `mdKey = artifacts.summaryMd.key ?? data.summaryMd`; absent → denied.
- **Read-only/no money:** three `.select().maybeSingle()` only; zero `.rpc/.insert/.update/.delete` — verified.
- **Error handling:** every DB error throws (never silently allow/deny).

## (B) Code quality: needs-changes (1 Important, test-only)
### Important — confused-deputy guard (B19b) has ZERO test coverage, and it IS seedable
The 5 tests cover live/expired/revoked/unknown/unpromoted but NONE forces a cross-owner token — the scenario D15 exists for (spec §7 explicitly requires it). `share_tokens` has no FK to playlists/videos and `mintDirect` raw-inserts, so a cross-owner token is directly insertable. This is the only test that would fail if the `.eq('owner_id')` filter were deleted → the guard is currently correct-by-construction but entirely unproven. **Fixed** (follow-up: cross-owner test added, load-bearing).
### Minor
- **Client-clock expiry** vs spec §4.3's server-side `expires_at > now()` — acceptable (matches plan), noted. (Codex additionally caught a NaN-fail-open here → hardened to fail-closed in the fix.)
- **Dead JS re-asserts** (`:31`,`:37`) are unreachable given the `.eq('owner_id')` filter — harmless belt-and-suspenders; reinforces that the real guard is the query filter, so the test must target it.

## Disposition
Spec ✅; code correct and read-only. Held for the cross-owner confused-deputy test (B19b, spec §7) + expiry fail-closed hardening + before-read test strengthening (Codex Mediums) — all in a follow-up commit. Codex concurred: 0 Blocking/High, isolation holds, same test gaps (ranked Medium/Low).
