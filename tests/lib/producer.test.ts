jest.mock('@/lib/youtube', () => ({
  ...jest.requireActual('@/lib/youtube'),
  fetchPlaylistVideos: jest.fn(),
}));
import * as youtube from '@/lib/youtube';
import { enqueuePlaylist, PlaylistTooLargeError, AllEnqueueFailedError, MAX_VIDEOS_PER_ENQUEUE } from '@/lib/job-queue/producer';
import type { VideoMeta } from '@/types';

const fetchMock = jest.mocked(youtube.fetchPlaylistVideos);
const URL_ = 'https://www.youtube.com/playlist?list=PLx';
const principal = { id: 'owner-1', indexKey: 'PLx' };

const meta = (id: string, dur = 100): VideoMeta =>
  ({ videoId: id, title: id, youtubeUrl: `https://youtu.be/${id}`, durationSeconds: dur,
     channelTitle: 'C', videoPublishedAt: '2020-01-01T00:00:00Z', addedToPlaylistAt: '2020-01-02T00:00:00Z' });

function fakeBundle(enqueueImpl: any) {
  const resolvePlaylistId = jest.fn(async () => 'pl-uuid');
  const enqueue = jest.fn(enqueueImpl);
  return { bundle: { metadataStore: { resolvePlaylistId }, jobQueue: { enqueue } } as any, resolvePlaylistId, enqueue };
}
beforeEach(() => { jest.clearAllMocks(); process.env.YOUTUBE_API_KEY = 'k'; });

it('rejects an over-cap playlist before resolving the playlist id', async () => {
  fetchMock.mockResolvedValueOnce(Array.from({ length: 51 }, (_, i) => meta(`v${i}`)));
  const { bundle, resolvePlaylistId } = fakeBundle(async () => ({ jobId: 'j', status: 'queued', joined: false }));
  await expect(enqueuePlaylist(bundle, principal, URL_)).rejects.toBeInstanceOf(PlaylistTooLargeError);
  expect(resolvePlaylistId).not.toHaveBeenCalled();
  expect(fetchMock).toHaveBeenCalledWith(URL_, 'k', { maxItems: MAX_VIDEOS_PER_ENQUEUE + 1 });
});

it('empty and all-skipped short-circuit with playlistId:null and no resolve', async () => {
  fetchMock.mockResolvedValueOnce([]);
  const { bundle, resolvePlaylistId } = fakeBundle(async () => ({ jobId: 'j', status: 'queued', joined: false }));
  const r = await enqueuePlaylist(bundle, principal, URL_);
  expect(r.playlistId).toBeNull(); expect(r.counts.enqueued).toBe(0);
  expect(resolvePlaylistId).not.toHaveBeenCalled();

  fetchMock.mockResolvedValueOnce([meta('v1', 0), meta('v2', 0)]);
  const r2 = await enqueuePlaylist(bundle, principal, URL_);
  expect(r2.playlistId).toBeNull(); expect(r2.counts.skipped).toBe(2);
  expect(resolvePlaylistId).not.toHaveBeenCalled();
});

it('fans out, counts disjointly, and joined does not count as enqueued', async () => {
  fetchMock.mockResolvedValueOnce([meta('v1'), meta('v2'), meta('v3', 0)]); // v3 skipped
  const { bundle, enqueue } = fakeBundle(async (key: any) =>
    key.videoId === 'v2' ? { jobId: 'j2', status: 'queued', joined: true } : { jobId: 'j1', status: 'queued', joined: false });
  const r = await enqueuePlaylist(bundle, principal, URL_);
  expect(r.playlistId).toBe('pl-uuid');
  expect(r.counts).toEqual({ enqueued: 1, joined: 1, skipped: 1, failed: 0 });
  expect(r.counts.enqueued + r.counts.joined + r.counts.skipped + r.counts.failed).toBe(3);
  expect(enqueue).toHaveBeenCalledWith(
    expect.objectContaining({ playlistId: 'pl-uuid', videoId: 'v1', sectionId: -1, kind: 'summary', version: '3.3' }),
    expect.anything());
});

it('throws AllEnqueueFailedError when every enqueue fails', async () => {
  fetchMock.mockResolvedValueOnce([meta('v1'), meta('v2')]);
  const { bundle } = fakeBundle(async () => { throw new Error('db down'); });
  await expect(enqueuePlaylist(bundle, principal, URL_)).rejects.toBeInstanceOf(AllEnqueueFailedError);

  fetchMock.mockResolvedValueOnce([meta('v1'), meta('v2')]);
  const { bundle: bundle2 } = fakeBundle(async () => { throw new Error('db down'); });
  let caught: unknown;
  try { await enqueuePlaylist(bundle2, principal, URL_); } catch (e) { caught = e; }
  expect((caught as AllEnqueueFailedError).playlistId).toBe('pl-uuid');   // review Minor — error must carry the playlistId
});

