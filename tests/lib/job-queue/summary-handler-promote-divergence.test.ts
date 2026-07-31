/**
 * Architecture review finding #2, **Writer 1** — the summary writer.
 *
 * The companion test `tests/lib/dig/write-dig-section-blob-promote.test.ts` proved the
 * writer-level defect for W2 (dig). Tracing its REACHABILITY showed W2 is LOW severity,
 * and — decisively — that W2 is protected by an accident of key design:
 *
 *   dig key:      dig/{base}/{sectionId}.r{V}.md    <- generator version IS in the key
 *   summary key:  {serial}_{slug}.md                <- NO version anywhere
 *
 * A dig generator-version bump therefore lands on a FRESH key and cannot collide. The
 * summary key has no such protection, and `reserve_video_slot` deliberately returns the
 * EXISTING serial for a video it has already seen (0009…sql:88 — `if v_serial is not null
 * then return v_serial`), so the key is stable for the life of the video.
 *
 * That makes a `CURRENT_DOC_VERSION` bump the dangerous case, and a doc-version bump is a
 * DESIGNED re-run: it opens a new `jobs_idem_active` slot, and the handler's idempotency
 * skip (summary-handler.ts:85-91) deliberately does NOT skip when the stored docVersion
 * differs from the job's.
 *
 * So the question this test asks: after a doc-version bump re-summarizes a video, does the
 * cloud path serve the NEW markdown — or does it keep the old body while `persistSummary`
 * stamps the new version anyway?
 *
 * This drives the REAL `makeSummaryHandler` (real key derivation, real write sequence).
 * Only the boundaries the integration suite already mocks are faked here, plus the storage
 * seam — substituted with `InMemoryBlobStore`, which is what finding #3 was built for.
 */
import type { LeasedJob } from '@/lib/storage/job-queue';
import { InMemoryBlobStore } from '@/lib/storage/testing/in-memory-blob-store';
import { localPrincipal } from '@/lib/storage/principal';
import type { HandlerCtx } from '@/lib/job-queue/handler-context';
import { padSerial } from '@/lib/serial-filename';
import { slugify } from '@/lib/slugify';

jest.mock('@/lib/storage/resolve');
jest.mock('@/lib/storage/worker-persistence');
jest.mock('@/lib/ingestion/summary-core');

import { getWorkerStorageBundle } from '@/lib/storage/resolve';
import { reserveVideoSlot, persistSummary, readVideo } from '@/lib/storage/worker-persistence';
import { summaryCore } from '@/lib/ingestion/summary-core';
// Imported AFTER the jest.mock calls so the handler's own imports resolve to the mocks.
import { makeSummaryHandler } from '@/lib/job-queue/summary-handler';
import { docVersionKey } from '@/lib/storage/job-queue';
import { CURRENT_DOC_VERSION } from '@/lib/doc-version';

const OWNER = '11111111-1111-4111-8111-111111111111';
const PLAYLIST = '22222222-2222-4222-8222-222222222222';
const VIDEO = 'vid123';
const TITLE = 'A Video About Alpha';
const SERIAL = 7;

const principal = localPrincipal('/idx');
const WORKER_VERSION = docVersionKey(CURRENT_DOC_VERSION);

/** The key the handler derives — recomputed here from the SAME functions it uses. */
const SUMMARY_KEY = `${padSerial(SERIAL)}_${slugify(TITLE)}.md`;

const ctx: HandlerCtx = {
  isCancelled: async () => false,
  signal: new AbortController().signal,
  setPhase: async () => {},
  billing: { metered: false },
};

/** Only `guardrail_config` is read straight off the client; everything else goes through
 *  the mocked worker-persistence wrappers. */
const serviceClient = {
  from: () => ({
    select: () => ({ single: async () => ({ data: { max_duration_seconds: 4 * 3600 }, error: null }) }),
    delete: () => ({ eq: () => ({ eq: () => ({ eq: () => ({ is: async () => ({ error: null }) }) }) }) }),
  }),
} as never;

function job(): LeasedJob {
  return {
    id: 'job-1', ownerId: OWNER, playlistId: PLAYLIST, videoId: VIDEO, sectionId: 0,
    kind: 'summary', version: WORKER_VERSION, attempts: 1, leaseToken: 'tok',
    payload: {
      youtubeUrl: 'https://youtu.be/vid123', title: TITLE,
      durationSeconds: 600, playlistIndex: 1,
    },
  };
}

