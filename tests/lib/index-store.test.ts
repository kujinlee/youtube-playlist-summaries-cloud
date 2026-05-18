import fs from 'fs';
import os from 'os';
import path from 'path';
import { readIndex, writeIndex, upsertVideo, updateVideoFields } from '../../lib/index-store';
import type { PlaylistIndex, Video } from '../../types';

const TEST_DIR = path.join(os.homedir(), `.test-index-store-${Date.now()}`);

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
    summaryPdf: null,
    deepDiveMd: null,
    deepDivePdf: null,
    processedAt: '2024-01-01T00:00:00.000Z',
    ...overrides,
  };
}

beforeAll(() => fs.mkdirSync(TEST_DIR, { recursive: true }));
afterAll(() => fs.rmSync(TEST_DIR, { recursive: true, force: true }));

describe('readIndex', () => {
  it('returns empty index when file is missing', () => {
    const dir = path.join(TEST_DIR, 'empty');
    fs.mkdirSync(dir, { recursive: true });

    const result = readIndex(dir);

    expect(result.videos).toEqual([]);
    expect(result.outputFolder).toBe(dir);
  });
});

describe('writeIndex + readIndex', () => {
  it('round-trip preserves all fields', () => {
    const dir = path.join(TEST_DIR, 'roundtrip');
    fs.mkdirSync(dir, { recursive: true });

    const index: PlaylistIndex = {
      playlistUrl: 'https://www.youtube.com/playlist?list=PLtest123',
      outputFolder: dir,
      videos: [makeVideo()],
    };

    writeIndex(dir, index);
    const result = readIndex(dir);

    expect(result).toEqual(index);
  });
});

describe('upsertVideo', () => {
  it('adds a new video to an empty index', () => {
    const dir = path.join(TEST_DIR, 'upsert-add');
    fs.mkdirSync(dir, { recursive: true });

    const video = makeVideo({ id: 'vid111111111' });
    upsertVideo(dir, video);

    const result = readIndex(dir);
    expect(result.videos).toHaveLength(1);
    expect(result.videos[0]).toEqual(video);
  });

  it('replaces existing video by ID without adding a duplicate', () => {
    const dir = path.join(TEST_DIR, 'upsert-replace');
    fs.mkdirSync(dir, { recursive: true });

    const original = makeVideo({ id: 'vid222222222', title: 'Original' });
    const updated = makeVideo({ id: 'vid222222222', title: 'Updated' });

    upsertVideo(dir, original);
    upsertVideo(dir, updated);

    const result = readIndex(dir);
    expect(result.videos).toHaveLength(1);
    expect(result.videos[0].title).toBe('Updated');
  });
});

describe('updateVideoFields', () => {
  it('merges specified fields without losing unspecified ones', () => {
    const dir = path.join(TEST_DIR, 'update-fields');
    fs.mkdirSync(dir, { recursive: true });

    const video = makeVideo({ id: 'vid333333333', summaryMd: null });
    upsertVideo(dir, video);

    updateVideoFields(dir, 'vid333333333', { summaryMd: 'vid333333333.md', summaryPdf: 'vid333333333.pdf' });

    const result = readIndex(dir);
    expect(result.videos[0].summaryMd).toBe('vid333333333.md');
    expect(result.videos[0].summaryPdf).toBe('vid333333333.pdf');
    expect(result.videos[0].title).toBe(video.title);
    expect(result.videos[0].ratings).toEqual(video.ratings);
  });
});