it('mixed 4-bucket input yields exact disjoint counts summing to videos.length', async () => {   // review convergent — disjointness invariant
  fetchMock.mockResolvedValueOnce([
    meta('v-new'),       // will be newly enqueued (joined:false)
    meta('v-join'),      // will join an existing job (joined:true)
    meta('v-skip', 0),   // duration<=0 -> skipped before reaching the queue
    meta('v-fail'),       // enqueue throws -> failed
  ]);
  const { bundle } = fakeBundle(async (key: any) => {
    if (key.videoId === 'v-join') return { jobId: 'j-join', status: 'queued', joined: true };
    if (key.videoId === 'v-fail') throw new Error('boom');
    return { jobId: 'j-new', status: 'queued', joined: false };
  });
  const r = await enqueuePlaylist(bundle, principal, URL_);
  expect(r.counts).toEqual({ enqueued: 1, joined: 1, skipped: 1, failed: 1 });
  expect(r.counts.enqueued + r.counts.joined + r.counts.skipped + r.counts.failed).toBe(4);
});

it('best-effort: one failed enqueue does not stop the rest', async () => {
  fetchMock.mockResolvedValueOnce([meta('v1'), meta('v2')]);
  const { bundle } = fakeBundle(async (key: any) => {
    if (key.videoId === 'v1') throw new Error('boom: raw db secret');
    return { jobId: 'j2', status: 'queued', joined: false };
  });
  const r = await enqueuePlaylist(bundle, principal, URL_);
  expect(r.counts).toEqual({ enqueued: 1, joined: 0, skipped: 0, failed: 1 });
  const failedEntry = r.jobs.find((j: any) => j.videoId === 'v1');
  expect(failedEntry).toEqual({ videoId: 'v1', error: 'enqueue failed' });   // review High — no raw error leak
});

it('a fully-idempotent re-submit (all joined) is NOT a false 503', async () => {   // review L2
  fetchMock.mockResolvedValueOnce([meta('v1'), meta('v2')]);
  const { bundle } = fakeBundle(async () => ({ jobId: 'j', status: 'completed', joined: true }));
  const r = await enqueuePlaylist(bundle, principal, URL_);
  expect(r.counts).toEqual({ enqueued: 0, joined: 2, skipped: 0, failed: 0 });
});

it('resolvePlaylistId failure aborts before any enqueue', async () => {   // review L2
  fetchMock.mockResolvedValueOnce([meta('v1')]);
  const enqueue = jest.fn();
  const bundle = { metadataStore: { resolvePlaylistId: jest.fn(async () => { throw new Error('db'); }) },
                   jobQueue: { enqueue } } as any;
  await expect(enqueuePlaylist(bundle, principal, URL_)).rejects.toThrow('db');
  expect(enqueue).not.toHaveBeenCalled();
});

it('throws when the bundle has no jobQueue (misconfigured/local)', async () => {   // review High
  const resolvePlaylistId = jest.fn();
  const bundle = { metadataStore: { resolvePlaylistId } } as any;  // no jobQueue
  await expect(enqueuePlaylist(bundle, principal, URL_)).rejects.toThrow(/jobQueue/);
  expect(resolvePlaylistId).not.toHaveBeenCalled();
});

it('throws when jobQueue is present but broken (no enqueue fn) — proves no orphan playlist write', async () => {   // review High + convergent test gap
  // No fetchMock.mockResolvedValueOnce here: the fixed guard must throw before fetch is ever
  // reached. (jest.clearAllMocks() does not drain queued *Once implementations, so leaving an
  // unconsumed mock here would leak into the next test.)
  const resolvePlaylistId = jest.fn(async () => 'pl-uuid');
  const bundle = { metadataStore: { resolvePlaylistId }, jobQueue: {} } as any;  // present-but-broken queue
  await expect(enqueuePlaylist(bundle, principal, URL_)).rejects.toThrow(/jobQueue/);
  expect(resolvePlaylistId).not.toHaveBeenCalled();
  expect(fetchMock).not.toHaveBeenCalled();
});

it('wraps a fetch failure in PlaylistFetchError', async () => {   // review Blocking (502 mapping)
  fetchMock.mockRejectedValueOnce(new Error('quota exceeded'));
  const { bundle } = fakeBundle(async () => ({ jobId: 'j', status: 'queued', joined: false }));
  const { PlaylistFetchError } = await import('@/lib/job-queue/producer');
  await expect(enqueuePlaylist(bundle, principal, URL_)).rejects.toBeInstanceOf(PlaylistFetchError);
});
