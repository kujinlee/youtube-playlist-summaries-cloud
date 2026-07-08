# Stage 1E-b Whole-Branch — Re-Review Round 2 (of the fix `51a5d8a`) + Round-3 fixes

**Target:** fix diff `3fb577c..51a5d8a` (the 8 whole-branch fixes). **Date:** 2026-07-07.
**Reviewers:** Codex (`gpt-5.5`, session `019f4079…`) + Claude Opus — independent.

## Round-2 verdicts (they DISAGREED — dual review earned its cost)
- **Codex: revise-again.** Confirmed fixes 4/5/6 (worker-crash, reserve-NULL, version-drift) genuinely fixed. But NEW findings: (B1) `persist_summary` still clobbers stale non-summary fields — the archived/removedFromPlaylist-only preservation left `playlistIndex`/`videoPublishedAt`/`title`/etc. exposed to the broad `v.data || (p_video - 'artifacts')` merge; (B2) stale unfenced write still corrupting *because of* B1; (H1) monotonic status not key-scoped (a new key inherits `promoted` → row claims a promoted artifact for an un-promoted blob); (H2) rollback delete unguarded (a concurrent worker's promoted row could be deleted).
- **Claude Opus: CONVERGED.** Argued archived+removedFromPlaylist is the *entire* concurrent-write surface (claimed `reconcile_membership` writes only those two to `data`; position is a column), so B1 is unreachable. Verified fixes 1-8 genuinely fixed; only a Minor (transient-then-permanent orphan → already deferred to 1H).

## Adjudication (controller) — Codex is right on B1; both cheap hardenings applied
Verified the concurrent-writer surface directly: `videos.data` is written not only by `reconcile_membership` (archived/removedFromPlaylist) but also by the GENERAL merges `merge_video_data` / `merge_video_data_bulk` (0007) and `upsertVideo` / `updateVideoFields` — which write arbitrary fields. So Opus's "only two fields" premise is too narrow and **Codex B1 is a real latent corruption**. Rather than enumerate every concurrent writer, adopt the robust design Codex recommended: **persist_summary writes ONLY summary-owned fields and preserves everything else** — making the disagreement moot.

## Round-3 fixes (commit below)
- **persist_summary rewritten to a whitelist merge** (`0009`): `data = (p_video - 'artifacts')` [payload defaults for a first-time bare row] `|| (v.data - 'artifacts' - {summary-owned keys})` [existing NON-summary fields win back — archived, membership, playlistIndex, title, timestamps, dig artifacts, personal notes are never reverted by a stale payload] `|| summaryMd-coalesce || artifacts-merge`. Summary-owned keys = `{language, ratings, overallScore, summaryMd, processedAt, videoType, audience, tags, tldr, takeaways, docVersion}`. Fully resolves B1 and makes B2's residual stale write non-corrupting (only summary fields ever touched).
- **Monotonic status is now KEY-SCOPED** (H1): preserve `promoted` against a `committed` write only when the artifact key is unchanged; a different key is a genuinely new artifact allowed through as `committed`.
- **Rollback delete GUARDED** (H2): the `PermanentTranscriptError` cleanup now deletes only a row that is still the bare reservation (`.is('data->>summaryMd', null)`), so a concurrent worker's written/promoted row is never deleted.
- New tests: (1) ALL concurrent non-summary state (playlistIndex reorder + `digDeeperMd`) preserved while a summary-owned field (ratings) updates; (2) key-scoped monotonic — a new key in `committed` is NOT held at `promoted`. Existing archived-preservation + same-key monotonic tests still pass.
- **Verified:** full guard GREEN — integration 116 (+2), unit 1588, tsc 0, confinement OK, `db reset` clean; all 24 worker-persistence + summary-handler tests pass.

## Convergence status
Round 2 found NEW Blocking/High → per the iterate rule, **another round is mandatory**. Round-3 re-review (dual) dispatched to verify these fixes are genuine and introduce no new defect (esp. the substantially-rewritten whitelist merge). See `-v3-rereview.md`.
