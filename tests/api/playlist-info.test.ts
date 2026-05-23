jest.mock('../../lib/youtube');

import { GET } from '../../app/api/playlist-info/route';
import * as youtube from '../../lib/youtube';

const mockFetchPlaylistTitle = jest.mocked(youtube.fetchPlaylistTitle);

const ORIGINAL_ENV = { ...process.env };

afterEach(() => {
  process.env = { ...ORIGINAL_ENV };
  jest.clearAllMocks();
});

function get(params: Record<string, string> = {}) {
  const query = new URLSearchParams(params).toString();
  return GET(new Request(`http://localhost/api/playlist-info?${query}`));
}

describe('GET /api/playlist-info', () => {
  it('returns 400 when url param is missing', async () => {
    const res = await get();
    expect(res.status).toBe(400);
  });

  it('returns 400 for a non-URL string', async () => {
    const res = await get({ url: 'not-a-url' });
    expect(res.status).toBe(400);
  });

  it('returns 400 for a URL without a ?list= param', async () => {
    const res = await get({ url: 'https://www.youtube.com/watch?v=abc123' });
    expect(res.status).toBe(400);
  });

  it('returns playlistId as title when YOUTUBE_API_KEY is not set', async () => {
    delete process.env.YOUTUBE_API_KEY;
    const res = await get({ url: 'https://www.youtube.com/playlist?list=PLtest123' });
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body).toEqual({ playlistId: 'PLtest123', title: 'PLtest123' });
    expect(mockFetchPlaylistTitle).not.toHaveBeenCalled();
  });

  it('fetches title from YouTube API when YOUTUBE_API_KEY is set', async () => {
    process.env.YOUTUBE_API_KEY = 'test-key';
    mockFetchPlaylistTitle.mockResolvedValue('My Playlist Title');
    const res = await get({ url: 'https://www.youtube.com/playlist?list=PLtest123' });
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body).toEqual({ playlistId: 'PLtest123', title: 'My Playlist Title' });
    expect(mockFetchPlaylistTitle).toHaveBeenCalledWith('PLtest123', 'test-key');
  });

  it('falls back to playlistId as title when YouTube API call fails', async () => {
    process.env.YOUTUBE_API_KEY = 'test-key';
    mockFetchPlaylistTitle.mockRejectedValue(new Error('API error'));
    const res = await get({ url: 'https://www.youtube.com/playlist?list=PLtest123' });
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body).toEqual({ playlistId: 'PLtest123', title: 'PLtest123' });
  });

  it('strips extra query params from the playlist URL (e.g. &si=...)', async () => {
    delete process.env.YOUTUBE_API_KEY;
    const res = await get({
      url: 'https://www.youtube.com/playlist?list=PLtest123&si=abc',
    });
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.playlistId).toBe('PLtest123');
  });
});
