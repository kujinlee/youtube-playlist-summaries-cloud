/**
 * pipeline-async.test.ts
 *
 * Tests that the pipeline correctly awaits every MetadataStore call. Uses a
 * delayed-async fake (5 ms macrotask delay per call) so that any consumer that
 * reads a store value without awaiting gets `undefined` rather than the real value,
 * producing an immediate, deterministic failure.
 *
 * Three behaviours under test:
 * 1. missed-await detection — the delayedStore itself surfaces sync access as undefined
 * 2. full sync under delay — runIngestion stays green with a delayed store
 * 3. idempotency — running ingestion twice produces consistent results
 */
import crypto from 'crypto';
import fs from 'fs';
import os from 'os';
import path from 'path';

import { delayedStore } from './storage/delayed-async-fake';
import { LocalFsMetadataStore } from '@/lib/storage/local/local-metadata-store';
import type { MetadataStore } from '@/lib/storage/metadata-store';
import { getPrincipal } from '@/lib/storage/resolve';

// ---------------------------------------------------------------------------
// B1: missed-await detection
// ---------------------------------------------------------------------------
it('B1: delayedStore surfaces a missed await as undefined (discipline check)', async () => {
  const dir = fs.mkdtempSync(path.join(os.homedir(), '.tmp-async-fake-'));
  fs.writeFileSync(path.join(dir, 'playlist-index.json'),
    JSON.stringify({ playlistUrl: 'https://p', outputFolder: dir, videos: [] }));
  try {
    const inner = new LocalFsMetadataStore();
    const store = delayedStore(inner);
    const principal = getPrincipal(dir);

    // Correctly awaited: should return a real PlaylistIndex object.
    const idx = await store.readIndex(principal);
    expect(idx.videos).toBeDefined();

    // Without await the result is a pending Promise — accessing .videos yields undefined.
    // (TypeScript would catch this in real code; this test documents the runtime behaviour.)
    const pendingPromise = store.readIndex(principal);
    const pending = pendingPromise as unknown as Record<string, unknown>;
    expect(pending.videos).toBeUndefined(); // Promise, not PlaylistIndex
    // Drain the floating promise before cleanup so it doesn't pollute the next test.
    await pendingPromise;
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

// ---------------------------------------------------------------------------
// B2: full sync under delay — runIngestion awaits every store call
// ---------------------------------------------------------------------------
jest.mock('@/lib/youtube');
jest.mock('@/lib/gemini');
jest.mock('@/lib/html-doc/generate');
// Replace the singleton store with a delayed version so that any missed await
// in the pipeline turns into a runtime type error caught by the test.
jest.mock('@/lib/storage/resolve', () => {
  const real = jest.requireActual('@/lib/storage/resolve') as typeof import('@/lib/storage/resolve');
  const { LocalFsMetadataStore: LocalImpl } = jest.requireActual('@/lib/storage/local/local-metadata-store') as typeof import('@/lib/storage/local/local-metadata-store');
  const { delayedStore: delayed } = require('./storage/delayed-async-fake') as typeof import('./storage/delayed-async-fake');
  const store: MetadataStore = delayed(new LocalImpl());
  return { ...real, getMetadataStore: () => store };
});

import { runIngestion } from '@/lib/pipeline';
import * as youtube from '@/lib/youtube';
import * as gemini from '@/lib/gemini';
import * as htmlDocGenerate from '@/lib/html-doc/generate';

const mockFetchPlaylistVideos = jest.mocked(youtube.fetchPlaylistVideos);
const mockFetchTranscriptSegments = jest.mocked(youtube.fetchTranscriptSegments);
const mockDetectLanguage = jest.mocked(youtube.detectLanguage);
const mockGenerateSummary = jest.mocked(gemini.generateSummary);
const mockRunHtmlDoc = jest.mocked(htmlDocGenerate.runHtmlDoc);

describe('B2: runIngestion awaits every store call (delayed-store integration)', () => {
  let dir: string;

  beforeEach(() => {
    dir = fs.mkdtempSync(path.join(os.homedir(), `.tmp-pipeline-async-${crypto.randomUUID().slice(0, 8)}-`));
    fs.writeFileSync(path.join(dir, 'playlist-index.json'),
      JSON.stringify({ playlistUrl: 'https://p', outputFolder: dir, videos: [] }));
    process.env.YOUTUBE_API_KEY = 'test-key';
    process.env.PREGEN_SUMMARY_HTML = 'off';

    mockDetectLanguage.mockReturnValue('en');
    mockFetchTranscriptSegments.mockResolvedValue([{ text: 'hello', offset: 0, duration: 5 }]);
    mockGenerateSummary.mockResolvedValue({
      summary: 'Summary body.',
      ratings: { usefulness: 3, depth: 3, originality: 3, recency: 3, completeness: 3 },
      overallScore: 3,
      tldr: 'tldr',
      takeaways: ['t1'],
    });
    mockRunHtmlDoc.mockResolvedValue(undefined);
  });

  afterEach(() => {
    fs.rmSync(dir, { recursive: true, force: true });
    jest.clearAllMocks();
    delete process.env.YOUTUBE_API_KEY;
    delete process.env.PREGEN_SUMMARY_HTML;
  });

  it('completes without error for a single new video', async () => {
    mockFetchPlaylistVideos.mockResolvedValue([{
      videoId: 'vid1', title: 'Alpha', youtubeUrl: 'https://y.be/v1', durationSeconds: 60,
    }]);
    const events: { type: string }[] = [];
    await runIngestion('https://p', dir, (e) => events.push(e));
    expect(events.some((e) => e.type === 'done')).toBe(true);
    expect(events.every((e) => e.type !== 'error')).toBe(true);
    // Verify the markdown was written
    const mdFiles = fs.readdirSync(dir).filter((f) => f.endsWith('.md'));
    expect(mdFiles).toHaveLength(1);
  });

  it('B3: idempotent — second run skips already-indexed video', async () => {
    const meta = { videoId: 'vid1', title: 'Alpha', youtubeUrl: 'https://y.be/v1', durationSeconds: 60 };
    mockFetchPlaylistVideos.mockResolvedValue([meta]);

    // First run
    await runIngestion('https://p', dir, () => {});
    const mdAfterFirst = fs.readdirSync(dir).filter((f) => f.endsWith('.md'));
    expect(mdAfterFirst).toHaveLength(1);

    // Second run — vid1 now in the index, so it is skipped
    const events2: { type: string }[] = [];
    await runIngestion('https://p', dir, (e) => events2.push(e));
    expect(events2.some((e) => e.type === 'done')).toBe(true);
    expect(events2.every((e) => e.type !== 'error')).toBe(true);
    // No new md files written
    const mdAfterSecond = fs.readdirSync(dir).filter((f) => f.endsWith('.md'));
    expect(mdAfterSecond).toHaveLength(1);
  });
});
