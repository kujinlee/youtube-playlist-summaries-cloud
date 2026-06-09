jest.mock('../../lib/settings-store');
// Partial-mock: keep the real InvalidPlaylistUrlError class; stub resolveOutputFolder
// AND normalizeToRoot so the route's anchoring is observable without touching fs.
jest.mock('../../lib/output-folder', () => ({
  ...jest.requireActual('../../lib/output-folder'),
  resolveOutputFolder: jest.fn(),
  normalizeToRoot: jest.fn(),
}));

import { GET } from '../../app/api/resolve-folder/route';
import * as settings from '../../lib/settings-store';
import * as outputFolder from '../../lib/output-folder';
import { InvalidPlaylistUrlError } from '../../lib/output-folder';

const mockReadSettings = jest.mocked(settings.readSettings);
const mockResolve = jest.mocked(outputFolder.resolveOutputFolder);
const mockNormalize = jest.mocked(outputFolder.normalizeToRoot);

const PLAYLIST_URL = 'https://youtube.com/playlist?list=PLabc';

function getReq(query: string) {
  return GET(new Request(`http://localhost/api/resolve-folder${query}`));
}

describe('GET /api/resolve-folder', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    // identity normalize by default; individual tests override
    mockNormalize.mockImplementation((p: string) => p);
  });

  it('E1: 400 when url param is missing', async () => {
    const res = await getReq('');
    expect(res.status).toBe(400);
  });

  it('E4: 400 when no base output folder is configured', async () => {
    mockReadSettings.mockReturnValue({ outputFolder: '' });
    const res = await getReq(`?url=${encodeURIComponent(PLAYLIST_URL)}`);
    expect(res.status).toBe(400);
    expect(mockResolve).not.toHaveBeenCalled();
    expect(mockNormalize).not.toHaveBeenCalled();
  });

  it('E2: no root param → normalizes the settings root, anchors, returns {root, outputFolder}', async () => {
    // legacy settings: outputFolder points at a playlist subfolder
    mockReadSettings.mockReturnValue({ baseOutputFolder: '/d/cs146s/raw', outputFolder: '/d/cs146s/raw' });
    mockNormalize.mockReturnValue('/d');
    mockResolve.mockResolvedValue('/d/agentic/raw');
    const res = await getReq(`?url=${encodeURIComponent(PLAYLIST_URL)}`);
    expect(res.status).toBe(200);
    // the raw settings root is normalized before anchoring (Codex Blocking #1)
    expect(mockNormalize).toHaveBeenCalledWith('/d/cs146s/raw');
    expect(mockResolve).toHaveBeenCalledWith(PLAYLIST_URL, '/d', process.env.YOUTUBE_API_KEY);
    expect(await res.json()).toEqual({ root: '/d', outputFolder: '/d/agentic/raw' });
  });

  it('E2: falls back to outputFolder as root when baseOutputFolder is absent (then normalizes)', async () => {
    mockReadSettings.mockReturnValue({ outputFolder: '/only/cs146s/raw' });
    mockNormalize.mockReturnValue('/only');
    mockResolve.mockResolvedValue('/only/p/raw');
    await getReq(`?url=${encodeURIComponent(PLAYLIST_URL)}`);
    expect(mockNormalize).toHaveBeenCalledWith('/only/cs146s/raw');
    expect(mockResolve).toHaveBeenCalledWith(PLAYLIST_URL, '/only', process.env.YOUTUBE_API_KEY);
  });

  it('E3: explicit ?root → normalizes it, anchors there (ignores settings root)', async () => {
    mockReadSettings.mockReturnValue({ baseOutputFolder: '/settings-root', outputFolder: '/settings-root' });
    mockNormalize.mockReturnValue('/d');
    mockResolve.mockResolvedValue('/d/cs146s/raw');
    const res = await getReq(
      `?url=${encodeURIComponent(PLAYLIST_URL)}&root=${encodeURIComponent('/d/cs146s/raw')}`,
    );
    expect(res.status).toBe(200);
    expect(mockNormalize).toHaveBeenCalledWith('/d/cs146s/raw');
    expect(mockResolve).toHaveBeenCalledWith(PLAYLIST_URL, '/d', process.env.YOUTUBE_API_KEY);
    expect(await res.json()).toEqual({ root: '/d', outputFolder: '/d/cs146s/raw' });
  });

  it('E4: 400 for an explicit blank root param — not a silent settings fallback', async () => {
    // A blank ?root= must be a client error, never a quiet fallback to the settings root.
    mockReadSettings.mockReturnValue({ baseOutputFolder: '/d', outputFolder: '/d' });
    const res = await getReq(`?url=${encodeURIComponent(PLAYLIST_URL)}&root=${encodeURIComponent('   ')}`);
    expect(res.status).toBe(400);
    expect(mockResolve).not.toHaveBeenCalled();
    expect(mockNormalize).not.toHaveBeenCalled();
  });

  it('E5: 400 for an invalid playlist URL (InvalidPlaylistUrlError)', async () => {
    mockReadSettings.mockReturnValue({ baseOutputFolder: '/d', outputFolder: '/d' });
    mockResolve.mockRejectedValue(new InvalidPlaylistUrlError('playlist URL has no ?list= id'));
    const res = await getReq(`?url=${encodeURIComponent('https://youtube.com/watch?v=x')}`);
    expect(res.status).toBe(400);
    expect(await res.json()).toEqual({ error: 'playlist URL has no ?list= id' });
  });

  it('E6: 500 generic (no leak) when the resolver throws an unexpected error', async () => {
    mockReadSettings.mockReturnValue({ baseOutputFolder: '/d', outputFolder: '/d' });
    mockResolve.mockRejectedValue(new Error('EACCES /secret/internal/path'));
    const res = await getReq(`?url=${encodeURIComponent(PLAYLIST_URL)}`);
    expect(res.status).toBe(500);
    expect(await res.json()).toEqual({ error: 'failed to resolve folder' });
  });
});
