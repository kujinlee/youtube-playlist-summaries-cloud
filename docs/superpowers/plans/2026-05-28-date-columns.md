# Date Columns Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `Published` (YouTube publish date) and `Added` (playlist add date) as sortable ISO date columns in the video table, capturing both timestamps from the YouTube API.

**Architecture:** Dates flow from YouTube API → `VideoMeta` transport type → `Video` index type → JSON index file → API sort handler → React table. Types land first (Task 1) so every downstream task compiles. Tasks 2–6 each follow a red-green TDD cycle in isolation.

**Tech Stack:** TypeScript / Zod (types), googleapis SDK (YouTube API), Jest + @testing-library/react (tests), Next.js API route (sort), React (components)

---

## File Map

| File | Change |
|---|---|
| `types/index.ts` | Add `videoPublishedAt?`, `addedToPlaylistAt?` to `VideoMetaSchema` and `VideoSchema`; extend `SortColumn` union |
| `lib/youtube.ts` | Add `'snippet'` to `playlistItems.list` part; capture both dates per video |
| `lib/pipeline.ts` | Spread dates into new `Video` objects; add date backfill maps in post-reconcile pass |
| `app/api/videos/route.ts` | Add `videoPublishedAt` / `addedToPlaylistAt` cases to `sortVideos` with null-last logic |
| `components/VideoRow.tsx` | Two new `<td>` cells (YYYY-MM-DD or `—`) after the `audience` cell |
| `components/VideoList.tsx` | Two new entries in `COLUMNS`; update first-click sort direction for date cols |
| `tests/lib/youtube.test.ts` | New tests: dates captured from API; missing dates → `undefined` |
| `tests/lib/pipeline.test.ts` | New tests: dates stamped on new videos; backfill on already-indexed; stable on re-sync |
| `tests/api/videos.test.ts` | New tests: sort by both date cols asc/desc; nulls sort last |
| `tests/components/VideoRow.test.tsx` | New tests: renders YYYY-MM-DD; renders `—` when absent |
| `tests/components/VideoList.test.tsx` | Updated: 13 sort buttons; new date-col first-click → desc; non-date col still → asc |

---

## Task 1: Types — Add date fields and extend SortColumn

**Files:**
- Modify: `types/index.ts`

No Jest tests — TypeScript validates these at compile time. This task must land before any other task compiles.

- [ ] **Step 1: Add `videoPublishedAt` and `addedToPlaylistAt` to `VideoMetaSchema`**

In `types/index.ts`, locate `VideoMetaSchema` (line ~29) and add two optional fields after `channelTitle`:

```ts
export const VideoMetaSchema = z.object({
  videoId: z.string(),
  title: z.string(),
  youtubeUrl: z.string().url(),
  durationSeconds: z.number().int().nonnegative(),
  channelTitle: z.string().optional(),
  videoPublishedAt: z.string().datetime().optional(),
  addedToPlaylistAt: z.string().datetime().optional(),
});
export type VideoMeta = z.infer<typeof VideoMetaSchema>;
```

- [ ] **Step 2: Add `videoPublishedAt` and `addedToPlaylistAt` to `VideoSchema`**

In `types/index.ts`, locate `VideoSchema` and add two optional fields after `playlistIndex` (line ~58):

```ts
  playlistIndex: z.number().int().positive().optional(),
  videoPublishedAt: z.string().datetime().optional(),
  addedToPlaylistAt: z.string().datetime().optional(),
```

- [ ] **Step 3: Extend `SortColumn` union**

In `types/index.ts`, locate `SortColumn` (line ~132) and extend it:

```ts
export type SortColumn = 'name' | 'overall' | RatingSortColumn | 'language' | 'videoType' | 'audience' | 'playlistIndex' | 'videoPublishedAt' | 'addedToPlaylistAt';
```

- [ ] **Step 4: Verify TypeScript compiles**

