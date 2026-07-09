import { QuotaExceededError, DailyCapError, VideoTooLongError } from '@/lib/job-queue/errors';
import type { Enqueuer, EnqueueCtx, PreflightVerdict, GuardrailConfigView } from '@/lib/job-queue/enqueuer';

jest.mock('@/lib/youtube', () => ({
  ...jest.requireActual('@/lib/youtube'),
  fetchPlaylistVideos: jest.fn(),
}));
import * as youtube from '@/lib/youtube';
import { enqueuePlaylist } from '@/lib/job-queue/producer';
import type { VideoMeta } from '@/types';

const fetchMock = jest.mocked(youtube.fetchPlaylistVideos);
const URL_ = 'https://www.youtube.com/playlist?list=PLx';
const principal = { id: 'owner-1', indexKey: 'PLx' };
const ctx: EnqueueCtx = { ownerId: 'owner-1', enqueueIp: '1.2.3.4' };
const MAX_DURATION = 1800;

const meta = (id: string, opts: Partial<VideoMeta> = {}): VideoMeta => ({
  videoId: id, title: id, youtubeUrl: `https://youtu.be/${id}`, durationSeconds: 100,
  channelTitle: 'C', videoPublishedAt: '2020-01-01T00:00:00Z', addedToPlaylistAt: '2020-01-02T00:00:00Z',
  ...opts,
});

/** Fake Enqueuer implementing the full interface; enqueueImpl drives .enqueue's behavior. */
function fakeEnqueuer(enqueueImpl: (ctx: EnqueueCtx, key: any, payload: any) => Promise<any>): {
  bundle: any; enqueuer: Enqueuer; resolvePlaylistId: jest.Mock; enqueue: jest.Mock;
} {
  const resolvePlaylistId = jest.fn(async () => 'pl-uuid');
  const enqueue = jest.fn(enqueueImpl);
  const enqueuer: Enqueuer = {
    enqueue,
    preflight: jest.fn(async (): Promise<PreflightVerdict> =>
      ({ admitted: true, atCapacity: false, velocityExceeded: false, challengeRequired: false })),
    getGuardrailConfig: jest.fn(async (): Promise<GuardrailConfigView> => ({ maxDurationSeconds: MAX_DURATION })),
  };
  const bundle = { metadataStore: { resolvePlaylistId } } as any;
  return { bundle, enqueuer, resolvePlaylistId, enqueue };
}

beforeEach(() => { jest.clearAllMocks(); process.env.YOUTUBE_API_KEY = 'k'; });

it('blocks an over-duration video as too_long, never calling enqueue for it', async () => {
  fetchMock.mockResolvedValueOnce([meta('v-long', { durationSeconds: MAX_DURATION + 1 })]);
  const { bundle, enqueuer, enqueue } = fakeEnqueuer(async () => ({ jobId: 'j', status: 'queued', joined: false }));
  const r = await enqueuePlaylist(bundle, enqueuer, principal, URL_, ctx);
  expect(r.counts.tooLong).toBe(1);
  expect(r.jobs).toContainEqual({ videoId: 'v-long', blocked: 'too_long' });
  expect(enqueue).not.toHaveBeenCalled();
  expect(r.counts.enqueued + r.counts.joined + r.counts.skipped + r.counts.failed
    + r.counts.quotaBlocked + r.counts.capBlocked + r.counts.tooLong).toBe(1);
});

it('blocks a live-broadcast video as too_long, never calling enqueue for it', async () => {
  fetchMock.mockResolvedValueOnce([meta('v-live', { liveBroadcastContent: 'live' })]);
  const { bundle, enqueuer, enqueue } = fakeEnqueuer(async () => ({ jobId: 'j', status: 'queued', joined: false }));
  const r = await enqueuePlaylist(bundle, enqueuer, principal, URL_, ctx);
  expect(r.counts.tooLong).toBe(1);
  expect(r.jobs).toContainEqual({ videoId: 'v-live', blocked: 'too_long' });
  expect(enqueue).not.toHaveBeenCalled();
});

