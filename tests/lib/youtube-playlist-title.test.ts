import { fetchPlaylistTitle, fetchPlaylistTitleOrNull } from '@/lib/youtube';
import { google } from 'googleapis';

jest.mock('googleapis', () => ({
  google: { youtube: jest.fn() },
}));

const mockPlaylistsList = jest.fn();

beforeEach(() => {
  jest.clearAllMocks();
  (google.youtube as jest.Mock).mockReturnValue({
    playlists: { list: mockPlaylistsList },
  });
});

describe('fetchPlaylistTitleOrNull', () => {
  it('returns the real title when items[0].snippet.title is present', async () => {
    mockPlaylistsList.mockResolvedValue({
      data: { items: [{ snippet: { title: 'My Real Playlist' } }] },
    });

    const result = await fetchPlaylistTitleOrNull('PLtest123', 'fake-api-key');

    expect(result).toBe('My Real Playlist');
  });

  it('returns null (not the list-id) when items is empty', async () => {
    mockPlaylistsList.mockResolvedValue({ data: { items: [] } });

    const result = await fetchPlaylistTitleOrNull('PLtest123', 'fake-api-key');

    expect(result).toBeNull();
    expect(result).not.toBe('PLtest123');
  });

  it('returns null (not the list-id) when items is absent', async () => {
    mockPlaylistsList.mockResolvedValue({ data: {} });

    const result = await fetchPlaylistTitleOrNull('PLtest123', 'fake-api-key');

    expect(result).toBeNull();
  });

  it('propagates errors from playlists.list', async () => {
    mockPlaylistsList.mockRejectedValue(new Error('YouTube API down'));

    await expect(
      fetchPlaylistTitleOrNull('PLtest123', 'fake-api-key'),
    ).rejects.toThrow('YouTube API down');
  });
});

describe('fetchPlaylistTitle (delegates to fetchPlaylistTitleOrNull)', () => {
  it('still falls back to the playlist id when there is no item (local callers unchanged)', async () => {
    mockPlaylistsList.mockResolvedValue({ data: { items: [] } });

    const result = await fetchPlaylistTitle('PLtest123', 'fake-api-key');

    expect(result).toBe('PLtest123');
  });

  it('returns the real title when present', async () => {
    mockPlaylistsList.mockResolvedValue({
      data: { items: [{ snippet: { title: 'My Real Playlist' } }] },
    });

    const result = await fetchPlaylistTitle('PLtest123', 'fake-api-key');

    expect(result).toBe('My Real Playlist');
  });

  it('propagates errors from playlists.list', async () => {
    mockPlaylistsList.mockRejectedValue(new Error('YouTube API down'));

    await expect(
      fetchPlaylistTitle('PLtest123', 'fake-api-key'),
    ).rejects.toThrow('YouTube API down');
  });
});
