jest.mock('../../lib/index-store');

import { GET } from '../../app/api/videos/route';
import * as indexStore from '../../lib/index-store';
import type { Video, PlaylistIndex } from '../../types';

const mockReadIndex = jest.mocked(indexStore.readIndex);
const mockAssertOutputFolder = jest.mocked(indexStore.assertOutputFolder);

function makeVideo(id: string, overallScore: number, title = `Video ${id}`, personalScore?: number): Video {
  return {
    id,
    title,
    youtubeUrl: `https://youtube.com/watch?v=${id}`,
    language: 'en',
    durationSeconds: 300,
    archived: false,
    ratings: { usefulness: 3, depth: 3, originality: 3, recency: 3, completeness: 3 },
    overallScore,
    personalScore,
    summaryMd: `${id}.md`,
    processedAt: new Date().toISOString(),
  };
}

function makeIndex(videos: Video[]): PlaylistIndex {
  return { playlistUrl: 'https://youtube.com/playlist?list=PLtest', outputFolder: '/tmp/out', videos };
}

const OUTPUT_FOLDER = '/tmp/out';

function get(params: Record<string, string> = {}) {
  const query = new URLSearchParams({ outputFolder: OUTPUT_FOLDER, ...params }).toString();
  return GET(new Request(`http://localhost/api/videos?${query}`));
}

