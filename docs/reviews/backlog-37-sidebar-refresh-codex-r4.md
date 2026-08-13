<!-- codex-review: model=gpt-5.5 -->

**Blocking**
None found.

**High**
[components/cloud/PlaylistSidebar.tsx](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/components/cloud/PlaylistSidebar.tsx:117): `setError(null)` can erase an error that is still accurate.

Concrete ordering:

1. Mount load starts as seq 1 and reads old `[]`, then stalls.
2. Ingest succeeds; refresh effect starts seq 2.
3. Seq 2 fails; refresh catch sets `Could not refresh...` at [line 234](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/components/cloud/PlaylistSidebar.tsx:234).
4. Seq 1 resolves after that. Since `appliedSeqRef.current` is still `0`, [line 112](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/components/cloud/PlaylistSidebar.tsx:112) allows it to apply.
5. [Line 117](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/components/cloud/PlaylistSidebar.tsx:117) clears the refresh-failed banner.

Result: after the user just created a playlist, the sidebar can show the stale pre-ingest list with no warning. Same shape with two rapid ingests: refresh 3 fails, refresh 2 later applies a list missing the second playlist and clears the banner. This is exactly case (c)/(e), and answers the explicit sub-question: yes, the new success clear can erase an error that is still true of the currently displayed list.

[components/cloud/PlaylistSidebar.tsx](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/components/cloud/PlaylistSidebar.tsx:240): the refresh effect is not cancelled on `userId` changes.

Concrete ordering:

1. User A has applied list seq 1.
2. A ingests; refresh effect starts seq 2 at [line 202](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/components/cloud/PlaylistSidebar.tsx:202).
3. Same mounted sidebar switches to user B. The `[userId]` effect cleans up and starts B load seq 3, but the `[refreshKey]` effect does not clean up because its deps are only `[refreshKey]`.
4. A’s refresh request resolves before B’s load applies.
5. `isCancelled()` is still false, `seq 2 > appliedSeq 1`, so [lines 112-114](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/components/cloud/PlaylistSidebar.tsx:112) render A’s playlists under B.

Round 3 fixed this for the mount effect by injecting cancellation, but the refresh effect’s cancellation lifetime is still scoped to `refreshKey`, not to the account whose data it requested.

**Medium**
None found beyond the High concurrency defects above.

**Low**
[tests/components/cloud-app-ingest.test.tsx](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/tests/components/cloud-app-ingest.test.tsx:145): the tests still do not cover “newer refresh fails, older stale success later clears the banner.” The existing test proves the older result can render, but not that the refresh failure remains visible afterward.

[tests/components/cloud-app-ingest.test.tsx](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/tests/components/cloud-app-ingest.test.tsx:294): the account-switch test covers a cancelled mount load, but not a cancelled refresh load. That leaves the second High unpinned.

**Question 1**
No, concurrency is still not correct. I found no stale-success overwrite after a newer successful apply, and stale rejections are now suppressed correctly. But a newer failed refresh followed by an older success can silently clear the accurate out-of-date banner, and an in-flight refresh can survive an account switch.

**Question 2**
No, this design is not worth its current complexity as implemented.

I would ship option 1 only after extracting it into a `usePlaylistList({ userId, refreshKey })` hook and fixing the error/list state machine there. The component should not carry this much concurrency policy inline. The hook should make “data freshness” and “refresh failure still relevant” explicit and testable.

I would not ship remount-as-refetch as the main fix. It does remove the ingest refresh effect and old-instance stale writes, and the cost is a visible loading flicker plus resetting instance refs. More importantly, it weakens the null-title repair story: a remount reuses the mount backfill path, which is sessionStorage-gated, so a newly ingested null-title playlist can still stay untitled if the sign-in sweep already ran. A stale-write hazard mostly disappears for the old instance, but in-instance delete/backfill/account-switch races still need discipline unless the key also includes `userId`.

A simpler viable alternative is a reducer-backed hook with a single request API: `load({ reason: 'initial' | 'ingest' | 'delete' | 'backfill', userIdAtStart })`, one monotonically increasing request id, and an error record tagged with the request/reason it describes. Strongest argument against the hook/current-family approach: four rounds have shown this state machine is easy to get subtly wrong, so it must be isolated and tested with the exact adversarial timelines above.

NOT CONVERGED