it('blocks an upcoming-broadcast video as too_long, never calling enqueue for it', async () => {
  fetchMock.mockResolvedValueOnce([meta('v-upcoming', { liveBroadcastContent: 'upcoming' })]);
  const { bundle, enqueuer, enqueue } = fakeEnqueuer(async () => ({ jobId: 'j', status: 'queued', joined: false }));
  const r = await enqueuePlaylist(bundle, enqueuer, principal, URL_, ctx);
  expect(r.counts.tooLong).toBe(1);
  expect(r.jobs).toContainEqual({ videoId: 'v-upcoming', blocked: 'too_long' });
  expect(enqueue).not.toHaveBeenCalled();
});

it('does NOT block a video with liveBroadcastContent absent or "none"', async () => {
  fetchMock.mockResolvedValueOnce([
    meta('v-absent'), // liveBroadcastContent undefined
    meta('v-none', { liveBroadcastContent: 'none' }),
  ]);
  const { bundle, enqueuer, enqueue } = fakeEnqueuer(async () => ({ jobId: 'j', status: 'queued', joined: false }));
  const r = await enqueuePlaylist(bundle, enqueuer, principal, URL_, ctx);
  expect(r.counts.tooLong).toBe(0);
  expect(r.counts.enqueued).toBe(2);
  expect(enqueue).toHaveBeenCalledTimes(2);
});

it('quota exhausts mid-list: per-video quota_exceeded, remaining videos still attempt enqueue', async () => {
  fetchMock.mockResolvedValueOnce([meta('v1'), meta('v2'), meta('v3')]);
  const { bundle, enqueuer, enqueue } = fakeEnqueuer(async (_ctx, key) => {
    if (key.videoId === 'v2') throw new QuotaExceededError();
    return { jobId: 'j', status: 'queued', joined: false };
  });
  const r = await enqueuePlaylist(bundle, enqueuer, principal, URL_, ctx);
  expect(r.counts.quotaBlocked).toBe(1);
  expect(r.counts.enqueued).toBe(2);
  expect(r.jobs).toContainEqual({ videoId: 'v2', blocked: 'quota_exceeded' });
  expect(enqueue).toHaveBeenCalledTimes(3); // v3 still attempted after v2's quota block
  expect(r.counts.enqueued + r.counts.joined + r.counts.skipped + r.counts.failed
    + r.counts.quotaBlocked + r.counts.capBlocked + r.counts.tooLong).toBe(3);
});

it('DailyCapError mid-loop blocks that video and all remaining as daily_cap; sets dailyCapReached', async () => {
  fetchMock.mockResolvedValueOnce([meta('v1'), meta('v2'), meta('v3'), meta('v4')]);
  const { bundle, enqueuer, enqueue } = fakeEnqueuer(async (_ctx, key) => {
    if (key.videoId === 'v2') throw new DailyCapError();
    return { jobId: 'j', status: 'queued', joined: false };
  });
  const r = await enqueuePlaylist(bundle, enqueuer, principal, URL_, ctx);
  expect(r.counts.capBlocked).toBe(3); // v2, v3, v4
  expect(r.counts.enqueued).toBe(1); // v1
  expect(r.dailyCapReached).toBe(true);
  expect(r.jobs).toContainEqual({ videoId: 'v2', blocked: 'daily_cap' });
  expect(r.jobs).toContainEqual({ videoId: 'v3', blocked: 'daily_cap' });
  expect(r.jobs).toContainEqual({ videoId: 'v4', blocked: 'daily_cap' });
  expect(enqueue).toHaveBeenCalledTimes(2); // v1, v2 — v3/v4 never attempted (cap short-circuits)
  expect(r.counts.enqueued + r.counts.joined + r.counts.skipped + r.counts.failed
    + r.counts.quotaBlocked + r.counts.capBlocked + r.counts.tooLong).toBe(4);
});

