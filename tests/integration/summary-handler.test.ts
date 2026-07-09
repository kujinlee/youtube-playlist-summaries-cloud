// tests/integration/summary-handler.test.ts
//
// Integration suite for makeSummaryHandler (Task 7) — the idempotent, self-healing
// summary job handler — against a live local Supabase stack. Gemini + transcript
// resolution are mocked at the lib boundary (project mocking policy); everything else
// (getWorkerStorageBundle, reserveVideoSlot, persistSummary, readVideo, blobStore) is real.
//
// Run via: npm run test:integration -- summary-handler
// Requires: stack up + .env.test.local present (see tests/integration/setup.ts).

import { randomUUID } from 'crypto';
import { adminClient, newUser, signInAs } from './helpers/clients';
import type { LeasedJob } from '@/lib/storage/job-queue';
import { docVersionKey } from '@/lib/storage/job-queue';
import { CURRENT_DOC_VERSION } from '@/lib/doc-version';
import { padSerial } from '@/lib/serial-filename';
import { slugify } from '@/lib/slugify';
import { NonRetryableError } from '@/lib/job-queue/errors';
import { PermanentTranscriptError } from '@/lib/transcript-source-errors';
import type { HandlerCtx } from '@/lib/job-queue/handler-context';
import { SupabaseBlobStore } from '@/lib/storage/supabase/supabase-blob-store';
import type { IngestionPayload } from '@/lib/job-queue/ingestion-payload';

jest.mock('@/lib/gemini');
jest.mock('@/lib/transcript-source');

import { generateSummary, extractQuickView } from '@/lib/gemini';
import { resolveTranscriptSegments } from '@/lib/transcript-source';
// Imported AFTER the jest.mock calls above so makeSummaryHandler's internal imports of
// '@/lib/gemini' and '@/lib/transcript-source' resolve to the mocked module instances.
import { makeSummaryHandler, MAX_DURATION_SECONDS } from '@/lib/job-queue/summary-handler';

jest.setTimeout(30_000);

const admin = () => adminClient();

async function seedPlaylist(client: any, ownerId: string): Promise<{ playlistId: string; playlistKey: string }> {
  const playlistKey = `k-${randomUUID()}`;
  const { data, error } = await client.from('playlists')
    .insert({ owner_id: ownerId, playlist_key: playlistKey, playlist_url: `https://x/${randomUUID()}` })
    .select('id').single();
  if (error) throw error;
  return { playlistId: data.id as string, playlistKey };
}

const mockCtx: HandlerCtx = {
  isCancelled: async () => false,
  signal: new AbortController().signal,
  setPhase: async () => {},
};

const GEMINI_SUMMARY_RESPONSE = {
  summary: '## 1. Alpha\n▶ [0:00](u)\nAlpha body.\n---\n## Conclusion\n▶ [1:00](u)\nWrap.',
  ratings: { usefulness: 4, depth: 4, originality: 4, recency: 4, completeness: 4 },
  overallScore: 4,
  videoType: 'Analysis',
  audience: 'Intermediate',
  tags: ['x'],
  tldr: 'This video explains alpha.',
  takeaways: ['Do alpha'],
};

const SEGMENTS = [{ text: 'hello world', offset: 0, duration: 5 }];

function resetGeminiMocks() {
  (resolveTranscriptSegments as jest.Mock).mockReset().mockResolvedValue({ segments: SEGMENTS, source: 'captions' });
  (generateSummary as jest.Mock).mockReset().mockResolvedValue(GEMINI_SUMMARY_RESPONSE);
  (extractQuickView as jest.Mock).mockReset().mockResolvedValue({ tldr: 'fallback', takeaways: ['fallback'] });
}

