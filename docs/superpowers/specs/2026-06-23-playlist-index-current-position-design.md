# Playlist Index = Current Playlist Position

**Date:** 2026-06-23
**Branch:** `fix/playlist-index-current-position`
**Status:** Design — pending adversarial review gate.

## Problem

The `#` column (`playlistIndex`, label "Playlist position") is not unique: across 269 videos there are only 198 distinct values — **12 videos at `#1`**, 8 at `#2`, 8 at `#3`, etc.

**Root cause** (`lib/pipeline.ts:389`): `playlistIndex` is **write-once**:
```ts
playlistIndex: v.playlistIndex ?? positionMap.get(v.id),
```
`metas = await fetchPlaylistVideos(...)` fetches the **full** playlist every sync and `positionMap` maps each video id → its current absolute position (`idx + 1`). But the `??` keeps any already-stored value, so a video's `playlistIndex` is frozen at first ingest. This playlist **prepends** new videos (newest-first), so every sync the newest video takes position `#1` and all existing videos shift down — yet their stored `playlistIndex` never updates. Twelve syncs that each added a top video → twelve videos frozen at `#1`. The code comment calls `playlistIndex` a "stable ID stamped at first ingest," but a playlist position is **not** stable under reordering — that is the incorrect assumption.

## Decision

`playlistIndex` should reflect the **current** playlist position, re-derived each sync for videos still in the playlist.

**Fix** — flip the precedence at `pipeline.ts:389`:
```ts
playlistIndex: positionMap.get(v.id) ?? v.playlistIndex,
```
- Videos **in** the current playlist are always in `positionMap` → they get their current absolute position. Distinct in-playlist videos never collide (each `idx` is distinct). Values are **unique, though not necessarily contiguous `1..N`**: if the same video id appears twice in the playlist, the `Map` keeps its last occurrence and the earlier slot is unassigned, leaving a gap — uniqueness for visible rows still holds.
- Videos **removed** from the playlist are not in `positionMap` → they keep their last-known `playlistIndex` (auto-archived / hidden by default; nulling could disturb sort). A removed video's stale index may coincide with an in-playlist video's position, but removed videos are hidden, so visible rows remain uniquely numbered.
- A video **manually archived but still in the playlist** (`removedFromPlaylist` false) IS in `positionMap`, so it is re-numbered to its current position each sync — correct, it still has a real playlist position.

`videoPublishedAt` and `addedToPlaylistAt` **remain write-once** (`v.x ?? map.get(id)`) — those are genuinely stable per video. New-video stamping (`pipeline.ts:342`, `playlistIndex: playlistPos`) is already correct and unchanged.

**Also update the stale comment at `pipeline.ts:385-386`** — it currently claims `playlistIndex` is a "stable ID … never updated"; after this change it must read that `playlistIndex` is re-derived from the current playlist order each sync (for in-playlist videos), while `videoPublishedAt`/`addedToPlaylistAt` remain write-once.

## Migration

No separate script. The fix re-stamps every in-playlist video from the freshly-fetched order on the **next Sync**; already-indexed videos are skipped in the processing loop (no Gemini, no transcript work), so the sync is a cheap re-numbering. After this lands, run one Sync against the corpus to correct the 269-video index.

## Components & boundaries

| Unit | Responsibility | Change |
|------|----------------|--------|
| `lib/pipeline.ts` `runIngestion` (line 389 re-stamp pass) | `playlistIndex` tracks current playlist position | Modify (one expression) |

No signature change; no other field's semantics change.

## Testing (TDD)

Unit test the re-stamp pass (the `videosWithIndex` mapping at `pipeline.ts:387-393`). **Mocking boundary:** mock `lib/youtube` (`fetchPlaylistVideos`) AND `lib/index-store` (`readIndex`/`writeIndex`/`upsertVideo`) — the re-stamp pass reads `readIndex(outputFolder)`, so the stale `playlistIndex` must be seeded through `index-store`, and the seeded video must be already-indexed so it is skipped in the main loop and corrected **only** by the re-stamp pass (the proof we're testing the right path). Follow the existing pattern at `tests/lib/pipeline.test.ts:369`.

1. **Reorder corrects stale index:** seed already-indexed video A with `playlistIndex: 1`; mock the playlist so A is now at position 5 → after sync, A's `playlistIndex === 5`.
2. **Collision resolves:** seed A=1 and B=1 (the bug state); mock playlist with A at pos 2, B at pos 1 → after sync, A=2, B=1 (distinct).
3. **Removed video keeps its index:** seed C with `playlistIndex: 3` but omit C from the mocked playlist → C's `playlistIndex` stays 3 (and C is archived via the existing reconcile).
4. **Returned-from-removal (H2):** seed D with `playlistIndex: 9`, `archived: true`, `removedFromPlaylist: true`; mock the playlist so D reappears at position 4 → after sync, D's `playlistIndex === 4`, `archived === false`, `removedFromPlaylist === false`.
5. **Archived-but-still-in-playlist (M3):** seed E with `playlistIndex: 1`, `archived: true`, `removedFromPlaylist: false`; mock playlist with E at position 6 → E's `playlistIndex === 6` (re-numbered, still archived).
6. **Stable fields untouched:** a video with stored `videoPublishedAt`/`addedToPlaylistAt` retains them (write-once preserved) even as `playlistIndex` updates.
7. **Empty playlist:** `fetchPlaylistVideos` returns `[]` → no crash; existing videos keep `playlistIndex` (fall through `?? v.playlistIndex`) and are archived by reconcile.

Full `npm test` + `npx tsc --noEmit` green before commit. Dual review per task.

## Out of scope

- Changing `videoPublishedAt` / `addedToPlaylistAt` write-once semantics.
- Re-numbering **removed-from-playlist** videos (not in `positionMap`) — they keep their last-known index and stay hidden. (Note: this differs from a *manually-archived-but-still-in-playlist* video, which IS re-numbered to its current position — see Decision.)
- Any UI/sort change (the `#` column and its sort already read `playlistIndex`; correcting the data is sufficient).
