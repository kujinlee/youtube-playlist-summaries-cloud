import crypto from 'crypto';
import fs from 'fs';
import os from 'os';
import path from 'path';
import { readIndex, updateVideoFields, upsertVideo } from '../../lib/index-store';
import type { Video } from '../../types';

const TEST_DIR = path.join(os.homedir(), `.test-index-store-updated-at-${crypto.randomUUID()}`);

function makeVideo(overrides: Partial<Video> = {}): Video {
  return {
    id: 'abc12345678',
    title: 'Test Video',
    youtubeUrl: 'https://www.youtube.com/watch?v=abc12345678',
    language: 'en',
    durationSeconds: 300,
    archived: false,
    ratings: { usefulness: 4, depth: 3, originality: 5, recency: 4, completeness: 3 },
    overallScore: 3.8,
    summaryMd: null,
    processedAt: '2024-01-01T00:00:00.000Z',
    ...overrides,
  };
}

beforeAll(() => fs.mkdirSync(TEST_DIR, { recursive: true }));
afterAll(() => fs.rmSync(TEST_DIR, { recursive: true, force: true }));

describe('updateVideoFields stamps updatedAt on the single mutated video', () => {
  it('stamps the touched video with an ISO updatedAt; a sibling video is unchanged', () => {
    const dir = path.join(TEST_DIR, 'update-fields-sibling');
    fs.mkdirSync(dir, { recursive: true });

    const touched = makeVideo({ id: 'vidTOUCHED01' });
    const sibling = makeVideo({ id: 'vidSIBLING01' });
    upsertVideo(dir, touched);
    upsertVideo(dir, sibling);

    const before = readIndex(dir);
    const siblingBefore = before.videos.find((v) => v.id === 'vidSIBLING01')!;
    expect(siblingBefore.updatedAt).toEqual(expect.any(String));

    updateVideoFields(dir, 'vidTOUCHED01', { personalScore: 4 });

    const result = readIndex(dir);
    const touchedResult = result.videos.find((v) => v.id === 'vidTOUCHED01')!;
    const siblingResult = result.videos.find((v) => v.id === 'vidSIBLING01')!;

    expect(touchedResult.updatedAt).toEqual(expect.any(String));
    expect(new Date(touchedResult.updatedAt!).toISOString()).toBe(touchedResult.updatedAt);
    expect(touchedResult.personalScore).toBe(4);

    // N3 (load-bearing): writeIndex must never stamp the whole file — the
    // sibling video (present in the same index but not the mutation target)
    // must be byte-for-byte unaffected by the update, including its own
    // pre-existing updatedAt timestamp.
    expect(siblingResult.updatedAt).toBe(siblingBefore.updatedAt);
    expect(siblingResult).toEqual(siblingBefore);
  });
});

describe('upsertVideo stamps updatedAt on the single mutated video', () => {
  it('stamps the inserted/replaced video with an ISO updatedAt; a sibling video is unchanged', () => {
    const dir = path.join(TEST_DIR, 'upsert-sibling');
    fs.mkdirSync(dir, { recursive: true });

    const sibling = makeVideo({ id: 'vidSIBLING02' });
    upsertVideo(dir, sibling);

    const before = readIndex(dir);
    const siblingBefore = before.videos.find((v) => v.id === 'vidSIBLING02')!;
    expect(siblingBefore.updatedAt).toEqual(expect.any(String));

    const touched = makeVideo({ id: 'vidTOUCHED02' });
    upsertVideo(dir, touched);

    const result = readIndex(dir);
    const touchedResult = result.videos.find((v) => v.id === 'vidTOUCHED02')!;
    const siblingResult = result.videos.find((v) => v.id === 'vidSIBLING02')!;

    expect(touchedResult.updatedAt).toEqual(expect.any(String));
    expect(new Date(touchedResult.updatedAt!).toISOString()).toBe(touchedResult.updatedAt);

    // N3 (load-bearing): the sibling written by an earlier, separate upsertVideo
    // call must not be re-stamped by this later, unrelated write.
    expect(siblingResult.updatedAt).toBe(siblingBefore.updatedAt);
    expect(siblingResult).toEqual(siblingBefore);
  });
});
