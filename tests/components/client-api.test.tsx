/** @jest-environment jsdom */
import {
  UnauthorizedError,
  listPlaylists,
  listVideos,
  getQuickView,
  saveAnnotation,
  setArchived,
} from '@/lib/client/api';
import type { Scope } from '@/lib/client/scope';

const CLOUD_SCOPE: Scope = { mode: 'cloud', playlistId: '11111111-1111-1111-1111-111111111111' };
const LOCAL_SCOPE: Scope = { mode: 'local', outputFolder: '/tmp/vault', baseOutputFolder: '/tmp' };
const VIDEO_ID = 'abc123XYZ01';

function mockFetchOk(body: unknown) {
  return jest.fn().mockResolvedValue({
    ok: true,
    status: 200,
    json: () => Promise.resolve(body),
  } as unknown as Response);
}

function mockFetchStatus(status: number, body: unknown = {}) {
  return jest.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(body),
  } as unknown as Response);
}

describe('lib/client/api', () => {
  afterEach(() => {
    jest.restoreAllMocks();
  });

  describe('listPlaylists', () => {
    it('fetches /api/playlists and returns the playlists array', async () => {
      const playlists = [
        { id: 'p1', playlistKey: 'k1', playlistUrl: 'https://x', playlistTitle: 'T', createdAt: '2026-01-01' },
      ];
      global.fetch = mockFetchOk({ playlists });
      const result = await listPlaylists();
      expect(global.fetch).toHaveBeenCalledWith('/api/playlists');
      expect(result).toEqual(playlists);
    });
  });

  describe('listVideos', () => {
    it('cloud: builds /api/videos?playlist=<uuid>&sortColumn=&sortOrder= with exact param values', async () => {
      global.fetch = mockFetchOk({ videos: [], playlistUrl: '', playlistTitle: null });
      await listVideos(CLOUD_SCOPE, { column: 'name', order: 'asc' });
      expect(global.fetch).toHaveBeenCalledWith(
        `/api/videos?playlist=${CLOUD_SCOPE.playlistId}&sortColumn=name&sortOrder=asc`,
      );
    });

    it('cloud: omits sortColumn/sortOrder when no sort is passed', async () => {
      global.fetch = mockFetchOk({ videos: [], playlistUrl: '', playlistTitle: null });
      await listVideos(CLOUD_SCOPE);
      expect(global.fetch).toHaveBeenCalledWith(`/api/videos?playlist=${CLOUD_SCOPE.playlistId}`);
    });

    it('local: builds /api/videos?outputFolder=<path>&sortColumn=&sortOrder=', async () => {
      global.fetch = mockFetchOk({ videos: [], playlistUrl: '', playlistTitle: null });
      await listVideos(LOCAL_SCOPE, { column: 'overall', order: 'desc' });
      expect(global.fetch).toHaveBeenCalledWith(
        `/api/videos?outputFolder=${encodeURIComponent(LOCAL_SCOPE.outputFolder as string)}&sortColumn=overall&sortOrder=desc`,
      );
    });

    it('cloud scope with no playlistId throws BEFORE fetch', async () => {
      global.fetch = jest.fn();
      const badScope = { mode: 'cloud', playlistId: '' } as Scope;
      await expect(listVideos(badScope)).rejects.toThrow();
      expect(global.fetch).not.toHaveBeenCalled();
    });

    it('local scope with no outputFolder throws BEFORE fetch', async () => {
      global.fetch = jest.fn();
      const badScope = { mode: 'local', outputFolder: '', baseOutputFolder: '/tmp' } as Scope;
      await expect(listVideos(badScope)).rejects.toThrow();
      expect(global.fetch).not.toHaveBeenCalled();
    });

    it('401 response throws UnauthorizedError', async () => {
      global.fetch = mockFetchStatus(401, { error: 'authentication required' });
      await expect(listVideos(CLOUD_SCOPE)).rejects.toBeInstanceOf(UnauthorizedError);
    });

    it('non-2xx response throws Error with the response error message', async () => {
      global.fetch = mockFetchStatus(400, { error: 'invalid playlist' });
      await expect(listVideos(CLOUD_SCOPE)).rejects.toThrow('invalid playlist');
    });
  });

  describe('getQuickView', () => {
    it('cloud: builds /api/videos/<id>/quick-view?playlist=<uuid>', async () => {
      global.fetch = mockFetchOk({ tldr: 't', takeaways: [], tags: [] });
      await getQuickView(CLOUD_SCOPE, VIDEO_ID);
      expect(global.fetch).toHaveBeenCalledWith(
        `/api/videos/${VIDEO_ID}/quick-view?playlist=${CLOUD_SCOPE.playlistId}`,
      );
    });

    it('local: builds /api/videos/<id>/quick-view?outputFolder=<path>', async () => {
      global.fetch = mockFetchOk({ tldr: 't', takeaways: [], tags: [] });
      await getQuickView(LOCAL_SCOPE, VIDEO_ID);
      expect(global.fetch).toHaveBeenCalledWith(
        `/api/videos/${VIDEO_ID}/quick-view?outputFolder=${encodeURIComponent(LOCAL_SCOPE.outputFolder as string)}`,
      );
    });

    it('cloud scope with no playlistId throws BEFORE fetch', async () => {
      global.fetch = jest.fn();
      const badScope = { mode: 'cloud', playlistId: '' } as Scope;
      await expect(getQuickView(badScope, VIDEO_ID)).rejects.toThrow();
      expect(global.fetch).not.toHaveBeenCalled();
    });

    it('401 response throws UnauthorizedError', async () => {
      global.fetch = mockFetchStatus(401, { error: 'authentication required' });
      await expect(getQuickView(CLOUD_SCOPE, VIDEO_ID)).rejects.toBeInstanceOf(UnauthorizedError);
    });
  });

  describe('saveAnnotation', () => {
    it('cloud: POSTs /api/videos/<id>/review?playlist=<uuid> with the patch as body', async () => {
      global.fetch = mockFetchOk({ ok: true });
      await saveAnnotation(CLOUD_SCOPE, VIDEO_ID, { personalScore: 4 });
      expect(global.fetch).toHaveBeenCalledWith(
        `/api/videos/${VIDEO_ID}/review?playlist=${CLOUD_SCOPE.playlistId}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ personalScore: 4 }),
        },
      );
    });

    it('local: POSTs /api/videos/<id>/review with outputFolder + patch in body', async () => {
      global.fetch = mockFetchOk({ ok: true });
      await saveAnnotation(LOCAL_SCOPE, VIDEO_ID, { personalNote: 'hello' });
      expect(global.fetch).toHaveBeenCalledWith(
        `/api/videos/${VIDEO_ID}/review`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ outputFolder: LOCAL_SCOPE.outputFolder, personalNote: 'hello' }),
        },
      );
    });

    it('cloud scope with no playlistId throws BEFORE fetch', async () => {
      global.fetch = jest.fn();
      const badScope = { mode: 'cloud', playlistId: '' } as Scope;
      await expect(saveAnnotation(badScope, VIDEO_ID, { personalScore: 3 })).rejects.toThrow();
      expect(global.fetch).not.toHaveBeenCalled();
    });

    it('401 response throws UnauthorizedError', async () => {
      global.fetch = mockFetchStatus(401, { error: 'authentication required' });
      await expect(saveAnnotation(CLOUD_SCOPE, VIDEO_ID, { personalScore: 3 })).rejects.toBeInstanceOf(
        UnauthorizedError,
      );
    });
  });

  describe('setArchived', () => {
    it('cloud: POSTs /api/videos/<id>/archive?playlist=<uuid> with action:archive', async () => {
      global.fetch = mockFetchOk({ ok: true });
      await setArchived(CLOUD_SCOPE, VIDEO_ID, true);
      expect(global.fetch).toHaveBeenCalledWith(
        `/api/videos/${VIDEO_ID}/archive?playlist=${CLOUD_SCOPE.playlistId}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ action: 'archive' }),
        },
      );
    });

    it('cloud: action:unarchive when archived=false', async () => {
      global.fetch = mockFetchOk({ ok: true });
      await setArchived(CLOUD_SCOPE, VIDEO_ID, false);
      expect(global.fetch).toHaveBeenCalledWith(
        `/api/videos/${VIDEO_ID}/archive?playlist=${CLOUD_SCOPE.playlistId}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ action: 'unarchive' }),
        },
      );
    });

    it('local: POSTs /api/videos/<id>/archive with outputFolder + action in body', async () => {
      global.fetch = mockFetchOk({ ok: true });
      await setArchived(LOCAL_SCOPE, VIDEO_ID, true);
      expect(global.fetch).toHaveBeenCalledWith(
        `/api/videos/${VIDEO_ID}/archive`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ outputFolder: LOCAL_SCOPE.outputFolder, action: 'archive' }),
        },
      );
    });

    it('local scope with no outputFolder throws BEFORE fetch', async () => {
      global.fetch = jest.fn();
      const badScope = { mode: 'local', outputFolder: '', baseOutputFolder: '/tmp' } as Scope;
      await expect(setArchived(badScope, VIDEO_ID, true)).rejects.toThrow();
      expect(global.fetch).not.toHaveBeenCalled();
    });

    it('401 response throws UnauthorizedError', async () => {
      global.fetch = mockFetchStatus(401, { error: 'authentication required' });
      await expect(setArchived(CLOUD_SCOPE, VIDEO_ID, true)).rejects.toBeInstanceOf(UnauthorizedError);
    });
  });
});
