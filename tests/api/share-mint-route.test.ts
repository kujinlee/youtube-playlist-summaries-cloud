let mockGetUser: jest.Mock;
let mockRpc: jest.Mock;

jest.mock('next/headers', () => ({ cookies: jest.fn(async () => ({ getAll: () => [], set: () => {} })) }));
jest.mock('@/lib/supabase/server', () => ({
  createServerSupabase: jest.fn(() => ({ auth: { getUser: mockGetUser }, rpc: mockRpc })),
}));

import { POST } from '@/app/api/share/route';

const VALID_BODY = { playlistId: 'pl-1', videoId: 'vid-1' };

const post = (body: any) =>
  POST(new Request('http://x/api/share', { method: 'POST', body: JSON.stringify(body) }) as any);

beforeEach(() => {
  jest.clearAllMocks();
  mockGetUser = jest.fn(async () => ({ data: { user: { id: 'owner-1' } } }));
  mockRpc = jest.fn(async () => ({ data: new Date(Date.now() + 30 * 864e5).toISOString(), error: null }));
});

describe('POST /api/share', () => {
  it('401 when no session', async () => {
    mockGetUser.mockResolvedValueOnce({ data: { user: null } });
    const res = await post(VALID_BODY);
    expect(res.status).toBe(401);
    expect(mockRpc).not.toHaveBeenCalled();
  });

  it('201 returns { token, url, expiresAt } once; token/url shape correct; RPC called with a 64-hex-char p_token_hash', async () => {
    const res = await post(VALID_BODY);
    expect(res.status).toBe(201);
    const body = await res.json();

    expect(body.token).toMatch(/^[A-Za-z0-9_-]{43}$/);
    expect(body.url).toBe(`/s/${body.token}`);
    expect(typeof body.expiresAt).toBe('string');

    expect(mockRpc).toHaveBeenCalledTimes(1);
    const [rpcName, rpcArgs] = mockRpc.mock.calls[0];
    expect(rpcName).toBe('create_share_token');
    expect(rpcArgs.p_playlist_id).toBe(VALID_BODY.playlistId);
    expect(rpcArgs.p_video_id).toBe(VALID_BODY.videoId);
    expect(rpcArgs.p_token_hash).toMatch(/^[0-9a-f]{64}$/);
    expect(rpcArgs.p_token_hash).toHaveLength(64);

    // plaintext token is present only in this response body, never in the RPC args.
    expect(rpcArgs.p_token_hash).not.toBe(body.token);
  });

  it.each([0, -1, 366, 3.5])('400 when ttlDays is out of range (%p)', async (ttlDays) => {
    const res = await post({ ...VALID_BODY, ttlDays });
    expect(res.status).toBe(400);
    expect(mockRpc).not.toHaveBeenCalled();
  });

  it('404 (coarse) when the RPC raises (unowned/unpromoted/bounds)', async () => {
    mockRpc.mockResolvedValueOnce({ data: null, error: { message: 'denied' } });
    const res = await post(VALID_BODY);
    expect(res.status).toBe(404);
  });
});