function makePayload(over: Partial<IngestionPayload> = {}): IngestionPayload {
  return {
    youtubeUrl: 'https://youtu.be/abc123',
    title: 'My Test Video',
    channel: 'Test Channel',
    durationSeconds: 120,
    playlistIndex: 1,
    videoPublishedAt: '2024-01-01T00:00:00.000Z',
    addedToPlaylistAt: '2024-01-02T00:00:00.000Z',
    ...over,
  };
}

function makeJob(fields: { ownerId: string; playlistId: string; videoId: string; payload: unknown }): LeasedJob {
  return {
    id: randomUUID(),
    sectionId: -1,
    kind: 'summary',
    version: docVersionKey(CURRENT_DOC_VERSION),
    attempts: 1,
    leaseToken: randomUUID(),
    ...fields,
  };
}

beforeEach(() => {
  resetGeminiMocks();
});

// ---------------------------------------------------------------------------
// (a) happy path
// ---------------------------------------------------------------------------
test('(a) happy path: Video row persisted + promoted + blob present', async () => {
  const u = await newUser();
  const { client, userId } = await signInAs(u.email, u.password);
  const { playlistId, playlistKey } = await seedPlaylist(client, userId);
  const videoId = randomUUID();
  const payload = makePayload();
  const job = makeJob({ ownerId: userId, playlistId, videoId, payload });

  const handler = makeSummaryHandler(admin());
  await handler(job, mockCtx);

  const row = await admin().from('videos').select('data').eq('playlist_id', playlistId).eq('video_id', videoId).single();
  const data = row.data!.data as any;

  expect(typeof data.serialNumber).toBe('number');
  expect(data.serialNumber).toBeGreaterThan(0);
  expect(data.playlistIndex).toBe(payload.playlistIndex);
  expect(data.ratings).toEqual(GEMINI_SUMMARY_RESPONSE.ratings);
  expect(data.artifacts.summaryMd.status).toBe('promoted');

  const baseName = `${padSerial(data.serialNumber)}_${slugify(payload.title)}`;
  expect(data.summaryMd).toBe(`${baseName}.md`);
  expect(data.artifacts.summaryMd.key).toBe(`${baseName}.md`);

  const blob = new SupabaseBlobStore(admin(), 'artifacts');
  const principal = { id: userId, indexKey: playlistKey };
  expect(await blob.exists(principal, `${baseName}.md`)).toBe(true);
  const content = await blob.get(principal, `${baseName}.md`);
  expect(content?.toString()).toContain('Alpha body.');
});

// ---------------------------------------------------------------------------
// (b) idempotent re-run: a fresh handler on the same DB state must not call Gemini again
// ---------------------------------------------------------------------------
test('(b) idempotent re-run: fresh handler skips Gemini, serial unchanged', async () => {
  const u = await newUser();
  const { client, userId } = await signInAs(u.email, u.password);
  const { playlistId } = await seedPlaylist(client, userId);
  const videoId = randomUUID();
  const payload = makePayload();
  const job = makeJob({ ownerId: userId, playlistId, videoId, payload });

  const handler1 = makeSummaryHandler(admin());
  await handler1(job, mockCtx);

  const before = await admin().from('videos').select('data').eq('playlist_id', playlistId).eq('video_id', videoId).single();
  const serialBefore = before.data!.data.serialNumber;

  (generateSummary as jest.Mock).mockClear();
  (resolveTranscriptSegments as jest.Mock).mockClear();

  const handler2 = makeSummaryHandler(admin()); // fresh handler instance, same DB state
  await handler2(job, mockCtx);

  expect(generateSummary).not.toHaveBeenCalled();
  expect(resolveTranscriptSegments).not.toHaveBeenCalled();

  const after = await admin().from('videos').select('data').eq('playlist_id', playlistId).eq('video_id', videoId).single();
  expect(after.data!.data.serialNumber).toBe(serialBefore);
  expect(after.data!.data.artifacts.summaryMd.status).toBe('promoted');
});

