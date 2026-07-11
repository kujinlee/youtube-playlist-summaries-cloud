import { createShare, revokeShare, UnauthorizedError } from '@/lib/client/api';

const PID = 'p-uuid';
const VID = 'abc123XYZ_0';

afterEach(() => { (global.fetch as jest.Mock)?.mockReset?.(); });

function mockFetch(status: number, body: unknown) {
  global.fetch = jest.fn().mockResolvedValue({
    status, ok: status >= 200 && status < 300,
    json: async () => body,
  }) as unknown as typeof fetch;
}

test('createShare posts playlistId/videoId/ttlDays and returns id+url', async () => {
  mockFetch(201, { id: 's1', token: 'tok', url: '/s/tok', expiresAt: null });
  const res = await createShare(PID, VID, 30);
  expect(global.fetch).toHaveBeenCalledWith('/api/share', expect.objectContaining({
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ playlistId: PID, videoId: VID, ttlDays: 30 }),
  }));
  expect(res).toEqual({ id: 's1', token: 'tok', url: '/s/tok', expiresAt: null });
});

test('createShare forwards ttl "never" as ttlDays', async () => {
  mockFetch(201, { id: 's2', token: 't', url: '/s/t', expiresAt: null });
  await createShare(PID, VID, 'never');
  expect(global.fetch).toHaveBeenCalledWith('/api/share', expect.objectContaining({
    body: JSON.stringify({ playlistId: PID, videoId: VID, ttlDays: 'never' }),
  }));
});

test('createShare maps 401 → UnauthorizedError', async () => {
  mockFetch(401, { error: 'authentication required' });
  await expect(createShare(PID, VID, 7)).rejects.toBeInstanceOf(UnauthorizedError);
});

test('createShare maps non-2xx → Error(body.error)', async () => {
  mockFetch(404, { error: 'not found' });
  await expect(createShare(PID, VID, 7)).rejects.toThrow('not found');
});

test('revokeShare posts to /api/share/<id>/revoke (bodyless) and returns revoked', async () => {
  mockFetch(200, { revoked: true });
  const res = await revokeShare('s-uuid-1');
  expect(global.fetch).toHaveBeenCalledWith('/api/share/s-uuid-1/revoke', { method: 'POST' });
  expect(res).toEqual({ revoked: true });
});

test('revokeShare maps 401 → UnauthorizedError', async () => {
  mockFetch(401, { error: 'authentication required' });
  await expect(revokeShare('s1')).rejects.toBeInstanceOf(UnauthorizedError);
});