describe('GET /api/videos', () => {
  beforeEach(() => {
    mockAssertOutputFolder.mockImplementation(() => {});
    mockReadIndex.mockReturnValue(makeIndex([
      makeVideo('vid1', 4, 'Beta'),
      makeVideo('vid2', 2, 'Alpha'),
      makeVideo('vid3', 5, 'Gamma'),
    ]));
  });

  afterEach(() => jest.clearAllMocks());

  it('returns 200 with videos array', async () => {
    const res = await get();
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(Array.isArray(body.videos)).toBe(true);
    expect(body.videos).toHaveLength(3);
  });

  it('sorts by name ascending by default', async () => {
    const res = await get({ sortColumn: 'name', sortOrder: 'asc' });
    const { videos } = await res.json();
    expect(videos.map((v: Video) => v.title)).toEqual(['Alpha', 'Beta', 'Gamma']);
  });

  it('sorts by name descending', async () => {
    const res = await get({ sortColumn: 'name', sortOrder: 'desc' });
    const { videos } = await res.json();
    expect(videos.map((v: Video) => v.title)).toEqual(['Gamma', 'Beta', 'Alpha']);
  });

  it('sorts by overallScore ascending', async () => {
    const res = await get({ sortColumn: 'overall', sortOrder: 'asc' });
    const { videos } = await res.json();
    expect(videos.map((v: Video) => v.overallScore)).toEqual([2, 4, 5]);
  });

  it('sorts by overallScore descending', async () => {
    const res = await get({ sortColumn: 'overall', sortOrder: 'desc' });
    const { videos } = await res.json();
    expect(videos.map((v: Video) => v.overallScore)).toEqual([5, 4, 2]);
  });

  it('returns 400 when outputFolder is missing', async () => {
    const res = await GET(new Request('http://localhost/api/videos'));
    expect(res.status).toBe(400);
  });

  it('sorts by serialNumber ascending', async () => {
    mockReadIndex.mockReturnValue(makeIndex([
      { ...makeVideo('vid1', 4, 'Beta'), serialNumber: 3 },
      { ...makeVideo('vid2', 2, 'Alpha'), serialNumber: 1 },
      { ...makeVideo('vid3', 5, 'Gamma'), serialNumber: 2 },
    ]));
    const res = await get({ sortColumn: 'serialNumber', sortOrder: 'asc' });
    const { videos } = await res.json();
    expect(videos.map((v: Video) => v.id)).toEqual(['vid2', 'vid3', 'vid1']);
  });

  it('sorts by serialNumber descending', async () => {
    mockReadIndex.mockReturnValue(makeIndex([
      { ...makeVideo('vid1', 4, 'Beta'), serialNumber: 3 },
      { ...makeVideo('vid2', 2, 'Alpha'), serialNumber: 1 },
      { ...makeVideo('vid3', 5, 'Gamma'), serialNumber: 2 },
    ]));
    const res = await get({ sortColumn: 'serialNumber', sortOrder: 'desc' });
    const { videos } = await res.json();
    expect(videos.map((v: Video) => v.id)).toEqual(['vid1', 'vid3', 'vid2']);
  });

  it('falls back to name sort for an unrecognized sortColumn (e.g. a stale playlistIndex)', async () => {
    mockReadIndex.mockReturnValue(makeIndex([
      { ...makeVideo('vid1', 4, 'Charlie') },
      { ...makeVideo('vid2', 2, 'Alpha') },
      { ...makeVideo('vid3', 5, 'Bravo') },
    ]));
    const res = await get({ sortColumn: 'playlistIndex', sortOrder: 'asc' });
    const { videos } = await res.json();
    // 'playlistIndex' is no longer a valid column → guard falls back to name (title) sort
    expect(videos.map((v: Video) => v.title)).toEqual(['Alpha', 'Bravo', 'Charlie']);
  });

  it('sorts videos without a serialNumber to the bottom regardless of direction', async () => {
    const withNoSerial = { ...makeVideo('vid2', 2, 'Alpha') };
    delete (withNoSerial as { serialNumber?: number }).serialNumber;
    mockReadIndex.mockReturnValue(makeIndex([
      { ...makeVideo('vid1', 4, 'Beta'), serialNumber: 2 },
      withNoSerial,
      { ...makeVideo('vid3', 5, 'Gamma'), serialNumber: 1 },
    ]));
    const asc = await (await get({ sortColumn: 'serialNumber', sortOrder: 'asc' })).json();
    expect(asc.videos.map((v: Video) => v.id)).toEqual(['vid3', 'vid1', 'vid2']);
    const desc = await (await get({ sortColumn: 'serialNumber', sortOrder: 'desc' })).json();
    expect(desc.videos.map((v: Video) => v.id)).toEqual(['vid1', 'vid3', 'vid2']);
  });

  it('includes playlistUrl from index in the response', async () => {
    const res = await get();
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.playlistUrl).toBe('https://youtube.com/playlist?list=PLtest');
  });

  it('includes playlistTitle from the index', async () => {
    mockReadIndex.mockReturnValue({ playlistUrl: 'https://youtube.com/playlist?list=PLa', playlistTitle: 'Building with Claude', videos: [] } as unknown as PlaylistIndex);
    const res = await get();
    expect((await res.json()).playlistTitle).toBe('Building with Claude');
  });

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

  describe('sort by personalScore', () => {
    beforeEach(() => {
      mockReadIndex.mockReturnValue(makeIndex([
        makeVideo('v1', 3, 'Alpha', 5),
        makeVideo('v2', 3, 'Beta',  2),
        makeVideo('v3', 3, 'Gamma', undefined), // unscored
      ]));
    });

    it('sorts personalScore descending: scored videos high→low, unscored last', async () => {
      const res = await get({ sortColumn: 'personalScore', sortOrder: 'desc' });
      const { videos } = await res.json();
      expect(videos.map((v: Video) => v.id)).toEqual(['v1', 'v2', 'v3']);
    });

    it('sorts personalScore ascending: scored videos low→high, unscored last', async () => {
      const res = await get({ sortColumn: 'personalScore', sortOrder: 'asc' });
      const { videos } = await res.json();
      expect(videos.map((v: Video) => v.id)).toEqual(['v2', 'v1', 'v3']);
    });

    it('two unscored videos maintain stable order (both return 0)', async () => {
      mockReadIndex.mockReturnValue(makeIndex([
        makeVideo('v1', 3, 'Alpha', undefined),
        makeVideo('v2', 3, 'Beta',  undefined),
      ]));
      const res = await get({ sortColumn: 'personalScore', sortOrder: 'asc' });
      const { videos } = await res.json();
      expect(videos.map((v: Video) => v.id)).toEqual(['v1', 'v2']); // stable: unchanged
    });
  });

  describe('sort by channel', () => {
    it('sorts by channel ascending (A→Z)', async () => {
      mockReadIndex.mockReturnValue(makeIndex([
        { ...makeVideo('v1', 3), channel: 'Eric Tech' },
        { ...makeVideo('v2', 3), channel: 'AI Engineer' },
        { ...makeVideo('v3', 3), channel: 'DeepLearningAI' },
      ]));
      const res = await get({ sortColumn: 'channel', sortOrder: 'asc' });
      const { videos } = await res.json();
      expect(videos.map((v: Video) => v.id)).toEqual(['v2', 'v3', 'v1']);
    });

    it('sorts by channel descending (Z→A)', async () => {
      mockReadIndex.mockReturnValue(makeIndex([
        { ...makeVideo('v1', 3), channel: 'Eric Tech' },
        { ...makeVideo('v2', 3), channel: 'AI Engineer' },
        { ...makeVideo('v3', 3), channel: 'DeepLearningAI' },
      ]));
      const res = await get({ sortColumn: 'channel', sortOrder: 'desc' });
      const { videos } = await res.json();
      expect(videos.map((v: Video) => v.id)).toEqual(['v1', 'v3', 'v2']);
    });

    it('sorts videos with missing channel to the bottom, regardless of direction', async () => {
      mockReadIndex.mockReturnValue(makeIndex([
        { ...makeVideo('v1', 3), channel: 'Beta' },
        { ...makeVideo('v2', 3), channel: undefined },
        { ...makeVideo('v3', 3), channel: 'Alpha' },
      ]));
      const asc = await (await get({ sortColumn: 'channel', sortOrder: 'asc' })).json();
      expect(asc.videos.map((v: Video) => v.id)).toEqual(['v3', 'v1', 'v2']);
      const desc = await (await get({ sortColumn: 'channel', sortOrder: 'desc' })).json();
      expect(desc.videos.map((v: Video) => v.id)).toEqual(['v1', 'v3', 'v2']);
    });
  });

  describe('sort by durationSeconds', () => {
    it('sorts by duration ascending (shortest first)', async () => {
      mockReadIndex.mockReturnValue(makeIndex([
        { ...makeVideo('v1', 3), durationSeconds: 985 },
        { ...makeVideo('v2', 3), durationSeconds: 120 },
        { ...makeVideo('v3', 3), durationSeconds: 8927 },
      ]));
      const res = await get({ sortColumn: 'durationSeconds', sortOrder: 'asc' });
      const { videos } = await res.json();
      expect(videos.map((v: Video) => v.id)).toEqual(['v2', 'v1', 'v3']);
    });

    it('sorts by duration descending (longest first)', async () => {
      mockReadIndex.mockReturnValue(makeIndex([
        { ...makeVideo('v1', 3), durationSeconds: 985 },
        { ...makeVideo('v2', 3), durationSeconds: 120 },
        { ...makeVideo('v3', 3), durationSeconds: 8927 },
      ]));
      const res = await get({ sortColumn: 'durationSeconds', sortOrder: 'desc' });
      const { videos } = await res.json();
      expect(videos.map((v: Video) => v.id)).toEqual(['v3', 'v1', 'v2']);
    });
  });

  // An incomplete video row — a reserved slot whose summary has not landed yet
  // (in-flight) or failed/dead-lettered — persists as `{ id, serialNumber }` only:
  // no title, ratings, overallScore, or durationSeconds. The list must render
  // (sorting such rows LAST, regardless of direction) rather than 500 on the whole
  // playlist and hide the videos that DID complete. Repro: a dead-lettered video
  // left a title-less row → `a.title.toLowerCase()` threw → GET /api/videos 500.
  describe('incomplete videos (reserved slots) sort last instead of crashing', () => {
    const slot = { id: 'slot', serialNumber: 9 } as unknown as Video; // no title/ratings/score/duration

    it('name sort: incomplete row last, list still returns 200 (asc)', async () => {
      mockReadIndex.mockReturnValue(makeIndex([
        makeVideo('vid1', 4, 'Beta'), slot, makeVideo('vid3', 5, 'Alpha'),
      ]));
      const res = await get({ sortColumn: 'name', sortOrder: 'asc' });
      expect(res.status).toBe(200);
      const { videos } = await res.json();
      expect(videos.map((v: Video) => v.id)).toEqual(['vid3', 'vid1', 'slot']);
    });

    it('name sort: incomplete row still last regardless of direction (desc)', async () => {
      mockReadIndex.mockReturnValue(makeIndex([
        makeVideo('vid1', 4, 'Beta'), slot, makeVideo('vid3', 5, 'Alpha'),
      ]));
      const res = await get({ sortColumn: 'name', sortOrder: 'desc' });
      expect(res.status).toBe(200);
      const { videos } = await res.json();
      expect(videos.map((v: Video) => v.id)).toEqual(['vid1', 'vid3', 'slot']);
    });

    it('overall sort: incomplete row (no overallScore) last', async () => {
      mockReadIndex.mockReturnValue(makeIndex([
        makeVideo('vid1', 4), slot, makeVideo('vid3', 5),
      ]));
      const res = await get({ sortColumn: 'overall', sortOrder: 'desc' });
      expect(res.status).toBe(200);
      const { videos } = await res.json();
      expect(videos.map((v: Video) => v.id)).toEqual(['vid3', 'vid1', 'slot']);
    });

    it('ratings sort: incomplete row (no ratings) last', async () => {
      mockReadIndex.mockReturnValue(makeIndex([
        makeVideo('vid1', 4), slot, makeVideo('vid3', 5),
      ]));
      const res = await get({ sortColumn: 'usefulness', sortOrder: 'desc' });
      expect(res.status).toBe(200);
      const { videos } = await res.json();
      expect(videos.map((v: Video) => v.id[0])).not.toContain(undefined); // no crash
      expect(videos[videos.length - 1].id).toBe('slot');
    });

    it('duration sort: incomplete row (no durationSeconds) last', async () => {
      mockReadIndex.mockReturnValue(makeIndex([
        { ...makeVideo('vid1', 3), durationSeconds: 500 }, slot,
        { ...makeVideo('vid3', 3), durationSeconds: 120 },
      ]));
      const res = await get({ sortColumn: 'durationSeconds', sortOrder: 'asc' });
      expect(res.status).toBe(200);
      const { videos } = await res.json();
      expect(videos.map((v: Video) => v.id)).toEqual(['vid3', 'vid1', 'slot']);
    });

    // language / videoType / audience are optional metadata: a missing value must sort
    // LAST like every other column (previously coalesced to ''/rank-0, which floated an
    // incomplete row to the TOP for ascending — inconsistent with the fix's invariant).
    it('language sort: incomplete row last in BOTH directions', async () => {
      mockReadIndex.mockReturnValue(makeIndex([
        { ...makeVideo('vid1', 3), language: 'ko' }, slot, { ...makeVideo('vid3', 3), language: 'en' },
      ]));
      const asc = await (await get({ sortColumn: 'language', sortOrder: 'asc' })).json();
      expect(asc.videos.map((v: Video) => v.id)).toEqual(['vid3', 'vid1', 'slot']);
      const desc = await (await get({ sortColumn: 'language', sortOrder: 'desc' })).json();
      expect(desc.videos.map((v: Video) => v.id)).toEqual(['vid1', 'vid3', 'slot']); // present reversed, missing still last
    });

    it('videoType sort: incomplete row last in BOTH directions', async () => {
      mockReadIndex.mockReturnValue(makeIndex([
        { ...makeVideo('vid1', 3), videoType: 'Framework' }, slot, { ...makeVideo('vid3', 3), videoType: 'Analysis' },
      ]));
      const asc = await (await get({ sortColumn: 'videoType', sortOrder: 'asc' })).json();
      expect(asc.videos.map((v: Video) => v.id)).toEqual(['vid3', 'vid1', 'slot']);
      const desc = await (await get({ sortColumn: 'videoType', sortOrder: 'desc' })).json();
      expect(desc.videos.map((v: Video) => v.id)).toEqual(['vid1', 'vid3', 'slot']);
    });

    it('audience sort: incomplete row last in BOTH directions', async () => {
      mockReadIndex.mockReturnValue(makeIndex([
        { ...makeVideo('vid1', 3), audience: 'Advanced' }, slot, { ...makeVideo('vid3', 3), audience: 'Beginner' },
      ]));
      const asc = await (await get({ sortColumn: 'audience', sortOrder: 'asc' })).json();
      expect(asc.videos.map((v: Video) => v.id)).toEqual(['vid3', 'vid1', 'slot']); // Beginner(1) < Advanced(3), missing last
      const desc = await (await get({ sortColumn: 'audience', sortOrder: 'desc' })).json();
      expect(desc.videos.map((v: Video) => v.id)).toEqual(['vid1', 'vid3', 'slot']);
    });
  });
});