// ---------------------------------------------------------------------------
// (c) malformed payload → NonRetryableError
// ---------------------------------------------------------------------------
test('(c) malformed payload → NonRetryableError', async () => {
  const u = await newUser();
  const { client, userId } = await signInAs(u.email, u.password);
  const { playlistId } = await seedPlaylist(client, userId);
  const videoId = randomUUID();
  const job = makeJob({ ownerId: userId, playlistId, videoId, payload: { title: 'missing everything else' } });

  const handler = makeSummaryHandler(admin());
  await expect(handler(job, mockCtx)).rejects.toBeInstanceOf(NonRetryableError);
  expect(generateSummary).not.toHaveBeenCalled();
});

// ---------------------------------------------------------------------------
// (d) over-long video → NonRetryableError
// ---------------------------------------------------------------------------
test('(d) durationSeconds > MAX_DURATION_SECONDS → NonRetryableError', async () => {
  const u = await newUser();
  const { client, userId } = await signInAs(u.email, u.password);
  const { playlistId } = await seedPlaylist(client, userId);
  const videoId = randomUUID();
  const payload = makePayload({ durationSeconds: MAX_DURATION_SECONDS + 1 });
  const job = makeJob({ ownerId: userId, playlistId, videoId, payload });

  const handler = makeSummaryHandler(admin());
  await expect(handler(job, mockCtx)).rejects.toBeInstanceOf(NonRetryableError);
  expect(generateSummary).not.toHaveBeenCalled();
});

// ---------------------------------------------------------------------------
// (i) doc-version mismatch → NonRetryableError, Gemini not called. A job enqueued at a doc
//     version the worker no longer speaks must fail fast, not run a stale pipeline.
// ---------------------------------------------------------------------------
test('(i) doc-version mismatch → NonRetryableError, Gemini not called', async () => {
  const u = await newUser();
  const { client, userId } = await signInAs(u.email, u.password);
  const { playlistId } = await seedPlaylist(client, userId);
  const videoId = randomUUID();
  const job = { ...makeJob({ ownerId: userId, playlistId, videoId, payload: makePayload() }), version: '9.9' };

  const handler = makeSummaryHandler(admin());
  await expect(handler(job, mockCtx)).rejects.toBeInstanceOf(NonRetryableError);
  expect(generateSummary).not.toHaveBeenCalled();
});

// ---------------------------------------------------------------------------
// (j) reserve rollback: a PERMANENT transcript failure on a brand-new video removes the bare
//     reserved row (non-retryable, never self-heals). A RETRYABLE (transient) failure must NOT
//     delete it, so the next attempt self-heals with the same serial.
// ---------------------------------------------------------------------------
test('(j) permanent transcript failure rolls back the freshly-reserved row', async () => {
  const u = await newUser();
  const { client, userId } = await signInAs(u.email, u.password);
  const { playlistId } = await seedPlaylist(client, userId);
  const videoId = randomUUID();
  const job = makeJob({ ownerId: userId, playlistId, videoId, payload: makePayload() });

  (resolveTranscriptSegments as jest.Mock).mockReset().mockRejectedValue(
    new PermanentTranscriptError(`no transcript available for ${videoId}: captions and video both returned zero segments`),
  );

  const handler = makeSummaryHandler(admin());
  await expect(handler(job, mockCtx)).rejects.toBeInstanceOf(NonRetryableError);

  const row = await admin().from('videos').select('id').eq('playlist_id', playlistId).eq('video_id', videoId).maybeSingle();
  expect(row.data).toBeNull(); // rolled back
});

