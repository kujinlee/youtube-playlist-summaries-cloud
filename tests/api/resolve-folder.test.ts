jest.mock('../../lib/settings-store');
// Partial-mock: keep the real InvalidPlaylistUrlError class, stub resolveOutputFolder.
jest.mock('../../lib/output-folder', () => ({
  ...jest.requireActual('../../lib/output-folder'),
  resolveOutputFolder: jest.fn(),
}));

import { GET } from '../../app/api/resolve-folder/route';
import * as settings from '../../lib/settings-store';
import * as outputFolder from '../../lib/output-folder';
import { InvalidPlaylistUrlError } from '../../lib/output-folder';

const mockReadSettings = jest.mocked(settings.readSettings);
const mockResolve = jest.mocked(outputFolder.resolveOutputFolder);

const PLAYLIST_URL = 'https://youtube.com/playlist?list=PLabc';

function getReq(query: string) {
  return GET(new Request(`http://localhost/api/resolve-folder${query}`));
}

describe('GET /api/resolve-folder', () => {
  afterEach(() => jest.clearAllMocks());

  it('400 when url param is missing', async () => {
    const res = await getReq('');
    expect(res.status).toBe(400);
  });

  it('400 when no base output folder is configured', async () => {
    mockReadSettings.mockReturnValue({ outputFolder: '' });
    const res = await getReq(`?url=${encodeURIComponent(PLAYLIST_URL)}`);
    expect(res.status).toBe(400);
    expect(mockResolve).not.toHaveBeenCalled();
  });

  it('returns the resolved outputFolder, anchored on baseOutputFolder', async () => {
    mockReadSettings.mockReturnValue({ baseOutputFolder: '/d', outputFolder: '/d/x/raw' });
    mockResolve.mockResolvedValue('/d/agentic-ai-claude-code/raw');
    const res = await getReq(`?url=${encodeURIComponent(PLAYLIST_URL)}`);
    expect(res.status).toBe(200);
    expect(await res.json()).toEqual({ outputFolder: '/d/agentic-ai-claude-code/raw' });
    expect(mockResolve).toHaveBeenCalledWith(PLAYLIST_URL, '/d', process.env.YOUTUBE_API_KEY);
  });

  it('falls back to outputFolder as root when baseOutputFolder is absent', async () => {
    mockReadSettings.mockReturnValue({ outputFolder: '/only' });
    mockResolve.mockResolvedValue('/only/p/raw');
    await getReq(`?url=${encodeURIComponent(PLAYLIST_URL)}`);
    expect(mockResolve).toHaveBeenCalledWith(PLAYLIST_URL, '/only', process.env.YOUTUBE_API_KEY);
  });

  it('400 for an invalid playlist URL (InvalidPlaylistUrlError)', async () => {
    mockReadSettings.mockReturnValue({ baseOutputFolder: '/d', outputFolder: '/d' });
    mockResolve.mockRejectedValue(new InvalidPlaylistUrlError('playlist URL has no ?list= id'));
    const res = await getReq(`?url=${encodeURIComponent('https://youtube.com/watch?v=x')}`);
    expect(res.status).toBe(400);
    expect(await res.json()).toEqual({ error: 'playlist URL has no ?list= id' });
  });

  it('500 generic (no leak) when the resolver throws an unexpected error', async () => {
    mockReadSettings.mockReturnValue({ baseOutputFolder: '/d', outputFolder: '/d' });
    mockResolve.mockRejectedValue(new Error('EACCES /secret/internal/path'));
    const res = await getReq(`?url=${encodeURIComponent(PLAYLIST_URL)}`);
    expect(res.status).toBe(500);
    expect(await res.json()).toEqual({ error: 'failed to resolve folder' });
  });
});