```bash
npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 5: Commit**

```bash
git add types/index.ts
git commit -m "feat(types): add videoPublishedAt, addedToPlaylistAt fields and SortColumn entries"
```

---

## Task 2: YouTube API — Capture both dates in `fetchPlaylistVideos`

**Files:**
- Modify: `lib/youtube.ts`
- Test: `tests/lib/youtube.test.ts`

- [ ] **Step 1: Write failing tests**

Add three new tests to `tests/lib/youtube.test.ts` inside the existing `describe('fetchPlaylistVideos', ...)` block:

```ts
it('captures addedToPlaylistAt from playlistItems snippet.publishedAt', async () => {
  mockPlaylistItemsList.mockResolvedValue({
    data: {
      items: [{
        contentDetails: { videoId: 'abc12345678' },
        snippet: { publishedAt: '2025-01-03T09:00:00Z' },
      }],
      nextPageToken: null,
    },
  });
  mockVideosList.mockResolvedValue({
    data: {
      items: [{
        id: 'abc12345678',
        snippet: { title: 'Test Video' },
        contentDetails: { duration: 'PT5M' },
      }],
    },
  });

  const result = await fetchPlaylistVideos(
    'https://www.youtube.com/playlist?list=PLtest123',
    'fake-api-key',
  );

  expect(result[0].addedToPlaylistAt).toBe('2025-01-03T09:00:00Z');
});

it('captures videoPublishedAt from videos snippet.publishedAt', async () => {
  mockPlaylistItemsList.mockResolvedValue({
    data: {
      items: [{ contentDetails: { videoId: 'abc12345678' } }],
      nextPageToken: null,
    },
  });
  mockVideosList.mockResolvedValue({
    data: {
      items: [{
        id: 'abc12345678',
        snippet: { title: 'Test Video', publishedAt: '2024-11-12T14:30:00Z' },
        contentDetails: { duration: 'PT5M' },
      }],
    },
  });

  const result = await fetchPlaylistVideos(
    'https://www.youtube.com/playlist?list=PLtest123',
    'fake-api-key',
  );

  expect(result[0].videoPublishedAt).toBe('2024-11-12T14:30:00Z');
});

