jest.mock('@/lib/youtube', () => ({
  ...jest.requireActual('@/lib/youtube'),
  fetchPlaylistVideos: jest.fn(),
  fetchPlaylistTitleOrNull: jest.fn(),
}));
import * as youtube from '@/lib/youtube';
import { enqueuePlaylist } from '@/lib/job-queue/producer';
import type { VideoMeta } from '@/types';
import type { Enqueuer, EnqueueCtx, PreflightVerdict, GuardrailConfigView } from '@/lib/job-queue/enqueuer';

const fetchMock = jest.mocked(youtube.fetchPlaylistVideos);
const titleMock = jest.mocked(youtube.fetchPlaylistTitleOrNull);
const URL_ = 'https://www.youtube.com/playlist?list=PLx';
const principal = { id: 'owner-1', indexKey: 'PLx' };
const ctx: EnqueueCtx = { ownerId: 'owner-1', enqueueIp: null };

const meta = (id: string, dur = 100): VideoMeta =>
  ({ videoId: id, title: id, youtubeUrl: `https://youtu.be/${id}`, durationSeconds: dur,
     channelTitle: 'C', videoPublishedAt: '2020-01-01T00:00:00Z', addedToPlaylistAt: '2020-01-02T00:00:00Z' });

/** Fake bundle+enqueuer, mirroring tests/lib/producer.test.ts's fakeEnqueuer, plus a
 *  setPlaylistMeta spy and a shared call-order log so we can assert ordering (behavior 4). */
function fakeEnqueuer(enqueueImpl: Enqueuer['enqueue']) {
  const order: string[] = [];
  const resolvePlaylistId = jest.fn(async () => { order.push('resolve'); return 'pl-uuid'; });
  const setPlaylistMeta = jest.fn(async () => { order.push('setPlaylistMeta'); });
  const enqueue = jest.fn(enqueueImpl);
  const enqueuer: Enqueuer = {
    enqueue,
    preflight: jest.fn(async (): Promise<PreflightVerdict> =>
      ({ admitted: true, atCapacity: false, velocityExceeded: false, challengeRequired: false })),
    getGuardrailConfig: jest.fn(async (): Promise<GuardrailConfigView> => ({ maxDurationSeconds: 1800 })),
  };
  const bundle = { metadataStore: { resolvePlaylistId, setPlaylistMeta } } as any;
  return { bundle, enqueuer, resolvePlaylistId, setPlaylistMeta, enqueue, order };
}

beforeEach(() => { jest.clearAllMocks(); process.env.YOUTUBE_API_KEY = 'k'; });

it('persists the real title, called after resolvePlaylistId (behaviors 1 + 4)', async () => {
  fetchMock.mockResolvedValueOnce([meta('v1')]);
  titleMock.mockResolvedValueOnce('My List');
  const { bundle, enqueuer, setPlaylistMeta, order } = fakeEnqueuer(async () => {
    order.push('enqueue');
    return { jobId: 'j', status: 'queued', joined: false };
  });

  await enqueuePlaylist(bundle, enqueuer, principal, URL_, ctx);

  expect(titleMock).toHaveBeenCalledWith('PLx', 'k');
  expect(setPlaylistMeta).toHaveBeenCalledWith(principal, { playlistUrl: URL_, playlistTitle: 'My List' });
  expect(order.indexOf('resolve')).toBeGreaterThanOrEqual(0);
  expect(order.indexOf('resolve')).toBeLessThan(order.indexOf('setPlaylistMeta'));
});

it('does NOT persist a fake title when the fetch returns null (behavior 2)', async () => {
  fetchMock.mockResolvedValueOnce([meta('v1')]);
  titleMock.mockResolvedValueOnce(null);
  const { bundle, enqueuer, setPlaylistMeta } = fakeEnqueuer(async () =>
    ({ jobId: 'j', status: 'queued', joined: false }));

  await enqueuePlaylist(bundle, enqueuer, principal, URL_, ctx);

  expect(setPlaylistMeta).not.toHaveBeenCalled();
});

it('a title-fetch throw does not fail ingest (behavior 3)', async () => {
  fetchMock.mockResolvedValueOnce([meta('v1')]);
  titleMock.mockRejectedValueOnce(new Error('quota exceeded'));
  const { bundle, enqueuer, setPlaylistMeta } = fakeEnqueuer(async () =>
    ({ jobId: 'j', status: 'queued', joined: false }));

  const result = await enqueuePlaylist(bundle, enqueuer, principal, URL_, ctx);

  expect(result.playlistId).toBe('pl-uuid');
  expect(result.counts.enqueued).toBe(1);
  expect(setPlaylistMeta).not.toHaveBeenCalled();
});

it('the all-videos-skipped early return does no title work (behavior 5)', async () => {
  fetchMock.mockResolvedValueOnce([meta('v-skip', 0)]); // duration<=0 -> skipped pre-resolve
  const { bundle, enqueuer, resolvePlaylistId, setPlaylistMeta } = fakeEnqueuer(async () =>
    ({ jobId: 'j', status: 'queued', joined: false }));

  const result = await enqueuePlaylist(bundle, enqueuer, principal, URL_, ctx);

  expect(result.playlistId).toBeNull();
  expect(resolvePlaylistId).not.toHaveBeenCalled();
  expect(titleMock).not.toHaveBeenCalled();
  expect(setPlaylistMeta).not.toHaveBeenCalled();
});
