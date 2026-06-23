# Adversarial Spec Review — playlist-index-current-position

**NOTE: Codex at usage limit (until Jul 18 2026); Claude (opus) adversarial review per docs/plugins.md fallback.**

Verdict: **needs-rework** → fix confirmed correct & low-risk; all High/Medium applied (spec-completeness + test-plan tightening, no architectural change).

## Applied

- **H1 — the write-once comment now lies.** `pipeline.ts:385-386` says playlistIndex is a "stable ID … never updated"; the flip invalidates that for playlistIndex. → Spec adds an explicit task to update that comment, separating `playlistIndex` (now re-derived each sync) from the genuinely write-once `videoPublishedAt`/`addedToPlaylistAt`.
- **H2 — returned-from-removal path untested (the strongest case for the flip).** A removed (archived, stale index) video that REAPPEARS in `metas` is skipped in the main loop (alreadyIndexed) but re-stamped by the post-loop pass → with the flip it gets its current position + reconcile un-archives it. → Added test case: removed+stale video reappears at a new position → `playlistIndex`=new pos, `archived:false`, `removedFromPlaylist:false`.
- **M1 — mocking boundary insufficient.** The re-stamp pass reads `readIndex(outputFolder)`, so seeding a stale `playlistIndex` requires mocking `index-store` (readIndex/writeIndex/upsertVideo), not just `lib/youtube`. → Test plan corrected to mock `index-store` (matching the existing `pipeline.test.ts:369` pattern) so the seeded video is already-indexed → skipped in the loop → only the re-stamp pass corrects it (proves the right code path).
- **M2 — uniqueness vs contiguity.** Distinct in-playlist videos never collide (each `idx` distinct). A same-id duplicate keeps its last occurrence (unique value) but leaves a GAP in 1..N. → Softened spec wording to "unique, though not necessarily contiguous when a video appears twice in the playlist."
- **M3 — archived-but-still-in-playlist re-numbered.** The re-stamp maps over ALL videos incl. archived; a manually-archived video still in the playlist is in `positionMap` → gets re-numbered each sync (correct, it has a real position). → Added test case + clarified the out-of-scope line to distinguish "removed from playlist" (keeps stale index, hidden) from "archived but still in playlist" (gets current position).

## Added test cases
returned-from-removal (un-archive + reposition); archived-but-in-playlist (re-numbered); empty playlist (`metas=[]` → no crash, all kept via `?? v.playlistIndex`, reconcile archives).

## Verified-correct (reviewer, prompt items)
Flip uniqueness ✓ (distinct ids → distinct idx); removed/archived hidden by default (`app/page.tsx:398` filters `!v.archived`) so visible rows stay uniquely numbered ✓; new-video `playlistPos=i+1` and `positionMap` `idx+1` share the same `metas` basis (consistent) ✓; zero-new-video sync still reaches the re-stamp pass (`pipeline.test.ts:369` proves it) ✓; **no consumer keys identity/filenames/dedup on playlistIndex** — only sort (`route.ts`) + display (`VideoList.tsx`), both read-only; filenames/dedup/links key on `video.id` ✓. LOW-3 (sort `?? 0` puts undefined-index videos first under Show Archive) is pre-existing, not introduced.
