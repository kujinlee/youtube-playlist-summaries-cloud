/** @jest-environment jsdom */
import { createIngest, getJobStatus, IngestError, ingestErrorMessage, UnauthorizedError, type IngestResult } from '@/lib/client/api';

function mockRes(status: number, body: any = {}, headers: Record<string, string> = {}) {
  return jest.fn().mockResolvedValue({
    ok: status >= 200 && status < 300, status,
    headers: { get: (k: string) => headers[k.toLowerCase()] ?? null },
    json: () => Promise.resolve(body),
  } as unknown as Response);
}

const OK: IngestResult = {
  playlistId: 'p-uuid', jobs: [], challengeRequired: false,
  counts: { enqueued: 3, joined: 0, skipped: 0, failed: 0, quotaBlocked: 0, capBlocked: 0, tooLong: 0 },
};

afterEach(() => jest.restoreAllMocks());

describe('createIngest', () => {
  it('POSTs playlistUrl and returns IngestResult on 200', async () => {
    global.fetch = mockRes(200, OK);
    const r = await createIngest('https://youtube.com/playlist?list=X');
    expect(global.fetch).toHaveBeenCalledWith('/api/jobs', expect.objectContaining({
      method: 'POST', headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ playlistUrl: 'https://youtube.com/playlist?list=X' }),
    }));
    expect(r).toEqual(OK);
  });
  it('maps 401 to UnauthorizedError', async () => {
    global.fetch = mockRes(401, { error: 'authentication required' });
    await expect(createIngest('u')).rejects.toBeInstanceOf(UnauthorizedError);
  });
  it('maps 422 to IngestError carrying limit/found', async () => {
    global.fetch = mockRes(422, { error: 'playlist too large', limit: 50, found: 80 });
    const err = await createIngest('u').catch((e) => e);
    expect(err).toBeInstanceOf(IngestError);
    expect(err.status).toBe(422); expect(err.info).toEqual({ limit: 50, found: 80 });
  });
  it('maps 429 to IngestError reading Retry-After header', async () => {
    global.fetch = mockRes(429, { error: 'rate limited' }, { 'retry-after': '60' });
    const err = await createIngest('u').catch((e) => e);
    expect(err.status).toBe(429); expect(err.info.retryAfterSeconds).toBe(60);
  });
  it('defaults Retry-After to 60 when header missing', async () => {
    global.fetch = mockRes(429, { error: 'rate limited' });
    const err = await createIngest('u').catch((e) => e);
    expect(err.info.retryAfterSeconds).toBe(60);
  });
  it.each([400, 403, 502, 503, 500])('wraps %s in IngestError', async (status) => {
    global.fetch = mockRes(status, { error: 'x' });
    const err = await createIngest('u').catch((e) => e);
    expect(err).toBeInstanceOf(IngestError); expect(err.status).toBe(status);
  });
  it('maps a 422 with a null JSON body to IngestError generic copy without crashing', async () => {
    global.fetch = mockRes(422, null);
    const err = await createIngest('u').catch((e) => e);
    expect(err).toBeInstanceOf(IngestError);
    expect(err.status).toBe(422);
    expect(err.info).toEqual({});
    expect(ingestErrorMessage(err)).toBe('That playlist is too large. Try a smaller one.');
  });
  it('ignores stringy 422 limit/found and falls back to generic copy', async () => {
    global.fetch = mockRes(422, { error: 'too large', limit: '50', found: '80' });
    const err = await createIngest('u').catch((e) => e);
    expect(err).toBeInstanceOf(IngestError);
    expect(err.info).toEqual({});
    expect(ingestErrorMessage(err)).toBe('That playlist is too large. Try a smaller one.');
  });
  it('defaults Retry-After to 60 on a malformed header', async () => {
    global.fetch = mockRes(429, { error: 'rate limited' }, { 'retry-after': 'later' });
    const err = await createIngest('u').catch((e) => e);
    expect(err.status).toBe(429);
    expect(err.info.retryAfterSeconds).toBe(60);
  });
  it('defaults Retry-After to 60 on an empty header value', async () => {
    global.fetch = mockRes(429, { error: 'rate limited' }, { 'retry-after': '' });
    const err = await createIngest('u').catch((e) => e);
    expect(err.info.retryAfterSeconds).toBe(60);
  });
  it('defaults Retry-After to 60 on a zero header value', async () => {
    global.fetch = mockRes(429, { error: 'rate limited' }, { 'retry-after': '0' });
    const err = await createIngest('u').catch((e) => e);
    expect(err.info.retryAfterSeconds).toBe(60);
  });
  it('defaults Retry-After to 60 on a negative header value', async () => {
    global.fetch = mockRes(429, { error: 'rate limited' }, { 'retry-after': '-5' });
    const err = await createIngest('u').catch((e) => e);
    expect(err.info.retryAfterSeconds).toBe(60);
  });
});

describe('ingestErrorMessage', () => {
  const msg = (status: number, info: any = {}) => ingestErrorMessage(new IngestError(status, info));
  it('400', () => expect(msg(400)).toBe('Enter a valid YouTube playlist URL.'));
  it('403', () => expect(msg(403)).toBe("This account can't ingest right now."));
  it('422', () => expect(msg(422, { limit: 50, found: 80 })).toBe('That playlist has 80 videos; the limit is 50. Try a smaller one.'));
  it('422 with missing limit/found falls back to generic', () => expect(msg(422, {})).toBe('That playlist is too large. Try a smaller one.'));
  it('429', () => expect(msg(429, { retryAfterSeconds: 60 })).toBe("You're adding playlists too quickly — try again in 60s."));
  it('502', () => expect(msg(502)).toBe("Couldn't reach YouTube for that playlist. Try again."));
  it('503', () => expect(msg(503)).toBe('The service is at capacity. Try again shortly.'));
  it('500 / unknown', () => expect(msg(500)).toBe('Something went wrong. Try again.'));
});

describe('getJobStatus', () => {
  it('GETs by playlistId and returns { jobs, rollup }', async () => {
    const payload = { jobs: [], rollup: { queued: 0, active: 0, completed: 0, failed: 0, dead_letter: 0, cancelled: 0, total: 0, terminal: false } };
    global.fetch = mockRes(200, payload);
    const r = await getJobStatus('p-uuid');
    expect(global.fetch).toHaveBeenCalledWith('/api/jobs?playlistId=p-uuid');
    expect(r).toEqual(payload);
  });
  it('maps 401 to UnauthorizedError', async () => {
    global.fetch = mockRes(401, { error: 'authentication required' });
    await expect(getJobStatus('p')).rejects.toBeInstanceOf(UnauthorizedError);
  });
  it('encodes the playlistId into the query string', async () => {
    const payload = { jobs: [], rollup: { queued: 0, active: 0, completed: 0, failed: 0, dead_letter: 0, cancelled: 0, total: 0, terminal: false } };
    global.fetch = mockRes(200, payload);
    await getJobStatus('p uuid&x=1');
    expect(global.fetch).toHaveBeenCalledWith('/api/jobs?playlistId=p%20uuid%26x%3D1');
  });
});
