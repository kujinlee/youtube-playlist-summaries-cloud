import { fetchPlaylistVideos } from '@/lib/youtube';
import { google } from 'googleapis';

jest.mock('googleapis', () => ({
  google: { youtube: jest.fn() },
}));

const mockPlaylistItemsList = jest.fn();
const mockVideosList = jest.fn();

beforeEach(() => {
  jest.clearAllMocks();
  (google.youtube as jest.Mock).mockReturnValue({
    playlistItems: { list: mockPlaylistItemsList },
    videos: { list: mockVideosList },
  });
});

function mockVideosListImpl({ id }: { id: string[] }) {
  return Promise.resolve({
    data: {
      items: id.map((videoId) => ({
        id: videoId,
        snippet: { title: `Title ${videoId}` },
        contentDetails: { duration: 'PT1M' },
      })),
    },
  });
}

describe('fetchPlaylistVideos maxItems bound', () => {
  it('bounds the videos.list metadata fetch to maxItems when a single page overshoots it', async () => {
    // Single page returns MORE items than maxItems, so the pagination-bound loop
    // (`while pageToken && videoIds.length < maxItems`) cannot stop things early —
    // the `videoIds.slice(0, maxItems)` bound is the only thing preventing videos.list
    // from being called with all 5 ids.
    const allIds = ['v1', 'v2', 'v3', 'v4', 'v5'];
    mockPlaylistItemsList.mockResolvedValue({
      data: {
        items: allIds.map((id) => ({ contentDetails: { videoId: id }, snippet: { publishedAt: '2024-01-01T00:00:00Z' } })),
        nextPageToken: null,
      },
    });
    mockVideosList.mockImplementation(mockVideosListImpl);

    const result = await fetchPlaylistVideos(
      'https://www.youtube.com/playlist?list=PLtest123',
      'fake-api-key',
      { maxItems: 2 },
    );

    // playlistItems.list is only called once since the single page already has nextPageToken: null.
    expect(mockPlaylistItemsList.mock.calls.length).toBe(1);

    // The critical assertion: videos.list must only ever be asked about the first
    // 2 ids (v1, v2) — NOT all 5 ids from the overshot page.
    const allRequestedIds = mockVideosList.mock.calls.flatMap((call) => call[0].id);
    expect(allRequestedIds.length).toBe(2);
    expect(allRequestedIds).toEqual(['v1', 'v2']);

    expect(result.length).toBeLessThanOrEqual(2);
    expect(result.map((v) => v.videoId)).toEqual(['v1', 'v2']);
  });

  it('stops paginating once maxItems is reached across multiple pages', async () => {
    // 5-item playlist, paginated 1 item per page (5 pages total if unbounded).
    const allIds = ['vid1', 'vid2', 'vid3', 'vid4', 'vid5'];
    mockPlaylistItemsList.mockImplementation(({ pageToken }: { pageToken?: string }) => {
      const idx = pageToken ? Number(pageToken) : 0;
      const id = allIds[idx];
      const nextPageToken = idx + 1 < allIds.length ? String(idx + 1) : null;
      return Promise.resolve({
        data: { items: [{ contentDetails: { videoId: id }, snippet: { publishedAt: '2024-01-01T00:00:00Z' } }], nextPageToken },
      });
    });
    mockVideosList.mockImplementation(mockVideosListImpl);

    const result = await fetchPlaylistVideos(
      'https://www.youtube.com/playlist?list=PLtest123',
      'fake-api-key',
      { maxItems: 2 },
    );

    expect(mockPlaylistItemsList.mock.calls.length).toBeLessThanOrEqual(2);
    for (const call of mockVideosList.mock.calls) {
      expect(call[0].id.length).toBeLessThanOrEqual(2);
    }
    expect(result.length).toBeLessThanOrEqual(2);
  });
});