/** Rows persisted by the handler, in order — so we can inspect what it CLAIMED. */
let persisted: { status: string; docVersion: unknown }[];

function setup(store: InMemoryBlobStore, mdContent: string, existingDocVersion: unknown | null) {
  persisted = [];
  (getWorkerStorageBundle as jest.Mock).mockResolvedValue({ blobStore: store, principal });
  (reserveVideoSlot as jest.Mock).mockResolvedValue(SERIAL); // stable serial — see header
  (readVideo as jest.Mock).mockResolvedValue(
    existingDocVersion === null
      ? null
      : {
          id: VIDEO, serialNumber: SERIAL, summaryMd: SUMMARY_KEY,
          docVersion: existingDocVersion,
          artifacts: { summaryMd: { key: SUMMARY_KEY, status: 'promoted' } },
        },
  );
  (persistSummary as jest.Mock).mockImplementation(
    async (_c: unknown, _o: string, _p: string, _v: string, video: { docVersion?: unknown }, status: string) => {
      persisted.push({ status, docVersion: video.docVersion });
    },
  );
  (summaryCore as jest.Mock).mockResolvedValue({
    frontmatter: {}, markdown: mdContent, mdContent, quickView: null,
    geminiFields: { language: 'en', ratings: {}, overallScore: 4 },
  });
}

describe('summary writer (W1) — re-summarize after a doc-version bump', () => {
  it('derives the SAME blob key on both runs (no version in the summary key)', async () => {
    const store = new InMemoryBlobStore({ promoteSemantics: 'overwrite' });
    setup(store, 'ORIGINAL summary body', null);
    await makeSummaryHandler(serviceClient)(job(), ctx);

    expect(await store.exists(principal, SUMMARY_KEY)).toBe(true);
    // The contrast with the dig key is the whole finding: `dig/{base}/{id}.r{V}.md` would
    // change here, this does not.
    expect(SUMMARY_KEY).not.toMatch(/\d+\.\d+/);
  });

  it('serves the NEW body under local semantics (promote overwrites)', async () => {
    const store = new InMemoryBlobStore({ promoteSemantics: 'overwrite' });
    setup(store, 'ORIGINAL summary body', null);
    await makeSummaryHandler(serviceClient)(job(), ctx);

    // Doc version bumped: the stored row is one version behind, so the idempotency skip
    // (summary-handler.ts:85-91) does NOT fire and the handler re-summarizes.
    setup(store, 'REGENERATED summary body', { major: 1, minor: 0 });
    await makeSummaryHandler(serviceClient)(job(), ctx);

    const bytes = await store.get(principal, SUMMARY_KEY);
    expect(bytes?.toString()).toContain('REGENERATED summary body');
  });

  // The behaviour under test. If this fails, W1 is a LIVE cloud-only staleness defect:
  // after a doc-version bump the blob keeps its old body while persistSummary stamps the
  // NEW docVersion — i.e. the database asserts a version its blob does not contain.
  it('serves the NEW body under Supabase semantics (promote is create-if-absent)', async () => {
    const store = new InMemoryBlobStore({ promoteSemantics: 'create-if-absent' });
    setup(store, 'ORIGINAL summary body', null);
    await makeSummaryHandler(serviceClient)(job(), ctx);

    setup(store, 'REGENERATED summary body', { major: 1, minor: 0 });
    await makeSummaryHandler(serviceClient)(job(), ctx);

    const bytes = await store.get(principal, SUMMARY_KEY);
    expect(bytes?.toString()).toContain('REGENERATED summary body');
  });

  // The silence is the second half of the defect: whatever the blob ends up holding, the
  // handler unconditionally reports 'promoted' at the CURRENT doc version.
  it('stamps promoted at the current doc version regardless of what the blob holds', async () => {
    const store = new InMemoryBlobStore({ promoteSemantics: 'create-if-absent' });
    setup(store, 'ORIGINAL summary body', null);
    await makeSummaryHandler(serviceClient)(job(), ctx);

    setup(store, 'REGENERATED summary body', { major: 1, minor: 0 });
    await makeSummaryHandler(serviceClient)(job(), ctx);

    expect(persisted.map((p) => p.status)).toEqual(['committed', 'promoted']);
    expect(persisted.at(-1)?.docVersion).toEqual(CURRENT_DOC_VERSION);
  });
});
