<!-- codex-review: model=gpt-5.5 -->

**Blocking**
None found.

**High**
`components/cloud/PlaylistSidebar.tsx:78`, `components/cloud/PlaylistSidebar.tsx:81`, `components/cloud/PlaylistSidebar.tsx:134`: stale playlist results can still win because the original `[userId]` effect and new `[refreshKey]` effect have independent cancellation flags.

Concrete ordering:

1. Sidebar mounts and `[userId]` effect starts `listPlaylists()` returning old snapshot `[]`, but it is slow.
2. User clicks `+ New playlist`; the button is rendered even while playlists are loading.
3. Ingest succeeds; `CloudAppBody` bumps `sidebarRefreshKey` at `components/cloud/CloudApp.tsx:87`.
4. Refresh effect runs and `listPlaylists()` returns fresh `[Business]`; line 139 sets that list.
5. Original mount request finally resolves; its own `cancelled` is still `false`, so line 81 overwrites state with `[]`.

Two rapid ingests are better: the `[refreshKey]` cleanup cancels the older refresh when the key increments. The cross-effect race is the real hole.

**Medium**
`components/cloud/PlaylistSidebar.tsx:86`, `components/cloud/PlaylistSidebar.tsx:134`, `lib/job-queue/producer.ts:91`: the refresh path can surface a newly ingested null-title playlist as `Untitled playlist` without invoking the existing title backfill.

The ingest producer explicitly leaves the row untitled when title fetch misses or throws, expecting the backfill route to retry later. But the only automatic backfill check is inside the mount `[userId]` effect. Since the new refresh effect deliberately avoids that path, a fresh null-title playlist becomes visible but unrepaired. If `sessionStorage['backfilledTitles:<userId>']` is already set, even a same-session reload will skip repair. If it is not set, a hard reload can still fix it, so the “nothing until next session” claim is too absolute, but the user-visible defect is real.

**Low**
`tests/components/cloud-app-ingest.test.tsx:52`: the new positive test covers the ordinary loaded-sidebar case, but it cannot catch the stale-overwrite race because line 60 waits for the initial empty list to render before ingest starts. That removes the only interleaving where the old mount request can overwrite the refresh result.

`tests/components/cloud-app-ingest.test.tsx:65`: the “not a poll” test does not constrain polling. It only proves a manual rerender with a changed mocked search param does not call `listPlaylists` again. A wrong implementation that refetches on ingest and also polls every 30 seconds would pass under this test because no timers are advanced. The `waitFor(() => expect(push).not.toHaveBeenCalled())` at line 72 is also vacuous.

`components/cloud/PlaylistSidebar.tsx:54`, `components/cloud/PlaylistSidebar.tsx:135`: the `refreshKey = 0` default makes existing omitted-prop callers safe. I found no current caller passing an initial non-zero value. But the component contract allows it, and that would cause duplicate initial fetches: the mount effect and refresh effect both run on first render.

`docs/backlog.md:45`, `docs/roadmap-to-launch.md:321`: the docs overstate the correction. The backlog says severity “stays 🟠”, while the roadmap says the filed severity was wrong. Also, “both filed causes were wrong” is too broad if the original “caching” theory is read as client-side stale state; the code disproves server read-path/RLS/null-title filtering, not every form of caching/staleness.

**Coverage Note**
The fix intentionally covers only in-tab ingest success. It still does not refresh for another tab, background ingest completion, or later title backfill. That is a reasonable narrow fix only if the UI/docs keep the claim narrow; it is not a general freshness model.

Verdict: NOT CONVERGED.