it('returns undefined for both dates when snippet fields are absent', async () => {
  mockPlaylistItemsList.mockResolvedValue({
    data: {
      items: [{ contentDetails: { videoId: 'abc12345678' } }],
      nextPageToken: null,
    },
  });
  mockVideosList.mockResolvedValue({
    data: {
      items: [{
        id: 'abc12345678',
        snippet: { title: 'Test Video' },
        contentDetails: { duration: 'PT5M' },
      }],
    },
  });

  const result = await fetchPlaylistVideos(
    'https://www.youtube.com/playlist?list=PLtest123',
    'fake-api-key',
  );

  expect(result[0].videoPublishedAt).toBeUndefined();
  expect(result[0].addedToPlaylistAt).toBeUndefined();
});
```

- [ ] **Step 2: Run tests — confirm they fail**

```bash
npx jest tests/lib/youtube.test.ts --no-coverage
```

Expected: 3 new tests FAIL (`addedToPlaylistAt` and `videoPublishedAt` are `undefined` even when mock provides them).

- [ ] **Step 3: Implement — update `fetchPlaylistVideos` in `lib/youtube.ts`**

Replace the `fetchPlaylistVideos` function body with the following (adds `'snippet'` to `playlistItems.list`, collects `addedToPlaylistAt` per video, and captures `videoPublishedAt` from `videos.list`):

```ts
export async function fetchPlaylistVideos(playlistUrl: string, apiKey: string): Promise<VideoMeta[]> {
  let playlistId: string | null;
  try {
    playlistId = new URL(playlistUrl).searchParams.get('list');
  } catch {
    throw new Error(`Invalid playlist URL: ${playlistUrl}`);
  }
  if (!playlistId) throw new Error(`No playlist ID found in URL: ${playlistUrl}`);

  const yt = google.youtube({ version: 'v3', auth: apiKey });

  const videoIds: string[] = [];
  const addedDates: Record<string, string | undefined> = {};
  let pageToken: string | undefined;
  let pageCount = 0;
  const MAX_PAGES = 100;
  do {
    if (pageCount++ >= MAX_PAGES) throw new Error(`Playlist exceeded ${MAX_PAGES} pages: ${playlistUrl}`);
    const res = await yt.playlistItems.list({
      part: ['contentDetails', 'snippet'],
      playlistId,
      maxResults: 50,
      pageToken,
    });
    for (const item of res.data.items ?? []) {
      if (item.contentDetails?.videoId) {
        videoIds.push(item.contentDetails.videoId);
        addedDates[item.contentDetails.videoId] = item.snippet?.publishedAt ?? undefined;
      }
    }
    pageToken = res.data.nextPageToken ?? undefined;
  } while (pageToken);

  const videos: VideoMeta[] = [];
  for (let i = 0; i < videoIds.length; i += 50) {
    const res = await yt.videos.list({
      part: ['snippet', 'contentDetails'],
      id: videoIds.slice(i, i + 50),
    });
    for (const item of res.data.items ?? []) {
      if (!item.id) continue;
      videos.push({
        videoId: item.id,
        title: item.snippet?.title ?? '',
        channelTitle: item.snippet?.channelTitle ?? undefined,
        youtubeUrl: `https://www.youtube.com/watch?v=${item.id}`,
        durationSeconds: parseDuration(item.contentDetails?.duration ?? ''),
        videoPublishedAt: item.snippet?.publishedAt ?? undefined,
        addedToPlaylistAt: addedDates[item.id],
      });
    }
  }
  // videos.list doesn't guarantee response order matches input — restore playlist order
  const videoMap = new Map(videos.map((v) => [v.videoId, v]));
  return videoIds.map((id) => videoMap.get(id)).filter(Boolean) as VideoMeta[];
}
```

- [ ] **Step 4: Run tests — confirm all pass**

```bash
npx jest tests/lib/youtube.test.ts --no-coverage
```

Expected: all tests PASS.

- [ ] **Step 5: Run full suite — confirm no regressions**

```bash
npm test -- --no-coverage
```

Expected: all tests PASS.

- [ ] **Step 6: Commit**

```bash
git add lib/youtube.ts tests/lib/youtube.test.ts
git commit -m "feat(youtube): capture videoPublishedAt and addedToPlaylistAt from YouTube API"
```

---

## Task 3: Pipeline — Stamp dates on new videos and backfill already-indexed

**Files:**
- Modify: `lib/pipeline.ts`
- Test: `tests/lib/pipeline.test.ts`

- [ ] **Step 1: Write failing tests**

Add the following tests to `tests/lib/pipeline.test.ts` inside the existing `describe('runIngestion', ...)` block. Use the existing `makeVideoMeta` and `makeIndexedVideo` helpers (already defined in the file):

```ts
it('stamps videoPublishedAt and addedToPlaylistAt on new videos from VideoMeta', async () => {
  const meta = {
    ...makeVideoMeta('vid1'),
    videoPublishedAt: '2024-11-12T14:30:00Z',
    addedToPlaylistAt: '2025-01-03T09:00:00Z',
  };
  mockFetchPlaylistVideos.mockResolvedValue([meta]);
  mockFetchTranscript.mockResolvedValue('transcript');
  mockGenerateSummary.mockResolvedValue(makeSummaryResponse());

  await runIngestion(PLAYLIST_URL, outputFolder, () => {});

  expect(mockUpsertVideo).toHaveBeenCalledWith(
    outputFolder,
    expect.objectContaining({
      id: 'vid1',
      videoPublishedAt: '2024-11-12T14:30:00Z',
      addedToPlaylistAt: '2025-01-03T09:00:00Z',
    }),
  );
});

it('backfills dates on already-indexed videos via reconciliation writeIndex call', async () => {
  const existingVid = makeIndexedVideo('vid1'); // no dates
  mockReadIndex.mockReturnValue({ playlistUrl: PLAYLIST_URL, outputFolder, videos: [existingVid] });

  const meta = {
    ...makeVideoMeta('vid1'),
    videoPublishedAt: '2024-11-12T14:30:00Z',
    addedToPlaylistAt: '2025-01-03T09:00:00Z',
  };
  mockFetchPlaylistVideos.mockResolvedValue([meta]);

  await runIngestion(PLAYLIST_URL, outputFolder, () => {});

  const lastWriteCall = mockWriteIndex.mock.calls[mockWriteIndex.mock.calls.length - 1];
  const writtenVideos: Video[] = lastWriteCall[1].videos;
  expect(writtenVideos).toContainEqual(
    expect.objectContaining({
      id: 'vid1',
      videoPublishedAt: '2024-11-12T14:30:00Z',
      addedToPlaylistAt: '2025-01-03T09:00:00Z',
    }),
  );
});

