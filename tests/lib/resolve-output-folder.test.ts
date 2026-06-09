import fs from 'fs';
import { resolveOutputFolder } from '../../lib/output-folder';
import { fetchPlaylistTitle } from '../../lib/youtube';

jest.mock('fs');
jest.mock('../../lib/youtube', () => ({ fetchPlaylistTitle: jest.fn() }));

const mockFetchTitle = fetchPlaylistTitle as jest.Mock;

// Virtual filesystem: `root` exists, `dirs` are its subdirectories, `files` maps
// absolute index paths to their JSON contents.
function setupFs(opts: { root: string; dirs: string[]; files: Record<string, string> }) {
  (fs.existsSync as jest.Mock).mockImplementation(
    (p: string) => p === opts.root || p in opts.files,
  );
  (fs.readdirSync as jest.Mock).mockImplementation((p: string) =>
    p === opts.root ? opts.dirs.map((name) => ({ name, isDirectory: () => true })) : [],
  );
  (fs.readFileSync as jest.Mock).mockImplementation((p: string) => {
    if (p in opts.files) return opts.files[p];
    throw new Error(`ENOENT ${p}`);
  });
}

const idx = (listId: string) =>
  JSON.stringify({ playlistUrl: `https://youtube.com/playlist?list=${listId}&si=abc` });

describe('resolveOutputFolder', () => {
  beforeEach(() => jest.clearAllMocks());

  it('matches an existing NESTED playlist by id → returns <dir>/raw', async () => {
    setupFs({
      root: '/d',
      dirs: ['agentic'],
      files: { '/d/agentic/raw/playlist-index.json': idx('PLabc') },
    });
    const out = await resolveOutputFolder('https://youtube.com/playlist?list=PLabc', '/d', 'key');
    expect(out).toBe('/d/agentic/raw');
    expect(mockFetchTitle).not.toHaveBeenCalled();
  });

  it('matches an existing FLAT playlist by id → returns <dir>', async () => {
    setupFs({
      root: '/d',
      dirs: ['cs146s'],
      files: { '/d/cs146s/playlist-index.json': idx('PLxyz') },
    });
    const out = await resolveOutputFolder('https://youtube.com/playlist?list=PLxyz&si=zzz', '/d', 'key');
    expect(out).toBe('/d/cs146s');
  });

  it('new playlist (no match) → fetches title and returns <root>/<slug>/raw', async () => {
    setupFs({
      root: '/d',
      dirs: ['agentic'],
      files: { '/d/agentic/raw/playlist-index.json': idx('PLother') },
    });
    mockFetchTitle.mockResolvedValue('Cool Title!');
    const out = await resolveOutputFolder('https://youtube.com/playlist?list=PLnew', '/d', 'key');
    expect(out).toBe('/d/cool-title/raw');
    expect(mockFetchTitle).toHaveBeenCalledWith('PLnew', 'key');
  });

  it('new playlist without an API key → slugs the playlist id, no fetch', async () => {
    setupFs({ root: '/d', dirs: [], files: {} });
    const out = await resolveOutputFolder('https://youtube.com/playlist?list=PLnew', '/d', undefined);
    expect(out).toBe('/d/plnew/raw');
    expect(mockFetchTitle).not.toHaveBeenCalled();
  });

  it('treats a missing root as a new playlist (no scan crash)', async () => {
    (fs.existsSync as jest.Mock).mockReturnValue(false);
    mockFetchTitle.mockResolvedValue('Title');
    const out = await resolveOutputFolder('https://youtube.com/playlist?list=PLnew', '/d', 'key');
    expect(out).toBe('/d/title/raw');
  });

  it('skips a corrupt index and still finds a later valid match', async () => {
    setupFs({
      root: '/d',
      dirs: ['bad', 'good'],
      files: {
        '/d/bad/raw/playlist-index.json': '{ not valid json',
        '/d/good/raw/playlist-index.json': idx('PLwant'),
      },
    });
    const out = await resolveOutputFolder('https://youtube.com/playlist?list=PLwant', '/d', 'key');
    expect(out).toBe('/d/good/raw');
  });

  it('falls back to an id slug when the title fetch fails', async () => {
    setupFs({ root: '/d', dirs: [], files: {} });
    mockFetchTitle.mockRejectedValue(new Error('quota exceeded'));
    const out = await resolveOutputFolder('https://youtube.com/playlist?list=PLnew', '/d', 'key');
    expect(out).toBe('/d/plnew/raw');
  });

  it('rejects a URL with no list= id', async () => {
    setupFs({ root: '/d', dirs: [], files: {} });
    await expect(resolveOutputFolder('https://youtube.com/watch?v=abc', '/d', 'key')).rejects.toThrow();
  });

  it('rejects an unparseable URL', async () => {
    setupFs({ root: '/d', dirs: [], files: {} });
    await expect(resolveOutputFolder('not a url', '/d', 'key')).rejects.toThrow();
  });
});
