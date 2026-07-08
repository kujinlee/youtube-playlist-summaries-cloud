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

describe('fetchPlaylistVideos maxItems bound', () => {
  it('bounds both pagination and the videos.list metadata fetch to maxItems', async () => {
    // 5-item playlist, paginated 1 item per page (5 pages total if unbounded).
    const allIds = ['vid1', 'vid2', 'vid3', 'vid4', 'vid5'];
    mockPlaylistItemsList.mockImplementation(({ pageToken }: { pageToken?: string }) => {
      const idx = pageToken ? Number(pageToken) : 0;
      const id = allIds[idx];
      const nextPageToken = idx + 1 < allIds.length ? String(idx + 1) : null;
      return Promise.resolve({
        data: { items: [{ contentDetails: { videoId: id } }], nextPageToken },
      });
    });
    mockVideosList.mockImplementation(({ id }: { id: string[] }) => Promise.resolve({
      data: {
        items: id.map((videoId) => ({
          id: videoId,
          snippet: { title: `Title ${videoId}` },
          contentDetails: { duration: 'PT1M' },
        })),
      },
    }));

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
