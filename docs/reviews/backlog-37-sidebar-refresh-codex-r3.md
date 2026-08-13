<!-- codex-review: model=gpt-5.5 -->

**Blocking**
None found.

**High**
[components/cloud/PlaylistSidebar.tsx](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/components/cloud/PlaylistSidebar.tsx:100): `loadPlaylists()` now applies state before any effect-level `cancelled` flag is checked. The comments say sequence answers “superseded” and cancellation answers “tore down”, but cancellation no longer protects the state write at lines 104-106.

Concrete account-switch ordering:

1. User A load starts as seq 1.
2. Same mounted instance switches to user B; A effect cleanup sets `cancelled = true`; B load starts as seq 2.
3. A load resolves before B applies anything.
4. `seq 1 > appliedSeqRef.current`, so A’s playlists render under B’s sidebar.

That is not an `appliedSeqRef` monotonic-reset problem; new B loads still get larger sequence numbers. It is the opposite: an old cancelled load is allowed to apply because the cancellation check at [line 126](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/components/cloud/PlaylistSidebar.tsx:126) runs after `setPlaylists()` has already happened.

[components/cloud/PlaylistSidebar.tsx](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/components/cloud/PlaylistSidebar.tsx:211): latest post-mutation refetch failures are swallowed, and the two-counter rule then allows an older pre-mutation result to apply with no indication the fresh load failed.

Concrete ingest ordering:

1. Mount load seq 1 starts before ingest and captures old `[]`.
2. Ingest succeeds; refresh load seq 2 starts.
3. Seq 2 rejects. The refresh effect catches and suppresses it at lines 211-214.
4. Seq 1 resolves after that; because no newer load applied, line 104 allows it and lines 105-106 render the old `[]`.
5. User is left with the stale sidebar and no error.

Same shape with two rapid ingests: refresh 1 starts after playlist A, refresh 2 starts after playlist B, refresh 2 fails silently, refresh 1 later applies a list missing B. This is the “silently keeps stale data” failure mode the project explicitly cares about.

**Medium**
[components/cloud/PlaylistSidebar.tsx](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/components/cloud/PlaylistSidebar.tsx:106): successful loads never clear a previous `error`. If an initial load rejects at line 153, a later ingest-triggered refresh can successfully set `playlists`, but [line 246](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/components/cloud/PlaylistSidebar.tsx:246) keeps rendering the old error and the `!error` guards hide the fresh list. `PlaylistLibrary` clears error on success; this helper should probably do the same.

**Low**
Tests: I count seven current `#37` tests, not six.

- [line 56](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/tests/components/cloud-app-ingest.test.tsx:56): an implementation that refetches on every same-route navigation, not specifically ingest success, still passes.
- [line 72](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/tests/components/cloud-app-ingest.test.tsx:72): a focus/visibility listener or 65-minute poll still passes.
- [line 100](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/tests/components/cloud-app-ingest.test.tsx:100): proves stale success cannot overwrite newer success, but not the newer-failed/older-stale case above.
- [line 122](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/tests/components/cloud-app-ingest.test.tsx:122): it invokes the stale rejection, but a wrong implementation that suppresses all list errors also passes.
- [line 145](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/tests/components/cloud-app-ingest.test.tsx:145): it proves the older `CS146S` result rendered, but not that silently falling back to that stale result is acceptable after a failed post-ingest refresh.
- [line 168](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/tests/components/cloud-app-ingest.test.tsx:168): an implementation that backfills every null-title refresh without the intended bounds still passes.
- [line 188](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/tests/components/cloud-app-ingest.test.tsx:188): catches the failing-backfill display path, but not duplicate concurrent backfills.

**Nothing Found**
`initialRefreshKeyRef` is correct for the current caller. It imposes this contract: while the sidebar stays mounted, a real refresh signal must not revisit the first-render value. [CloudApp.tsx](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/components/cloud/CloudApp.tsx:82) starts at `0` and only increments, so it honors that. A parent remount is also fine because the mount effect owns the new initial load.

I do not see `appliedSeqRef` “never resets” causing a needed later load to be rejected; later starts get larger seqs. The backfill effects can duplicate `backfillPlaylistTitles()` if mount repair and ingest repair overlap, but I do not see a successful post-backfill reload being overwritten by a pre-backfill list once a newer result has applied.

Tests run: `npm test -- --runTestsByPath tests/components/cloud-app-ingest.test.tsx tests/components/cloud/PlaylistSidebar.backfill.test.tsx tests/components/cloud/PlaylistSidebar.delete.test.tsx --runInBand` passed.

NOT CONVERGED
