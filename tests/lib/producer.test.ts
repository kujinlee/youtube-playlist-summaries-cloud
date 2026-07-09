jest.mock('@/lib/youtube', () => ({
  ...jest.requireActual('@/lib/youtube'),
  fetchPlaylistVideos: jest.fn(),
}));
import * as youtube from '@/lib/youtube';
import { enqueuePlaylist, PlaylistTooLargeError, AllEnqueueFailedError, MAX_VIDEOS_PER_ENQUEUE } from '@/lib/job-queue/producer';
import type { VideoMeta } from '@/types';
import type { Enqueuer, EnqueueCtx, PreflightVerdict, GuardrailConfigView } from '@/lib/job-queue/enqueuer';

const fetchMock = jest.mocked(youtube.fetchPlaylistVideos);
const URL_ = 'https://www.youtube.com/playlist?list=PLx';
const principal = { id: 'owner-1', indexKey: 'PLx' };
const ctx: EnqueueCtx = { ownerId: 'owner-1', enqueueIp: null };

const meta = (id: string, dur = 100): VideoMeta =>
  ({ videoId: id, title: id, youtubeUrl: `https://youtu.be/${id}`, durationSeconds: dur,
     channelTitle: 'C', videoPublishedAt: '2020-01-01T00:00:00Z', addedToPlaylistAt: '2020-01-02T00:00:00Z' });

/** Fake Enqueuer implementing the full interface; getGuardrailConfig defaults to a
 *  high cap so existing duration-100 fixtures never trip the too_long pre-block. */
function fakeEnqueuer(enqueueImpl: Enqueuer['enqueue']) {
  const resolvePlaylistId = jest.fn(async () => 'pl-uuid');
  const enqueue = jest.fn(enqueueImpl);
  const enqueuer: Enqueuer = {
    enqueue,
    preflight: jest.fn(async (): Promise<PreflightVerdict> =>
      ({ admitted: true, atCapacity: false, velocityExceeded: false, challengeRequired: false })),
    getGuardrailConfig: jest.fn(async (): Promise<GuardrailConfigView> => ({ maxDurationSeconds: 1800 })),
  };
  const bundle = { metadataStore: { resolvePlaylistId } } as any;
  return { bundle, enqueuer, resolvePlaylistId, enqueue };
}
beforeEach(() => { jest.clearAllMocks(); process.env.YOUTUBE_API_KEY = 'k'; });

it('rejects an over-cap playlist before resolving the playlist id', async () => {
  fetchMock.mockResolvedValueOnce(Array.from({ length: 51 }, (_, i) => meta(`v${i}`)));
  const { bundle, enqueuer, resolvePlaylistId } = fakeEnqueuer(async () => ({ jobId: 'j', status: 'queued', joined: false }));
  await expect(enqueuePlaylist(bundle, enqueuer, principal, URL_, ctx)).rejects.toBeInstanceOf(PlaylistTooLargeError);
  expect(resolvePlaylistId).not.toHaveBeenCalled();
  expect(fetchMock).toHaveBeenCalledWith(URL_, 'k', { maxItems: MAX_VIDEOS_PER_ENQUEUE + 1 });
});

it('empty and all-skipped short-circuit with playlistId:null and no resolve', async () => {
  fetchMock.mockResolvedValueOnce([]);
  const { bundle, enqueuer, resolvePlaylistId } = fakeEnqueuer(async () => ({ jobId: 'j', status: 'queued', joined: false }));
  const r = await enqueuePlaylist(bundle, enqueuer, principal, URL_, ctx);
  expect(r.playlistId).toBeNull(); expect(r.counts.enqueued).toBe(0);
  expect(resolvePlaylistId).not.toHaveBeenCalled();

  fetchMock.mockResolvedValueOnce([meta('v1', 0), meta('v2', 0)]);
  const r2 = await enqueuePlaylist(bundle, enqueuer, principal, URL_, ctx);
  expect(r2.playlistId).toBeNull(); expect(r2.counts.skipped).toBe(2);
  expect(resolvePlaylistId).not.toHaveBeenCalled();
});

it('fans out, counts disjointly, and joined does not count as enqueued', async () => {
  fetchMock.mockResolvedValueOnce([meta('v1'), meta('v2'), meta('v3', 0)]); // v3 skipped
  const { bundle, enqueuer, enqueue } = fakeEnqueuer(async (_ctx: any, key: any) =>
    key.videoId === 'v2' ? { jobId: 'j2', status: 'queued', joined: true } : { jobId: 'j1', status: 'queued', joined: false });
  const r = await enqueuePlaylist(bundle, enqueuer, principal, URL_, ctx);
  expect(r.playlistId).toBe('pl-uuid');
  expect(r.counts).toEqual({ enqueued: 1, joined: 1, skipped: 1, failed: 0, quotaBlocked: 0, capBlocked: 0, tooLong: 0 });
  expect(r.counts.enqueued + r.counts.joined + r.counts.skipped + r.counts.failed
    + r.counts.quotaBlocked + r.counts.capBlocked + r.counts.tooLong).toBe(3);
  expect(enqueue).toHaveBeenCalledWith(
    ctx,
    expect.objectContaining({ playlistId: 'pl-uuid', videoId: 'v1', sectionId: -1, kind: 'summary', version: '3.3' }),
    expect.anything());
});