test('(j2) transient transcript failure keeps the reserved row (retryable, self-heals)', async () => {
  const u = await newUser();
  const { client, userId } = await signInAs(u.email, u.password);
  const { playlistId } = await seedPlaylist(client, userId);
  const videoId = randomUUID();
  const job = makeJob({ ownerId: userId, playlistId, videoId, payload: makePayload() });

  (resolveTranscriptSegments as jest.Mock).mockReset().mockRejectedValue(new Error('transient network blip'));

  const handler = makeSummaryHandler(admin());
  await expect(handler(job, mockCtx)).rejects.not.toBeInstanceOf(NonRetryableError);

  const row = await admin().from('videos').select('data').eq('playlist_id', playlistId).eq('video_id', videoId).maybeSingle();
  expect(row.data).not.toBeNull(); // reserved row survives for the next attempt
  expect(typeof row.data!.data.serialNumber).toBe('number');
});

// ---------------------------------------------------------------------------
// (e) pre-promote-crash retry (self-healing): re-reserves same serial, re-stages same
//     deterministic key, promotes cleanly, Gemini called again (nothing was promoted).
// ---------------------------------------------------------------------------
test('(e) pre-promote crash retry: same serial, re-promotes cleanly, Gemini called again', async () => {
  const u = await newUser();
  const { client, userId } = await signInAs(u.email, u.password);
  const { playlistId } = await seedPlaylist(client, userId);
  const videoId = randomUUID();
  const payload = makePayload();
  const job = makeJob({ ownerId: userId, playlistId, videoId, payload });

  const promoteSpy = jest.spyOn(SupabaseBlobStore.prototype, 'promote')
    .mockImplementationOnce(async () => { throw new Error('simulated crash between commit and promote'); });

  const handler1 = makeSummaryHandler(admin());
  await expect(handler1(job, mockCtx)).rejects.toThrow('simulated crash between commit and promote');

  const midRow = await admin().from('videos').select('data').eq('playlist_id', playlistId).eq('video_id', videoId).single();
  expect(midRow.data!.data.artifacts.summaryMd.status).toBe('committed');
  const serialAfterCrash = midRow.data!.data.serialNumber;

  expect(generateSummary).toHaveBeenCalledTimes(1);

  // Re-run with a fresh handler; promoteSpy's mockImplementationOnce is exhausted so this
  // call uses the real (working) implementation.
  const handler2 = makeSummaryHandler(admin());
  await handler2(job, mockCtx);

  const finalRow = await admin().from('videos').select('data').eq('playlist_id', playlistId).eq('video_id', videoId).single();
  expect(finalRow.data!.data.serialNumber).toBe(serialAfterCrash); // no serial drift
  expect(finalRow.data!.data.artifacts.summaryMd.status).toBe('promoted'); // no orphan
  expect(generateSummary).toHaveBeenCalledTimes(2); // skip did NOT fire — nothing was promoted

  const baseName = `${padSerial(serialAfterCrash)}_${slugify(payload.title)}`;
  expect(finalRow.data!.data.summaryMd).toBe(`${baseName}.md`);

  promoteSpy.mockRestore();
});

// ---------------------------------------------------------------------------
// (f) transient transcript failure → propagated as-is, NOT wrapped as NonRetryableError
// ---------------------------------------------------------------------------
test('(f) transient transcript failure propagates, not wrapped as NonRetryableError', async () => {
  const u = await newUser();
  const { client, userId } = await signInAs(u.email, u.password);
  const { playlistId } = await seedPlaylist(client, userId);
  const videoId = randomUUID();
  const payload = makePayload();
  const job = makeJob({ ownerId: userId, playlistId, videoId, payload });

  (resolveTranscriptSegments as jest.Mock).mockReset().mockRejectedValue(new Error('transient network blip'));

  const handler = makeSummaryHandler(admin());
  let caught: unknown;
  try {
    await handler(job, mockCtx);
    throw new Error('expected handler to throw');
  } catch (e) {
    caught = e;
  }
  expect(caught).toBeInstanceOf(Error);
  expect(caught).not.toBeInstanceOf(NonRetryableError);
  expect((caught as Error).message).toBe('transient network blip');
});