it('enqueue receives ctx {ownerId, enqueueIp}', async () => {
  fetchMock.mockResolvedValueOnce([meta('v1')]);
  const { bundle, enqueuer, enqueue } = fakeEnqueuer(async () => ({ jobId: 'j', status: 'queued', joined: false }));
  await enqueuePlaylist(bundle, enqueuer, principal, URL_, ctx);
  expect(enqueue).toHaveBeenCalledWith(
    { ownerId: 'owner-1', enqueueIp: '1.2.3.4' },
    expect.objectContaining({ videoId: 'v1' }),
    expect.anything(),
  );
});

it('PJ003 backstop firing inside the RPC (duration passes producer check) counts toward tooLong', async () => {
  fetchMock.mockResolvedValueOnce([meta('v1', { durationSeconds: 100 })]); // well under MAX_DURATION
  const { bundle, enqueuer, enqueue } = fakeEnqueuer(async () => { throw new VideoTooLongError(); });
  const r = await enqueuePlaylist(bundle, enqueuer, principal, URL_, ctx);
  expect(enqueue).toHaveBeenCalledTimes(1); // producer's own check let it through
  expect(r.counts.tooLong).toBe(1);
  expect(r.jobs).toContainEqual({ videoId: 'v1', blocked: 'too_long' });
  expect(r.counts.enqueued + r.counts.joined + r.counts.skipped + r.counts.failed
    + r.counts.quotaBlocked + r.counts.capBlocked + r.counts.tooLong).toBe(1);
});

it('disjoint-sum invariant holds across a full mixed-bucket scenario', async () => {
  fetchMock.mockResolvedValueOnce([
    meta('v-new'),                                              // enqueued
    meta('v-join'),                                              // joined
    meta('v-skip', { durationSeconds: 0 }),                      // skipped (pre-payload-mapping)
    meta('v-fail'),                                               // failed (generic error)
    meta('v-quota'),                                              // quotaBlocked
    meta('v-toolong', { durationSeconds: MAX_DURATION + 1 }),     // tooLong (pre-block)
    meta('v-live', { liveBroadcastContent: 'live' }),             // tooLong (pre-block)
  ]);
  const { bundle, enqueuer } = fakeEnqueuer(async (_ctx, key) => {
    if (key.videoId === 'v-join') return { jobId: 'j', status: 'queued', joined: true };
    if (key.videoId === 'v-fail') throw new Error('boom');
    if (key.videoId === 'v-quota') throw new QuotaExceededError();
    return { jobId: 'j', status: 'queued', joined: false };
  });
  const r = await enqueuePlaylist(bundle, enqueuer, principal, URL_, ctx);
  const { enqueued, joined, skipped, failed, quotaBlocked, capBlocked, tooLong } = r.counts;
  expect(enqueued + joined + skipped + failed + quotaBlocked + capBlocked + tooLong).toBe(7);
  expect(enqueued).toBe(1);
  expect(joined).toBe(1);
  expect(skipped).toBe(1);
  expect(failed).toBe(1);
  expect(quotaBlocked).toBe(1);
  expect(tooLong).toBe(2);
  expect(capBlocked).toBe(0);
});

it('does not throw AllEnqueueFailedError when every enqueueable item is guardrail-blocked (not errored)', async () => {
  fetchMock.mockResolvedValueOnce([meta('v1', { durationSeconds: MAX_DURATION + 1 })]);
  const { bundle, enqueuer } = fakeEnqueuer(async () => ({ jobId: 'j', status: 'queued', joined: false }));
  const r = await enqueuePlaylist(bundle, enqueuer, principal, URL_, ctx);
  expect(r.counts.tooLong).toBe(1);
  expect(r.counts.failed).toBe(0);
  expect(r.playlistId).toBe('pl-uuid');
});
