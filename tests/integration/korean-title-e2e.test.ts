// Backlog #36, plan T14 — the end-to-end keystone: a title in ANY language ingests and then SERVES.
// Behaviors 14, 15, 16, 23. Drives the REAL cloud ingest (makeSummaryHandler) and the REAL serve
// seam (loadSummaryForServe); invents no entry points. Gemini and transcript resolution are mocked
// at the lib boundary — the project's mocking policy — so nothing meters.
//
// Money invariant: the ledger must not move. Asserted directly in behavior 14.
//
// ⚠ WHICH OF THESE ACTUALLY DISCRIMINATE — MEASURED 2026-08-17 by reverting supabase-blob-store.ts
// to its pre-encoder form and re-running. Only behaviors 14 and 23 go RED. Behaviors 15 and 16 pass
// with OR without the encoder, so they are regression guards, not evidence the fix works.
//
// The reason is `slugify` (lib/slugify.ts), which replaces every non-`\p{L}\p{N}` run with `-`:
//
//   'Café Introduction'.normalize('NFD')  →  the combining acute U+0301 is \p{M}, stripped
//                                            →  `cafe-introduction`   ASCII already
//   'intro 😀'                            →  the emoji is neither \p{L} nor \p{N}, stripped
//                                            →  `intro`               ASCII already
//   '한국어 강의'                          →  Hangul IS \p{L}, SURVIVES
//                                            →  `한국어-강의`          ← non-ASCII, the real case
//   'Lesson ⒈'                            →  U+2488 IS \p{N}, SURVIVES
//                                            →  `lesson-⒈`            ← non-ASCII, the real case
//
// Keep 15 and 16 — they pin behaviour that could regress if slugify changes — but do not read them
// as proof of the encoder. The plan listed all four as encoder evidence; two of them are not.
import fs from 'fs';
import os from 'os';
import path from 'path';
import { randomUUID } from 'crypto';
import type { SupabaseClient } from '@supabase/supabase-js';
import { adminClient, newUser, signInAs } from './helpers/clients';
import type { LeasedJob } from '@/lib/storage/job-queue';
import { docVersionKey } from '@/lib/storage/job-queue';
import { CURRENT_DOC_VERSION } from '@/lib/doc-version';
import { padSerial } from '@/lib/serial-filename';
import { slugify } from '@/lib/slugify';
import { localBlobStore } from '@/lib/storage/local/local-blob-store';
import { localPrincipal } from '@/lib/storage/principal';
import { loadSummaryForServe } from '@/lib/html-doc/serve-summary-core';
import type { HandlerCtx } from '@/lib/job-queue/handler-context';
import type { IngestionPayload } from '@/lib/job-queue/ingestion-payload';

jest.mock('@/lib/gemini');
jest.mock('@/lib/transcript-source');

import { generateSummary, extractQuickView } from '@/lib/gemini';
import { resolveTranscriptSegments } from '@/lib/transcript-source';
// AFTER the jest.mock calls, so the handler's own imports resolve to the mocked modules.
import { makeSummaryHandler } from '@/lib/job-queue/summary-handler';

jest.setTimeout(30_000);

// getStorageBundle({ supabaseClient }) selects the Supabase stores ONLY when
// STORAGE_BACKEND === 'supabase' (lib/storage/resolve.ts:53); it defaults to 'local'. Without this
// block `loadSummaryForServe` builds the LOCAL bundle and readIndex treats the cloud playlist key
// as a filesystem path — MEASURED: "Output folder does not exist: k-3656fcd0-…". The idiom is
// lifted from tests/integration/html-serve-isolation.test.ts:11-13.
const priorBackend = process.env.STORAGE_BACKEND;
beforeAll(() => { process.env.STORAGE_BACKEND = 'supabase'; });
afterAll(() => { if (priorBackend === undefined) delete process.env.STORAGE_BACKEND; else process.env.STORAGE_BACKEND = priorBackend; });

const admin = () => adminClient();