it('preserves existing dates for already-indexed videos on re-sync', async () => {
  const existingVid = makeIndexedVideo('vid1', {
    videoPublishedAt: '2024-11-12T14:30:00Z',
    addedToPlaylistAt: '2025-01-03T09:00:00Z',
  });
  mockReadIndex.mockReturnValue({ playlistUrl: PLAYLIST_URL, outputFolder, videos: [existingVid] });

  // Re-sync provides different dates (shouldn't matter — existing values win)
  const meta = {
    ...makeVideoMeta('vid1'),
    videoPublishedAt: '2024-12-01T00:00:00Z',
    addedToPlaylistAt: '2025-02-01T00:00:00Z',
  };
  mockFetchPlaylistVideos.mockResolvedValue([meta]);

  await runIngestion(PLAYLIST_URL, outputFolder, () => {});

  const lastWriteCall = mockWriteIndex.mock.calls[mockWriteIndex.mock.calls.length - 1];
  const writtenVideos: Video[] = lastWriteCall[1].videos;
  const written = writtenVideos.find((v) => v.id === 'vid1');
  // Original values preserved — ?? ensures write-once semantics
  expect(written?.videoPublishedAt).toBe('2024-11-12T14:30:00Z');
  expect(written?.addedToPlaylistAt).toBe('2025-01-03T09:00:00Z');
});
```

- [ ] **Step 2: Run tests — confirm they fail**

```bash
npx jest tests/lib/pipeline.test.ts --no-coverage
```

Expected: 3 new tests FAIL (`videoPublishedAt` and `addedToPlaylistAt` are `undefined` on all videos).

- [ ] **Step 3: Implement — update `lib/pipeline.ts`**

**Change 1:** In the `video: Video = { ... }` block (around line 253), add two date spreads after the `tags` line:

```ts
      const video: Video = {
        id: meta.videoId,
        title: meta.title,
        youtubeUrl: meta.youtubeUrl,
        language,
        durationSeconds: meta.durationSeconds,
        archived: false,
        ratings,
        overallScore,
        summaryMd: `${baseName}.md`,
        summaryPdf: `${baseName}.pdf`,
        deepDiveMd: null,
        deepDivePdf: null,
        processedAt: new Date().toISOString(),
        playlistIndex: current,
        ...(videoType !== undefined && { videoType }),
        ...(audience !== undefined && { audience }),
        ...(meta.channelTitle !== undefined && { channel: meta.channelTitle }),
        ...(tags !== undefined && { tags }),
        ...(meta.videoPublishedAt !== undefined && { videoPublishedAt: meta.videoPublishedAt }),
        ...(meta.addedToPlaylistAt !== undefined && { addedToPlaylistAt: meta.addedToPlaylistAt }),
      };
```

**Change 2:** In the post-reconcile stamping block (around line 299), add date maps alongside `positionMap`:

```ts
  const positionMap = new Map(metas.map((m, idx) => [m.videoId, idx + 1]));
  const publishedMap = new Map(metas.map((m) => [m.videoId, m.videoPublishedAt]));
  const addedMap = new Map(metas.map((m) => [m.videoId, m.addedToPlaylistAt]));
  const afterReconcile = readIndex(outputFolder);
  // Prefer existing values (write-once semantics via ??): playlistIndex, videoPublishedAt,
  // addedToPlaylistAt are all stable IDs stamped at first ingest and never updated.
  const videosWithIndex = afterReconcile.videos.map((v) => ({
    ...v,
    playlistIndex: v.playlistIndex ?? positionMap.get(v.id),
    videoPublishedAt: v.videoPublishedAt ?? publishedMap.get(v.id),
    addedToPlaylistAt: v.addedToPlaylistAt ?? addedMap.get(v.id),
  }));
  writeIndex(outputFolder, { ...afterReconcile, videos: videosWithIndex });
