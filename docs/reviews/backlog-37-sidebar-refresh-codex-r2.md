<!-- codex-review: model=gpt-5.5 -->

**Blocking**
None found.

**High**
[components/cloud/PlaylistSidebar.tsx](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/components/cloud/PlaylistSidebar.tsx:87): `loadPlaylists()` only sequence-guards successful results. Stale rejections still escape to the caller, so an older request can still win by setting error or redirecting after a newer request has already rendered the correct list.

Concrete interleaving:

1. Mount starts `loadPlaylists()` seq 1.
2. Ingest succeeds; refresh effect starts seq 2.
3. Seq 2 resolves fresh `[Business]`; line 91 applies it.
4. Seq 1 rejects with a transient `Error`; mount catch at lines 128-134 runs because `cancelled` is still false and sets `error`.
5. The sidebar hides the valid list behind the stale error.

If seq 1 rejects with `UnauthorizedError`, line 131 can redirect to `/login` after a newer successful refresh. The sequence guard needs to apply to failures too, not only resolved values.

[components/cloud/PlaylistSidebar.tsx](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/components/cloud/PlaylistSidebar.tsx:88): the opposite failure also exists: when two loads are in flight and the newer one rejects, the older legitimate result is permanently discarded.

Concrete interleaving:

1. Mount starts seq 1 and stalls.
2. Ingest refresh starts seq 2 and rejects.
3. Refresh catch at lines 190-193 swallows it.
4. Seq 1 resolves successfully, but line 90 returns `null` because seq 2 is still newest.
5. If this was initial load, the sidebar can stay on `Loading playlists…`; if there was an older list, it silently remains stale.

That is the “newer request failed, older request was usable” case the current sequence discipline does not handle.

**Low**
[components/cloud/PlaylistSidebar.tsx](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/components/cloud/PlaylistSidebar.tsx:162): `refreshEffectPrimedRef` is not StrictMode-safe. The existing comment at lines 63-66 correctly says refs survive React 18 StrictMode double effect invocation. That means the first StrictMode setup consumes the “first run” by setting the ref true, then the second setup sees it primed and runs the refresh body on mount anyway. In dev StrictMode this reintroduces a duplicate initial playlist fetch and can run the refresh-path null-title backfill on initial mount without the sessionStorage gate. Production behavior is likely unaffected, but the stated “skip my first run” contract is false under the project’s own StrictMode model.

[tests/components/cloud-app-ingest.test.tsx](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/tests/components/cloud-app-ingest.test.tsx:56): the four #37 tests still leave meaningful wrong implementations green:

- Line 56: a per-effect-cancelled implementation with no shared sequence still passes because the test waits for initial load before ingest.
- Line 72: the fake-timer test rejects short polling, but a 30-minute poll, focus poll, or visibility poll still passes, so it does not prove “not a poll” broadly.
- Line 97: the race test does exercise the claimed success ordering despite synchronous `createIngest`, because initial `listPlaylists()` is stalled and the post-ingest refetch supplies the link. But it does not cover stale rejection or newer-reject discard, which are now the real sequence holes.
- Line 120: the null-title test proves `backfillPlaylistTitles()` was called and that a later mock list returned `Business`; it does not prove the backfill caused the repair, was ordered before refetch, was bounded beyond one sample, or respected `userId`.

**Nothing Found**
The refresh-path backfill is bounded by `refreshKey` changes: one attempt per successful ingest-triggered refresh, and the post-backfill `loadPlaylists()` does not re-enter the effect because `refreshKey` is unchanged. If a private/deleted playlist stays null, this path does not loop.

I do not see scope creep in adding this repair to the refresh path. The branch intentionally made newly ingested rows visible; handling the known null-title state for those newly visible rows is part of making that UI state correct. The docs changes in [docs/backlog.md](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/backlog.md:45) and [docs/roadmap-to-launch.md](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/roadmap-to-launch.md:317) now read consistently.

I ran `npm test -- --runTestsByPath tests/components/cloud-app-ingest.test.tsx tests/components/cloud/PlaylistSidebar.backfill.test.tsx --runInBand`; both suites passed.

NOT CONVERGED
