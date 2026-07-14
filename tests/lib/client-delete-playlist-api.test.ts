// tests/lib/client-delete-playlist-api.test.ts
//
// Client unit coverage for lib/client/api.ts's deletePlaylist (Task 9). Mirrors the
// mockFetch pattern in tests/lib/client-share-api.test.ts.
import { deletePlaylist, UnauthorizedError } from '@/lib/client/api';

const PLAYLIST_ID = 'p-uuid-1';

afterEach(() => { (global.fetch as jest.Mock)?.mockReset?.(); });

function mockFetch(status: number, body: unknown = {}) {
  global.fetch = jest.fn().mockResolvedValue({
    status, ok: status >= 200 && status < 300,
    json: async () => body,
  }) as unknown as typeof fetch;
}

test('deletePlaylist sends DELETE to /api/playlists/<id>', async () => {
  mockFetch(200, { deleted: true });
  await deletePlaylist(PLAYLIST_ID);
  expect(global.fetch).toHaveBeenCalledWith(`/api/playlists/${PLAYLIST_ID}`, { method: 'DELETE' });
});

test('deletePlaylist resolves on 200', async () => {
  mockFetch(200, { deleted: true });
  await expect(deletePlaylist(PLAYLIST_ID)).resolves.toBeUndefined();
});

test('deletePlaylist treats 404 as success (already gone)', async () => {
  mockFetch(404, { error: 'not found' });
  await expect(deletePlaylist(PLAYLIST_ID)).resolves.toBeUndefined();
});

test('deletePlaylist maps 401 → UnauthorizedError', async () => {
  mockFetch(401, { error: 'authentication required' });
  await expect(deletePlaylist(PLAYLIST_ID)).rejects.toBeInstanceOf(UnauthorizedError);
});

test('deletePlaylist maps other non-2xx → Error(body.error)', async () => {
  mockFetch(500, { error: 'internal error' });
  await expect(deletePlaylist(PLAYLIST_ID)).rejects.toThrow('internal error');
});

test('deletePlaylist maps 501 (unsupported backend) → throws, NOT swallowed like 404', async () => {
  // review fix: the route now answers a non-supabase backend with 501 instead of 404, precisely
  // so this idempotency shortcut (404 → resolve) never masks a backend/config mistake that did
  // NOT delete anything.
  mockFetch(501, { error: 'unsupported' });
  await expect(deletePlaylist(PLAYLIST_ID)).rejects.toThrow('unsupported');
});