/** WHOLE-TABLE spend total — the same query `Ctx.spendLedgerTotal()` runs
 *  (`tests/integration/helpers/cloud.ts:153-161`), without dragging in a Ctx this file never uses.
 *  Because it is whole-table and unfiltered, asserting it unmoved across an ingest performed by a
 *  DIFFERENT user is meaningful, not vacuous — that was the worry; measuring dissolved it. */
async function ledgerTotal(): Promise<number> {
  const { data, error } = await admin().from('spend_ledger').select('reserved_cents,actual_cents');
  if (error) throw error;
  return (data ?? []).reduce((s, r) => s + (r.reserved_cents ?? 0) + (r.actual_cents ?? 0), 0);
}

// The fixtures below are lifted from tests/integration/summary-handler.test.ts — mockCtx (:46),
// GEMINI_SUMMARY_RESPONSE (:53), SEGMENTS (:64), resetGeminiMocks (:66), makePayload (:72),
// makeJob (:85) and seedPlaylist (:37). Verified against that file verbatim.
const mockCtx: HandlerCtx = {
  isCancelled: async () => false,
  signal: new AbortController().signal,
  setPhase: async () => {},
  billing: { metered: false },
};

const GEMINI_SUMMARY_RESPONSE = {
  summary: '## 1. Alpha\n▶ [0:00](u)\nAlpha body.\n---\n## Conclusion\n▶ [1:00](u)\nWrap.',
  ratings: { usefulness: 4, depth: 4, originality: 4, recency: 4, completeness: 4 },
  overallScore: 4, videoType: 'Analysis', audience: 'Intermediate', tags: ['x'],
  tldr: 'This video explains alpha.', takeaways: ['Do alpha'],
};
const SEGMENTS = [{ text: 'hello world', offset: 0, duration: 5 }];

beforeEach(() => {
  (resolveTranscriptSegments as jest.Mock).mockReset()
    .mockResolvedValue({ segments: SEGMENTS, source: 'captions' });
  (generateSummary as jest.Mock).mockReset().mockResolvedValue(GEMINI_SUMMARY_RESPONSE);
  (extractQuickView as jest.Mock).mockReset()
    .mockResolvedValue({ tldr: 'fallback', takeaways: ['fallback'] });
});

function makePayload(over: Partial<IngestionPayload> = {}): IngestionPayload {
  return {
    youtubeUrl: 'https://youtu.be/abc123', title: 'My Test Video', channel: 'Test Channel',
    durationSeconds: 120, playlistIndex: 1,
    videoPublishedAt: '2024-01-01T00:00:00.000Z', addedToPlaylistAt: '2024-01-02T00:00:00.000Z',
    ...over,
  };
}

function makeJob(f: {
  ownerId: string; playlistId: string; videoId: string; payload: unknown;
}): LeasedJob {
  return {
    id: randomUUID(), sectionId: -1, kind: 'summary',
    version: docVersionKey(CURRENT_DOC_VERSION), attempts: 1, leaseToken: randomUUID(), ...f,
  };
}

/** Create a user, sign in, seed a playlist, and run the REAL summary handler for `title`.
 *  Returns the coordinates the serve seam needs. This is the whole point of T14: `slugify`,
 *  `padSerial`, `putStaged`, `promote` and `persist_summary` all run for real. */
async function ingestViaHandler(
  { title }: { title: string },
): Promise<{ videoId: string; playlistId: string; userId: string; client: SupabaseClient }> {
  const u = await newUser();
  const { client, userId } = await signInAs(u.email, u.password);
  const playlistKey = `k-${randomUUID()}`;
  const { data, error } = await client.from('playlists')
    .insert({ owner_id: userId, playlist_key: playlistKey, playlist_url: `https://x/${randomUUID()}` })
    .select('id').single();
  if (error) throw error;
  const playlistId = data.id as string;
  const videoId = randomUUID();
  await makeSummaryHandler(admin())(
    makeJob({ ownerId: userId, playlistId, videoId, payload: makePayload({ title }) }),
    mockCtx,
  );
  return { videoId, playlistId, userId, client };
}