it('throws AllEnqueueFailedError when every enqueue fails', async () => {
  fetchMock.mockResolvedValueOnce([meta('v1'), meta('v2')]);
  const { bundle, enqueuer } = fakeEnqueuer(async () => { throw new Error('db down'); });
  await expect(enqueuePlaylist(bundle, enqueuer, principal, URL_, ctx)).rejects.toBeInstanceOf(AllEnqueueFailedError);

  fetchMock.mockResolvedValueOnce([meta('v1'), meta('v2')]);
  const { bundle: bundle2, enqueuer: enqueuer2 } = fakeEnqueuer(async () => { throw new Error('db down'); });
  let caught: unknown;
  try { await enqueuePlaylist(bundle2, enqueuer2, principal, URL_, ctx); } catch (e) { caught = e; }
  expect((caught as AllEnqueueFailedError).playlistId).toBe('pl-uuid');   // review Minor — error must carry the playlistId
});

it('mixed 7-bucket-shaped input yields exact disjoint counts summing to videos.length', async () => {   // review convergent — disjointness invariant
  fetchMock.mockResolvedValueOnce([
    meta('v-new'),       // will be newly enqueued (joined:false)
    meta('v-join'),      // will join an existing job (joined:true)
    meta('v-skip', 0),   // duration<=0 -> skipped before reaching the queue
    meta('v-fail'),       // enqueue throws -> failed
  ]);
  const { bundle, enqueuer } = fakeEnqueuer(async (_ctx: any, key: any) => {
    if (key.videoId === 'v-join') return { jobId: 'j-join', status: 'queued', joined: true };
    if (key.videoId === 'v-fail') throw new Error('boom');
    return { jobId: 'j-new', status: 'queued', joined: false };
  });
  const r = await enqueuePlaylist(bundle, enqueuer, principal, URL_, ctx);
  expect(r.counts).toEqual({ enqueued: 1, joined: 1, skipped: 1, failed: 1, quotaBlocked: 0, capBlocked: 0, tooLong: 0 });
  expect(r.counts.enqueued + r.counts.joined + r.counts.skipped + r.counts.failed
    + r.counts.quotaBlocked + r.counts.capBlocked + r.counts.tooLong).toBe(4);
});

it('best-effort: one failed enqueue does not stop the rest', async () => {
  fetchMock.mockResolvedValueOnce([meta('v1'), meta('v2')]);
  const { bundle, enqueuer } = fakeEnqueuer(async (_ctx: any, key: any) => {
    if (key.videoId === 'v1') throw new Error('boom: raw db secret');
    return { jobId: 'j2', status: 'queued', joined: false };
  });
  const r = await enqueuePlaylist(bundle, enqueuer, principal, URL_, ctx);
  expect(r.counts).toEqual({ enqueued: 1, joined: 0, skipped: 0, failed: 1, quotaBlocked: 0, capBlocked: 0, tooLong: 0 });
  const failedEntry = r.jobs.find((j: any) => j.videoId === 'v1');
  expect(failedEntry).toEqual({ videoId: 'v1', error: 'enqueue failed' });   // review High — no raw error leak
});

it('a fully-idempotent re-submit (all joined) is NOT a false 503', async () => {   // review L2
  fetchMock.mockResolvedValueOnce([meta('v1'), meta('v2')]);
  const { bundle, enqueuer } = fakeEnqueuer(async () => ({ jobId: 'j', status: 'completed', joined: true }));
  const r = await enqueuePlaylist(bundle, enqueuer, principal, URL_, ctx);
  expect(r.counts).toEqual({ enqueued: 0, joined: 2, skipped: 0, failed: 0, quotaBlocked: 0, capBlocked: 0, tooLong: 0 });
});

it('resolvePlaylistId failure aborts before any enqueue', async () => {   // review L2
  fetchMock.mockResolvedValueOnce([meta('v1')]);
  const enqueue = jest.fn();
  const enqueuer: Enqueuer = {
    enqueue,
    preflight: jest.fn(async (): Promise<PreflightVerdict> =>
      ({ admitted: true, atCapacity: false, velocityExceeded: false, challengeRequired: false })),
    getGuardrailConfig: jest.fn(async (): Promise<GuardrailConfigView> => ({ maxDurationSeconds: 1800 })),
  };
  const bundle = { metadataStore: { resolvePlaylistId: jest.fn(async () => { throw new Error('db'); }) } } as any;
  await expect(enqueuePlaylist(bundle, enqueuer, principal, URL_, ctx)).rejects.toThrow('db');
  expect(enqueue).not.toHaveBeenCalled();
});

it('wraps a fetch failure in PlaylistFetchError', async () => {   // review Blocking (502 mapping)
  fetchMock.mockRejectedValueOnce(new Error('quota exceeded'));
  const { bundle, enqueuer } = fakeEnqueuer(async () => ({ jobId: 'j', status: 'queued', joined: false }));
  const { PlaylistFetchError } = await import('@/lib/job-queue/producer');
  await expect(enqueuePlaylist(bundle, enqueuer, principal, URL_, ctx)).rejects.toBeInstanceOf(PlaylistFetchError);
});
