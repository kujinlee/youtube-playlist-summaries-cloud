jest.mock('@/lib/html-doc/serve-summary-core', () => ({ loadSummaryForServe: jest.fn() }));
import { enqueueDig } from '@/lib/dig/cloud/enqueue-dig-core';
import { loadSummaryForServe } from '@/lib/html-doc/serve-summary-core';
import { QuotaExceededError, DailyCapError, VideoTooLongError } from '@/lib/job-queue/errors';
import { digSectionKey } from '@/lib/dig/cloud/dig-blob-key';

const SUMMARY_MD = `# T

## 2. Encoder
▶ [2:12–2:20](https://youtu.be/vid1?t=132s)
Prose.
`;
const okLoad = (existsResult: boolean, existsFn?: jest.Mock) => ({
  ok: true, mdBytes: Buffer.from(SUMMARY_MD, 'utf-8'), base: '0007_intro',
  principal: { id: 'u1', indexKey: 'PLk' },
  bundle: { blobStore: { exists: existsFn ?? jest.fn(async () => existsResult) } },
  video: { id: 'vid1', durationSeconds: 600, youtubeUrl: 'https://youtu.be/vid1', title: 'T', language: 'en' },
  playlistId: 'pl', mdKey: '0007_intro.md',
});
const enqueuer = {
  preflight: jest.fn(async () => ({ admitted: true, atCapacity: false, velocityExceeded: false, challengeRequired: false })),
  enqueue: jest.fn(async () => ({ jobId: 'job1', status: 'queued', joined: false })),
  getGuardrailConfig: jest.fn(),
};
const base = { supabase: {} as any, enqueuer: enqueuer as any, userId: 'u1', isAnonymous: false, videoId: 'vid1', playlistId: 'pl', sectionId: 132, enqueueIp: null };
beforeEach(() => jest.clearAllMocks());

it('202 enqueued when absent (charges once)', async () => {
  (loadSummaryForServe as jest.Mock).mockResolvedValue(okLoad(false));
  const r = await enqueueDig(base);
  expect(r.status).toBe(202);
  expect(r.body).toEqual({ status: 'enqueued', jobId: 'job1', sectionId: 132 });
  expect(enqueuer.enqueue).toHaveBeenCalledWith(
    { ownerId: 'u1', enqueueIp: null },
    expect.objectContaining({ kind: 'dig', sectionId: 132, version: expect.stringMatching(/^dig-/) }),
    { durationSeconds: 600 },
  );
});
it('200 ready when the current-version blob exists (no enqueue, no charge)', async () => {
  (loadSummaryForServe as jest.Mock).mockResolvedValue(okLoad(true));
  const r = await enqueueDig(base);
  expect(r.status).toBe(200);
  expect(r.body).toEqual({ status: 'ready', sectionId: 132 });
  expect(enqueuer.enqueue).not.toHaveBeenCalled();
});
it('403 for an anonymous user (never reads/enqueues)', async () => {
  const r = await enqueueDig({ ...base, isAnonymous: true });
  expect(r.status).toBe(403);
  expect(loadSummaryForServe).not.toHaveBeenCalled();
});
it('propagates loadSummaryForServe failure status (404/503/409)', async () => {
  (loadSummaryForServe as jest.Mock).mockResolvedValue({ ok: false, status: 404, error: 'not found' });
  expect((await enqueueDig(base)).status).toBe(404);
});
it('404 when the section is not in the summary', async () => {
  (loadSummaryForServe as jest.Mock).mockResolvedValue(okLoad(false));
  expect((await enqueueDig({ ...base, sectionId: 999 })).status).toBe(404);
});
it('maps guardrail errors: quota→429, cap→503, too_long→400', async () => {
  (loadSummaryForServe as jest.Mock).mockResolvedValue(okLoad(false));
  enqueuer.enqueue.mockRejectedValueOnce(new QuotaExceededError());
  expect((await enqueueDig(base)).status).toBe(429);
  enqueuer.enqueue.mockRejectedValueOnce(new DailyCapError());
  expect((await enqueueDig(base)).status).toBe(503);
  enqueuer.enqueue.mockRejectedValueOnce(new VideoTooLongError());
  expect((await enqueueDig(base)).status).toBe(400);
});
it('maps preflight verdicts: velocity→429, capacity→503, !admitted→403', async () => {
  (loadSummaryForServe as jest.Mock).mockResolvedValue(okLoad(false));
  enqueuer.preflight.mockResolvedValueOnce({ admitted: true, atCapacity: false, velocityExceeded: true, challengeRequired: false });
  expect((await enqueueDig(base)).status).toBe(429);
  enqueuer.preflight.mockResolvedValueOnce({ admitted: true, atCapacity: true, velocityExceeded: false, challengeRequired: false });
  expect((await enqueueDig(base)).status).toBe(503);
  enqueuer.preflight.mockResolvedValueOnce({ admitted: false, atCapacity: false, velocityExceeded: false, challengeRequired: false });
  expect((await enqueueDig(base)).status).toBe(403);
});
it('joined a COMPLETED row but the blob is still absent → 409 repair, NOT 202 (§9.2)', async () => {
  const exists = jest.fn(async () => false); // absent at dedup AND at the post-enqueue re-check
  (loadSummaryForServe as jest.Mock).mockResolvedValue(okLoad(false, exists));
  enqueuer.enqueue.mockResolvedValueOnce({ jobId: 'jc', status: 'completed', joined: true });
  const r = await enqueueDig(base);
  expect(r.status).toBe(409);
  expect(exists).toHaveBeenCalledTimes(2); // dedup + re-check
});
it('joined a COMPLETED row and the blob is now present (concurrent promote) → 200 ready', async () => {
  let calls = 0;
  const exists = jest.fn(async () => (calls++ === 0 ? false : true)); // miss at dedup, hit on re-check
  (loadSummaryForServe as jest.Mock).mockResolvedValue(okLoad(false, exists));
  enqueuer.enqueue.mockResolvedValueOnce({ jobId: 'jc', status: 'completed', joined: true });
  const r = await enqueueDig(base);
  expect(r.status).toBe(200);
  expect(r.body).toEqual({ status: 'ready', sectionId: 132 });
});
it('joined a live queued/active row → 202 (normal in-flight join, no re-check needed)', async () => {
  (loadSummaryForServe as jest.Mock).mockResolvedValue(okLoad(false));
  enqueuer.enqueue.mockResolvedValueOnce({ jobId: 'jq', status: 'queued', joined: true });
  expect((await enqueueDig(base)).status).toBe(202);
});