// ---------------------------------------------------------------------------
// (g) PERMANENT transcript failure → NonRetryableError (do not burn max_attempts on a
//     provably-unavailable transcript, each retry holding a worker slot to dead_letter).
// ---------------------------------------------------------------------------
test('(g) permanent transcript failure → NonRetryableError (not retryable)', async () => {
  const u = await newUser();
  const { client, userId } = await signInAs(u.email, u.password);
  const { playlistId } = await seedPlaylist(client, userId);
  const videoId = randomUUID();
  const payload = makePayload();
  const job = makeJob({ ownerId: userId, playlistId, videoId, payload });

  (resolveTranscriptSegments as jest.Mock).mockReset().mockRejectedValue(
    new PermanentTranscriptError(`no transcript available for ${videoId}: captions and video both returned zero segments`),
  );

  const handler = makeSummaryHandler(admin());
  await expect(handler(job, mockCtx)).rejects.toBeInstanceOf(NonRetryableError);
  expect(generateSummary).not.toHaveBeenCalled();
});

// ---------------------------------------------------------------------------
// (k) config-driven duration guard (spec §10): the handler reads the LIVE
//     guardrail_config.max_duration_seconds, not a hard-coded constant. Set it low, then assert an
//     over-value payload is rejected (NonRetryableError, no Gemini) and an under-value one is
//     accepted (runs the full pipeline). Restores the singleton row afterward.
// ---------------------------------------------------------------------------
test('(k) handler reads guardrail_config.max_duration_seconds for the duration guard', async () => {
  const u = await newUser();
  const { client, userId } = await signInAs(u.email, u.password);
  const { playlistId } = await seedPlaylist(client, userId);

  const orig = await admin().from('guardrail_config').select('max_duration_seconds').single();
  const origMax = orig.data!.max_duration_seconds as number;
  try {
    await admin().from('guardrail_config').update({ max_duration_seconds: 100 }).eq('id', true);

    // over the live cap (200 > 100) → NonRetryableError, Gemini never called
    const overJob = makeJob({
      ownerId: userId, playlistId, videoId: randomUUID(), payload: makePayload({ durationSeconds: 200 }),
    });
    const handler = makeSummaryHandler(admin());
    await expect(handler(overJob, mockCtx)).rejects.toBeInstanceOf(NonRetryableError);
    expect(generateSummary).not.toHaveBeenCalled();

    // under the live cap (50 <= 100) → accepted, pipeline runs to promotion
    const underVideoId = randomUUID();
    const underJob = makeJob({
      ownerId: userId, playlistId, videoId: underVideoId, payload: makePayload({ durationSeconds: 50 }),
    });
    await handler(underJob, mockCtx);
    expect(generateSummary).toHaveBeenCalledTimes(1);
    const row = await admin().from('videos').select('data')
      .eq('playlist_id', playlistId).eq('video_id', underVideoId).single();
    expect(row.data!.data.artifacts.summaryMd.status).toBe('promoted');
  } finally {
    await admin().from('guardrail_config').update({ max_duration_seconds: origMax }).eq('id', true);
  }
});

// ---------------------------------------------------------------------------
// (h) NaN durationSeconds is rejected pre-flight → NonRetryableError. Without the schema's
//     `.finite()`, NaN slips past the `> MAX_DURATION_SECONDS` guard (NaN > MAX is false).
// ---------------------------------------------------------------------------
test('(h) NaN durationSeconds → NonRetryableError (does not bypass the over-long guard)', async () => {
  const u = await newUser();
  const { client, userId } = await signInAs(u.email, u.password);
  const { playlistId } = await seedPlaylist(client, userId);
  const videoId = randomUUID();
  const job = makeJob({ ownerId: userId, playlistId, videoId, payload: makePayload({ durationSeconds: NaN }) });

  const handler = makeSummaryHandler(admin());
  await expect(handler(job, mockCtx)).rejects.toBeInstanceOf(NonRetryableError);
  expect(generateSummary).not.toHaveBeenCalled();
});