it('behavior 14 — a KOREAN-titled video ingests and SERVES, and the ledger is unmoved', async () => {
  const before = await ledgerTotal();
  const { videoId, playlistId, userId, client } = await ingestViaHandler({ title: '한국어 강의' });
  const load = await loadSummaryForServe(client, { videoId, playlistId, userId });
  // MEASURED before the encoder landed, by reverting supabase-blob-store.ts and re-running:
  //
  //   StorageApiError: Invalid key: <uid>/<k-…>/_staging/<uuid>/001_한국어-강의.md
  //
  // The ingest THROWS at `putStaged`. `persist_summary` never runs, no artifact is ever recorded,
  // and the serve seam is never reached at all — so the user-visible end state is a 404, from
  // serve-summary-core.ts:51 (`status !== 'promoted'`), not the 409 the plan predicted from the
  // key guard at :60-64. The guard never fires: it accepts this key, because it requires a single
  // path component, not ASCII. That distinction is the whole scope finding behind this PR.
  expect(load.ok).toBe(true);
  expect((load as { mdKey: string }).mdKey).toMatch(/^\d{3,}_.*\.md$/);
  expect(await ledgerTotal()).toBe(before);            // Gemini is mocked; nothing may meter
});

it('behavior 15 — an NFD accented-Latin title ingests and serves', async () => {
  const { videoId, playlistId, userId, client } = await ingestViaHandler({
    title: 'Café Introduction'.normalize('NFD'),
  });
  expect((await loadSummaryForServe(client, { videoId, playlistId, userId })).ok).toBe(true);
});

it('behavior 16 — space / emoji titles ingest and serve', async () => {
  for (const title of ['hello world', 'intro \u{1F600}']) {
    const { videoId, playlistId, userId, client } = await ingestViaHandler({ title });
    expect((await loadSummaryForServe(client, { videoId, playlistId, userId })).ok).toBe(true);
  }
});

it('behavior 16 — the VAULT filename is well-formed ON DISK, byte-for-byte, with no U+FFFD', async () => {
  // A LOCAL claim, independent of the encoder: the vault round-trips a Unicode name through the
  // real local blob store byte-for-byte. Decision ① — the vault keeps its Unicode.
  const dir = await fs.promises.mkdtemp(path.join(os.tmpdir(), 'vault-'));
  const P = localPrincipal(dir);
  for (const title of ['hello world', 'intro \u{1F600}']) {
    const name = `${padSerial(1)}_${slugify(title)}.md`;
    expect(name.isWellFormed()).toBe(true);
    await localBlobStore.put(P, name, Buffer.from('# body\n', 'utf8'), 'text/markdown');
    expect(await fs.promises.readdir(dir)).toContain(name);   // byte-for-byte; NO U+FFFD
  }
  await fs.promises.rm(dir, { recursive: true, force: true });
});

// ⚠ A KNOWN, STILL-OPEN DEFECT — deliberately asserted as still broken, not deleted.
//
// The plan's T14 folded this case into the test above, which made that test fail for a reason
// having nothing to do with the encoder. MEASURED 2026-08-17: `slugify` slices at 60 UTF-16 code
// UNITS, so an astral character straddling the boundary is cut in half and the name carries a lone
// surrogate — `name.isWellFormed()` is FALSE today.
//
// That is the `slugify` surrogate repair (plan T3), which is NOT in this PR. Asserting the defect
// still exists is the honest instrument: this test starts FAILING the moment T3 lands, which is
// exactly when someone should come back and delete it. A silently dropped case would have left no
// trace that the astral half of behavior 16 is unmet.
it('KNOWN DEFECT (plan T3, deferred) — an astral char on slugify\'s slice boundary is orphaned', () => {
  const name = `${padSerial(1)}_${slugify('a'.repeat(59) + '\u{20000}')}.md`;
  expect(name.isWellFormed()).toBe(false);   // ← flip to true, and delete this test, when T3 ships
});

it('behavior 23 — a title ending in the U+2488..U+249B or U+1F100 class ingests and serves', async () => {
  for (const ch of ['⒈', '⒛', '\u{1F100}']) {
    const { videoId, playlistId, userId, client } = await ingestViaHandler({ title: `Lesson ${ch}` });
    expect((await loadSummaryForServe(client, { videoId, playlistId, userId })).ok).toBe(true);
  }
});