```

- [ ] **Step 4: Run tests — confirm all pass**

```bash
npx jest tests/lib/pipeline.test.ts --no-coverage
```

Expected: all tests PASS.

- [ ] **Step 5: Run full suite — confirm no regressions**

```bash
npm test -- --no-coverage
```

Expected: all tests PASS.

- [ ] **Step 6: Commit**

```bash
git add lib/pipeline.ts tests/lib/pipeline.test.ts
git commit -m "feat(pipeline): stamp and backfill videoPublishedAt, addedToPlaylistAt on ingest"
```

---

## Task 4: API Sort — Date sort cases with null-last logic

**Files:**
- Modify: `app/api/videos/route.ts`
- Test: `tests/api/videos.test.ts`

- [ ] **Step 1: Write failing tests**

Add the following tests to `tests/api/videos.test.ts` inside the existing `describe('GET /api/videos', ...)` block. The existing `makeVideo` helper is at the top of the file — use object spread to add date fields:

```ts
describe('sort by videoPublishedAt', () => {
  it('sorts by videoPublishedAt ascending (oldest first)', async () => {
    mockReadIndex.mockReturnValue(makeIndex([
      { ...makeVideo('vid1', 3), videoPublishedAt: '2025-03-01T00:00:00.000Z' },
      { ...makeVideo('vid2', 3), videoPublishedAt: '2024-11-12T00:00:00.000Z' },
      { ...makeVideo('vid3', 3), videoPublishedAt: '2025-01-20T00:00:00.000Z' },
    ]));
    const res = await get({ sortColumn: 'videoPublishedAt', sortOrder: 'asc' });
    const { videos } = await res.json();
    expect(videos.map((v: Video) => v.id)).toEqual(['vid2', 'vid3', 'vid1']);
  });

  it('sorts by videoPublishedAt descending (newest first)', async () => {
    mockReadIndex.mockReturnValue(makeIndex([
      { ...makeVideo('vid1', 3), videoPublishedAt: '2025-03-01T00:00:00.000Z' },
      { ...makeVideo('vid2', 3), videoPublishedAt: '2024-11-12T00:00:00.000Z' },
      { ...makeVideo('vid3', 3), videoPublishedAt: '2025-01-20T00:00:00.000Z' },
    ]));
    const res = await get({ sortColumn: 'videoPublishedAt', sortOrder: 'desc' });
    const { videos } = await res.json();
    expect(videos.map((v: Video) => v.id)).toEqual(['vid1', 'vid3', 'vid2']);
  });

  it('sorts videos with missing videoPublishedAt to the bottom (asc)', async () => {
    mockReadIndex.mockReturnValue(makeIndex([
      { ...makeVideo('vid1', 3), videoPublishedAt: '2025-01-01T00:00:00.000Z' },
      { ...makeVideo('vid2', 3) }, // no date
      { ...makeVideo('vid3', 3), videoPublishedAt: '2024-06-01T00:00:00.000Z' },
    ]));
    const res = await get({ sortColumn: 'videoPublishedAt', sortOrder: 'asc' });
    const { videos } = await res.json();
    expect(videos.map((v: Video) => v.id)).toEqual(['vid3', 'vid1', 'vid2']);
  });

  it('sorts videos with missing videoPublishedAt to the bottom (desc)', async () => {
    mockReadIndex.mockReturnValue(makeIndex([
      { ...makeVideo('vid1', 3), videoPublishedAt: '2025-01-01T00:00:00.000Z' },
      { ...makeVideo('vid2', 3) }, // no date
      { ...makeVideo('vid3', 3), videoPublishedAt: '2024-06-01T00:00:00.000Z' },
    ]));
    const res = await get({ sortColumn: 'videoPublishedAt', sortOrder: 'desc' });
    const { videos } = await res.json();
    expect(videos.map((v: Video) => v.id)).toEqual(['vid1', 'vid3', 'vid2']);
  });
});

