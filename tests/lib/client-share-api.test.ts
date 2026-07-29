import { createShare, revokeShare, warmSummaryModel, UnauthorizedError } from '@/lib/client/api';

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

// warmSummaryModel (backlog #14): best-effort pre-warm of the owner's rendered magazine model so a
// freshly-minted share link serves immediately. Hits the SAME owner-charged serve path a normal HTML
// view uses; never throws / never redirects (advisory — the link heals on the owner's next view).
test('warmSummaryModel GETs the owner summary serve URL (playlist + type=summary, no download/format)', async () => {
  mockFetch(200, '<html></html>');
  await warmSummaryModel(PID, VID);
  const url = (global.fetch as jest.Mock).mock.calls[0][0] as string;
  expect(url).toBe(`/api/html/${encodeURIComponent(VID)}?playlist=${PID}&type=summary`);
});

test('warmSummaryModel returns true on a 2xx (model materialized)', async () => {
  mockFetch(200, '');
  await expect(warmSummaryModel(PID, VID)).resolves.toBe(true);
});

test('warmSummaryModel swallows a non-2xx response → false, never throws (budget/transient/401)', async () => {
  for (const status of [402, 401, 500, 503]) {
    mockFetch(status, { error: 'nope' });
    await expect(warmSummaryModel(PID, VID)).resolves.toBe(false);
  }
});

test('warmSummaryModel swallows a network error → false, never throws', async () => {
  global.fetch = jest.fn().mockRejectedValue(new Error('offline')) as unknown as typeof fetch;
  await expect(warmSummaryModel(PID, VID)).resolves.toBe(false);
});

test('warmSummaryModel aborts a hung warm after the timeout → false (dialog can never freeze)', async () => {
  jest.useFakeTimers();
  // A fetch that never resolves on its own — it only settles when the AbortController fires.
  global.fetch = jest.fn((_url: string, init?: { signal?: AbortSignal }) =>
    new Promise((_resolve, reject) => {
      init?.signal?.addEventListener('abort', () => reject(new DOMException('aborted', 'AbortError')));
    }),
  ) as unknown as typeof fetch;
  const p = warmSummaryModel(PID, VID);
  jest.advanceTimersByTime(15_000); // reach WARM_MODEL_TIMEOUT_MS → controller.abort()
  await expect(p).resolves.toBe(false);
  // fetch received an AbortSignal (the timeout seam)
  expect((global.fetch as jest.Mock).mock.calls[0][1]).toEqual(expect.objectContaining({ signal: expect.anything() }));
  jest.useRealTimers();
});