describe('sort by addedToPlaylistAt', () => {
  it('sorts by addedToPlaylistAt descending (newest first)', async () => {
    mockReadIndex.mockReturnValue(makeIndex([
      { ...makeVideo('vid1', 3), addedToPlaylistAt: '2025-04-01T00:00:00.000Z' },
      { ...makeVideo('vid2', 3), addedToPlaylistAt: '2025-01-15T00:00:00.000Z' },
      { ...makeVideo('vid3', 3), addedToPlaylistAt: '2025-06-10T00:00:00.000Z' },
    ]));
    const res = await get({ sortColumn: 'addedToPlaylistAt', sortOrder: 'desc' });
    const { videos } = await res.json();
    expect(videos.map((v: Video) => v.id)).toEqual(['vid3', 'vid1', 'vid2']);
  });

  it('sorts videos with missing addedToPlaylistAt to the bottom (desc)', async () => {
    mockReadIndex.mockReturnValue(makeIndex([
      { ...makeVideo('vid1', 3), addedToPlaylistAt: '2025-04-01T00:00:00.000Z' },
      { ...makeVideo('vid2', 3) }, // no date
    ]));
    const res = await get({ sortColumn: 'addedToPlaylistAt', sortOrder: 'desc' });
    const { videos } = await res.json();
    expect(videos.map((v: Video) => v.id)).toEqual(['vid1', 'vid2']);
  });
});
```

- [ ] **Step 2: Run tests — confirm they fail**

```bash
npx jest tests/api/videos.test.ts --no-coverage
```

Expected: 6 new tests FAIL (date sort falls through to ratings branch, returns wrong order).

- [ ] **Step 3: Implement — update `sortVideos` in `app/api/videos/route.ts`**

Replace the `sortVideos` function with the following (adds date cases before the `else` ratings fallthrough):

```ts
function sortVideos(videos: Video[], column: SortColumn, order: SortOrder): Video[] {
  const sorted = [...videos].sort((a, b) => {
    let aVal: string | number;
    let bVal: string | number;
    if (column === 'name') {
      aVal = a.title.toLowerCase();
      bVal = b.title.toLowerCase();
    } else if (column === 'overall') {
      aVal = a.overallScore;
      bVal = b.overallScore;
    } else if (column === 'language') {
      aVal = a.language ?? '';
      bVal = b.language ?? '';
    } else if (column === 'videoType') {
      aVal = a.videoType ?? '';
      bVal = b.videoType ?? '';
    } else if (column === 'audience') {
      aVal = AUDIENCE_ORDER[a.audience ?? ''] ?? 0;
      bVal = AUDIENCE_ORDER[b.audience ?? ''] ?? 0;
    } else if (column === 'playlistIndex') {
      aVal = a.playlistIndex ?? 0;
      bVal = b.playlistIndex ?? 0;
    } else if (column === 'videoPublishedAt' || column === 'addedToPlaylistAt') {
      const aDate = a[column];
      const bDate = b[column];
      if (!aDate && !bDate) return 0;
      if (!aDate) return 1;  // nulls always to bottom
      if (!bDate) return -1;
      const cmp = aDate.localeCompare(bDate);
      return order === 'asc' ? cmp : -cmp;
    } else {
      aVal = a.ratings[column];
      bVal = b.ratings[column];
    }
    if (aVal < bVal) return order === 'asc' ? -1 : 1;
    if (aVal > bVal) return order === 'asc' ? 1 : -1;
    return 0;
  });
  return sorted;
}
```

- [ ] **Step 4: Run tests — confirm all pass**

```bash
npx jest tests/api/videos.test.ts --no-coverage
```

Expected: all tests PASS.

- [ ] **Step 5: Run full suite — confirm no regressions**

```bash
npm test -- --no-coverage
```

Expected: all tests PASS.

- [ ] **Step 6: Commit**

```bash
git add app/api/videos/route.ts tests/api/videos.test.ts
git commit -m "feat(api): sort by videoPublishedAt and addedToPlaylistAt with null-last logic"
```

---

## Task 5: VideoRow — Render date cells

**Files:**
- Modify: `components/VideoRow.tsx`
- Test: `tests/components/VideoRow.test.tsx`

- [ ] **Step 1: Write failing tests**

Add the following tests to `tests/components/VideoRow.test.tsx` inside the existing `describe('VideoRow', () => describe('row display', ...)` block (or add a new nested `describe`). The existing `renderRow` helper and `baseVideo` fixture are at the top of the file:

```ts
describe('date cells', () => {
  it('renders videoPublishedAt as YYYY-MM-DD', () => {
    renderRow({ videoPublishedAt: '2024-11-12T14:30:00.000Z' });
    expect(screen.getByRole('cell', { name: 'Published on YouTube' })).toHaveTextContent('2024-11-12');
  });

  it('renders — when videoPublishedAt is absent', () => {
    renderRow(); // baseVideo has no videoPublishedAt
    expect(screen.getByRole('cell', { name: 'Published on YouTube' })).toHaveTextContent('—');
  });

  it('renders addedToPlaylistAt as YYYY-MM-DD', () => {
    renderRow({ addedToPlaylistAt: '2025-01-03T09:00:00.000Z' });
    expect(screen.getByRole('cell', { name: 'Added to playlist' })).toHaveTextContent('2025-01-03');
  });

  it('renders — when addedToPlaylistAt is absent', () => {
    renderRow(); // baseVideo has no addedToPlaylistAt
    expect(screen.getByRole('cell', { name: 'Added to playlist' })).toHaveTextContent('—');
  });
});
```

- [ ] **Step 2: Run tests — confirm they fail**

```bash
npx jest tests/components/VideoRow.test.tsx --no-coverage
```

Expected: 4 new tests FAIL (cells with those `aria-label` values don't exist yet).

- [ ] **Step 3: Implement — add date cells to `components/VideoRow.tsx`**

Insert two new `<td>` elements after the `audience` cell (after line ~97) and before the `usefulness` cell:

```tsx
      <td className={`px-3 py-2 ${dim}`}>
        {video.audience && (
          <Badge label={video.audience} colorClass={AUDIENCE_COLOR[video.audience] ?? ''} />
        )}
      </td>
      <td className={`px-3 py-2 text-sm tabular-nums text-zinc-400 ${dim}`} aria-label="Published on YouTube">
        {video.videoPublishedAt ? video.videoPublishedAt.slice(0, 10) : '—'}
      </td>
      <td className={`px-3 py-2 text-sm tabular-nums text-zinc-400 ${dim}`} aria-label="Added to playlist">
        {video.addedToPlaylistAt ? video.addedToPlaylistAt.slice(0, 10) : '—'}
      </td>
      <td className={`px-3 py-2 text-sm tabular-nums font-mono text-right text-zinc-200 ${dim}`} aria-label="Usefulness">{ratings.usefulness}</td>
```

- [ ] **Step 4: Run tests — confirm all pass**

```bash
npx jest tests/components/VideoRow.test.tsx --no-coverage
```

Expected: all tests PASS.

- [ ] **Step 5: Run full suite — confirm no regressions**

```bash
npm test -- --no-coverage
```

Expected: all tests PASS.

- [ ] **Step 6: Commit**

```bash
git add components/VideoRow.tsx tests/components/VideoRow.test.tsx
git commit -m "feat(VideoRow): render Published and Added date cells (YYYY-MM-DD or —)"
```

---

## Task 6: VideoList — Add columns and first-click desc for date cols

**Files:**
- Modify: `components/VideoList.tsx`
- Test: `tests/components/VideoList.test.tsx`

- [ ] **Step 1: Write failing tests**

Find the `describe('VideoList', ...)` block in `tests/components/VideoList.test.tsx`. Add or update the following:

**Update the existing "11 sort buttons" test to 13:**

```ts
// Change this line:
it('renders 11 sort buttons in the column header row when onSort is provided', () => {
// To:
it('renders 13 sort buttons in the column header row when onSort is provided', () => {
```

And update the assertion from `toHaveLength(11)` to `toHaveLength(13)`.

**Add new tests for date column first-click behaviour:**

```ts
it('first click on Published calls onSort("videoPublishedAt", "desc")', () => {
  const onSort = jest.fn();
  renderWithSort({ onSort });
  fireEvent.click(screen.getByRole('button', { name: /published on youtube/i }));
  expect(onSort).toHaveBeenCalledWith('videoPublishedAt', 'desc');
});

it('first click on Added calls onSort("addedToPlaylistAt", "desc")', () => {
  const onSort = jest.fn();
  renderWithSort({ onSort });
  fireEvent.click(screen.getByRole('button', { name: /added to playlist/i }));
  expect(onSort).toHaveBeenCalledWith('addedToPlaylistAt', 'desc');
});

it('clicking active Published (desc) calls onSort with asc', () => {
  const onSort = jest.fn();
  renderWithSort({ sortColumn: 'videoPublishedAt', sortOrder: 'desc', onSort });
  fireEvent.click(screen.getByRole('button', { name: /published on youtube/i }));
  expect(onSort).toHaveBeenCalledWith('videoPublishedAt', 'asc');
});

it('first click on non-date column (Title) still calls onSort with asc', () => {
  const onSort = jest.fn();
  renderWithSort({ onSort });
  fireEvent.click(screen.getByRole('button', { name: /^title$/i }));
  expect(onSort).toHaveBeenCalledWith('name', 'asc');
});
```

- [ ] **Step 2: Run tests — confirm they fail**

```bash
npx jest tests/components/VideoList.test.tsx --no-coverage
```

Expected: 5 tests FAIL (button count is 11 not 13; date col buttons don't exist; first-click still returns 'asc').

- [ ] **Step 3: Implement — update `components/VideoList.tsx`**

**Change 1:** Add two new entries to the `COLUMNS` array after `audience` and before `usefulness`:

```ts
const COLUMNS: { key: SortColumn; label: string; fullName: string; align: 'left' | 'right' }[] = [
  { key: 'playlistIndex', label: '#', fullName: 'Playlist position', align: 'left' },
  { key: 'name', label: 'Title', fullName: 'Title', align: 'left' },
  { key: 'language', label: 'Lang', fullName: 'Language', align: 'left' },
  { key: 'videoType', label: 'Type', fullName: 'Type', align: 'left' },
  { key: 'audience', label: 'Audience', fullName: 'Audience', align: 'left' },
  { key: 'videoPublishedAt', label: 'Published', fullName: 'Published on YouTube', align: 'left' },
  { key: 'addedToPlaylistAt', label: 'Added', fullName: 'Added to playlist', align: 'left' },
  { key: 'usefulness', label: 'USE', fullName: 'Usefulness', align: 'right' },
  { key: 'depth', label: 'DPT', fullName: 'Depth', align: 'right' },
  { key: 'originality', label: 'ORI', fullName: 'Originality', align: 'right' },
  { key: 'recency', label: 'RCN', fullName: 'Recency', align: 'right' },
  { key: 'completeness', label: 'CMP', fullName: 'Completeness', align: 'right' },
  { key: 'overall', label: 'OVR', fullName: 'Overall', align: 'right' },
];
```

**Change 2:** Replace `handleHeaderClick` with a version that defaults date columns to `desc` on first click:

```ts
const DATE_COLS: SortColumn[] = ['videoPublishedAt', 'addedToPlaylistAt'];

// inside the component, replace handleHeaderClick:
function handleHeaderClick(col: SortColumn) {
  if (!onSort) return;
  let nextOrder: SortOrder;
  if (col === sortColumn) {
    nextOrder = sortOrder === 'asc' ? 'desc' : 'asc';
  } else if (DATE_COLS.includes(col)) {
    nextOrder = 'desc';
  } else {
    nextOrder = 'asc';
  }
  onSort(col, nextOrder);
}
```

Place `const DATE_COLS` outside the component (at module scope, after the `COLUMNS` array) so it's not recreated on every render.

- [ ] **Step 4: Run tests — confirm all pass**

```bash
npx jest tests/components/VideoList.test.tsx --no-coverage
```

Expected: all tests PASS.

- [ ] **Step 5: Run full suite — confirm no regressions**

```bash
npm test -- --no-coverage
```

Expected: all tests PASS.

- [ ] **Step 6: Commit**

```bash
git add components/VideoList.tsx tests/components/VideoList.test.tsx
git commit -m "feat(VideoList): add Published/Added columns; date cols default to desc on first click"
```

---

## Done

After all 6 tasks are committed, both date columns are live. Run the app (`npm run dev`) and sync a playlist — `Published` and `Added` columns appear after `Audience`, both sortable, newest-first on first click.
