jest.mock('../../lib/index-store');
jest.mock('../../lib/gemini');
jest.mock('../../lib/pipeline', () => ({
  ...jest.requireActual('../../lib/pipeline'),
  stripQuickViewCallout: jest.fn((s: string) => s),
  insertQuickViewCallout: jest.fn((_md: string, tldr: string, takeaways: string[]) => `CALLOUT:${tldr}:${takeaways.join(',')}`),
}));
jest.mock('../../lib/storage/resolve', () => ({
  ...jest.requireActual('../../lib/storage/resolve'),
  getStorageBundle: jest.fn(),
}));
jest.mock('fs', () => ({
  ...jest.requireActual('fs'),
  promises: {
    readFile: jest.fn(),
    writeFile: jest.fn(),
  },
}));

import { POST } from '../../app/api/videos/[id]/regenerate/route';
import * as indexStore from '../../lib/index-store';
import * as gemini from '../../lib/gemini';
import * as fs from 'fs';
import * as resolve from '../../lib/storage/resolve';

const mockReadIndex = jest.mocked(indexStore.readIndex);
const mockAssertOutputFolder = jest.mocked(indexStore.assertOutputFolder);
const mockAssertVideoId = jest.mocked(indexStore.assertVideoId);
const mockUpdateVideoFields = jest.mocked(indexStore.updateVideoFields);
const mockFixSummary = jest.mocked(gemini.fixSummary);
const mockExtractQuickView = jest.mocked(gemini.extractQuickView);
const mockReadFile = jest.mocked(fs.promises.readFile);
const mockWriteFile = jest.mocked(fs.promises.writeFile);
const mockUpdateVideoAnnotations = jest.fn();
const mockGetStorageBundle = jest.mocked(resolve.getStorageBundle);

const OUTPUT_FOLDER = '/tmp/out';
const VIDEO_ID = 'testVideoId1';
const SUMMARY_MD = 'test-video.md';
const MD_CONTENT = '# Title\n\n**URL:** https://youtube.com/watch?v=testVideoId1\n\n---\n\n## 1. Intro\nContent.';

function post(videoId: string, body: Record<string, unknown>) {
  return POST(
    new Request('http://localhost/api/videos/test/regenerate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }),
    { params: Promise.resolve({ id: videoId }) },
  );
}

const baseVideo = {
  id: VIDEO_ID,
  title: 'Test Video',
  summaryMd: SUMMARY_MD,
  tags: ['ai', 'rag'],
  tldr: 'Old TL;DR.',
  takeaways: ['Old point'],
};

const baseIndex = {
  playlistUrl: 'https://youtube.com/playlist?list=PL1',
  outputFolder: OUTPUT_FOLDER,
  videos: [baseVideo],
};

beforeEach(() => {
  jest.clearAllMocks();
  mockAssertOutputFolder.mockImplementation(() => {});
  mockAssertVideoId.mockImplementation(() => {});
  mockReadIndex.mockReturnValue(baseIndex as any);
  mockReadFile.mockResolvedValue(MD_CONTENT as any);
  mockWriteFile.mockResolvedValue(undefined);
  mockUpdateVideoAnnotations.mockResolvedValue({ found: true });
  // DELEGATE to the real local bundle and stub ONLY updateVideoAnnotations. The plan replaced the
  // whole metadataStore with { readIndex: mockReadIndex, updateVideoFields: mockUpdateVideoFields,
  // … }, which silently changes updateVideoFields' arguments from (OUTPUT_FOLDER, id, patch) —
  // what the local adapter passes down to index-store — to (principal, id, patch), breaking every
  // existing assertion in this file. Keeping the real adapter means those keep testing what they
  // always tested.
  const realBundle = jest.requireActual('../../lib/storage/resolve').getStorageBundle();
  mockGetStorageBundle.mockReturnValue({
    ...realBundle,
    metadataStore: {
      readIndex: (...a: unknown[]) => (realBundle.metadataStore.readIndex as (...x: unknown[]) => unknown)(...a),
      updateVideoFields: (...a: unknown[]) => (realBundle.metadataStore.updateVideoFields as (...x: unknown[]) => unknown)(...a),
      updateVideoAnnotations: mockUpdateVideoAnnotations,
    },
  } as unknown as ReturnType<typeof resolve.getStorageBundle>);
  mockFixSummary.mockResolvedValue({ text: MD_CONTENT, usage: null });
  mockExtractQuickView.mockResolvedValue({
    tldr: 'This video teaches X.',
    takeaways: ['Point one', 'Point two'],
  });
});

describe('POST /api/videos/[id]/regenerate', () => {
  it('returns 400 when outputFolder is missing', async () => {
    const res = await post(VIDEO_ID, {});
    expect(res.status).toBe(400);
  });

  it('returns 400 when videoId is invalid', async () => {
    mockAssertVideoId.mockImplementation(() => { throw new Error('bad id'); });
    const res = await post('bad id!', { outputFolder: OUTPUT_FOLDER });
    expect(res.status).toBe(400);
  });

  it('returns 404 when video is not in index', async () => {
    mockReadIndex.mockReturnValue({ ...baseIndex, videos: [] } as any);
    const res = await post(VIDEO_ID, { outputFolder: OUTPUT_FOLDER });
    expect(res.status).toBe(404);
  });

  it('returns 422 when video has no summaryMd', async () => {
    mockReadIndex.mockReturnValue({
      ...baseIndex,
      videos: [{ ...baseVideo, summaryMd: null }],
    } as any);
    const res = await post(VIDEO_ID, { outputFolder: OUTPUT_FOLDER });
    expect(res.status).toBe(422);
  });

  it('calls fixSummary when corrections are provided', async () => {
    const corrections = "Fix 'Clawcode' → 'Claude Code'";
    await post(VIDEO_ID, { outputFolder: OUTPUT_FOLDER, corrections });
    // Third argument added by T5. Asserted as a real AbortSignal rather than `expect.anything()`:
    // the whole point of making `opts` required is that the route forwards the REQUEST's signal, and
    // `anything()` would pass on `{}`.
    expect(mockFixSummary).toHaveBeenCalledWith(
      MD_CONTENT,
      corrections,
      expect.objectContaining({ signal: expect.any(AbortSignal) }),
    );
  });

  it('does not call fixSummary when corrections is empty string', async () => {
    await post(VIDEO_ID, { outputFolder: OUTPUT_FOLDER, corrections: '' });
    expect(mockFixSummary).not.toHaveBeenCalled();
  });

  it('does not call fixSummary when corrections is absent', async () => {
    await post(VIDEO_ID, { outputFolder: OUTPUT_FOLDER });
    expect(mockFixSummary).not.toHaveBeenCalled();
  });

  it('saves corrections before the Gemini call', async () => {
    const corrections = 'Fix spelling';
    await post(VIDEO_ID, { outputFolder: OUTPUT_FOLDER, corrections });
    // Watches updateVideoAnnotations, not updateVideoFields: T6 moved the corrections write to the
    // annotations surface, so the FIRST updateVideoFields call is now the post-Gemini currency
    // stamp — this assertion inverted and caught it. The property under test is unchanged and still
    // worth pinning: the user's text is durable before anything paid runs, so a Gemini failure
    // cannot lose what they typed.
    const annotationCalls = mockUpdateVideoAnnotations.mock.invocationCallOrder;
    const fixCalls = mockFixSummary.mock.invocationCallOrder;
    expect(annotationCalls[0]).toBeLessThan(fixCalls[0]);
  });

  it('returns 200 with new tldr, takeaways on success', async () => {
    const res = await post(VIDEO_ID, { outputFolder: OUTPUT_FOLDER });
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.tldr).toBe('This video teaches X.');
    expect(body.takeaways).toEqual(['Point one', 'Point two']);
  });

  it('returns 200 and echoes corrections in response', async () => {
    const corrections = 'Fix Clawcode';
    const res = await post(VIDEO_ID, { outputFolder: OUTPUT_FOLDER, corrections });
    const body = await res.json();
    expect(body.corrections).toBe('Fix Clawcode');
  });

  it('updates the index with new tldr and takeaways', async () => {
    await post(VIDEO_ID, { outputFolder: OUTPUT_FOLDER });
    expect(mockUpdateVideoFields).toHaveBeenCalledWith(
      OUTPUT_FOLDER,
      VIDEO_ID,
      expect.objectContaining({ tldr: 'This video teaches X.', takeaways: ['Point one', 'Point two'] }),
    );
  });

  it('returns 500 when Gemini throws', async () => {
    mockExtractQuickView.mockRejectedValueOnce(new Error('Gemini failed'));
    const res = await post(VIDEO_ID, { outputFolder: OUTPUT_FOLDER });
    expect(res.status).toBe(500);
    const body = await res.json();
    expect(body.error).toMatch(/Gemini failed/);
  });

  it('clears summaryHtml in the index update on success', async () => {
    await post(VIDEO_ID, { outputFolder: OUTPUT_FOLDER });
    expect(mockUpdateVideoFields).toHaveBeenCalledWith(
      OUTPUT_FOLDER,
      VIDEO_ID,
      expect.objectContaining({ summaryHtml: null }),
    );
  });

  it('includes summaryHtml: null in the JSON response on success', async () => {
    const res = await post(VIDEO_ID, { outputFolder: OUTPUT_FOLDER });
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body).toEqual(expect.objectContaining({ summaryHtml: null }));
  });
});

describe('bare press does not rewrite the file (spec §2, r5 B1)', () => {
  it('writes the file when corrections were applied', async () => {
    await post(VIDEO_ID, { outputFolder: OUTPUT_FOLDER, corrections: 'fix Clawcode' });
    expect(mockWriteFile).toHaveBeenCalledTimes(1);
  });

  it('does NOT write the file on a bare press (no corrections key)', async () => {
    await post(VIDEO_ID, { outputFolder: OUTPUT_FOLDER });
    expect(mockFixSummary).not.toHaveBeenCalled();
    expect(mockWriteFile).not.toHaveBeenCalled();
  });

  it('does NOT write the file on a whitespace-only press', async () => {
    await post(VIDEO_ID, { outputFolder: OUTPUT_FOLDER, corrections: '   ' });
    expect(mockWriteFile).not.toHaveBeenCalled();
  });

  it('does NOT write the file on an explicit clear', async () => {
    await post(VIDEO_ID, { outputFolder: OUTPUT_FOLDER, corrections: '' });
    expect(mockWriteFile).not.toHaveBeenCalled();
  });

  it('still refreshes tldr/takeaways on a bare press — quick-view stays unconditional', async () => {
    const res = await post(VIDEO_ID, { outputFolder: OUTPUT_FOLDER });
    expect(mockExtractQuickView).toHaveBeenCalledTimes(1);
    expect((await res.json()).tldr).toBe('This video teaches X.');
  });
});

describe('corrections are written through updateVideoAnnotations (spec §4.1)', () => {
  it('SETS corrections when the incoming text differs from the stored text', async () => {
    await post(VIDEO_ID, { outputFolder: OUTPUT_FOLDER, corrections: 'fix Clawcode' });
    expect(mockUpdateVideoAnnotations).toHaveBeenCalledWith(
      expect.anything(), VIDEO_ID, { corrections: 'fix Clawcode' }, [],
    );
  });

  it('CLEARS via the clear array, never via corrections: undefined', async () => {
    mockReadIndex.mockReturnValue({ ...baseIndex, videos: [{ ...baseVideo, corrections: 'old' }] } as any);
    await post(VIDEO_ID, { outputFolder: OUTPUT_FOLDER, corrections: '' });
    expect(mockUpdateVideoAnnotations).toHaveBeenCalledWith(
      expect.anything(), VIDEO_ID, {}, ['corrections'],
    );
  });

  it('issues NO call when the incoming text equals the stored text', async () => {
    mockReadIndex.mockReturnValue({ ...baseIndex, videos: [{ ...baseVideo, corrections: 'same' }] } as any);
    await post(VIDEO_ID, { outputFolder: OUTPUT_FOLDER, corrections: 'same' });
    expect(mockUpdateVideoAnnotations).not.toHaveBeenCalled();
  });

  it('issues NO call when clearing an ALREADY-EMPTY field', async () => {
    mockReadIndex.mockReturnValue({ ...baseIndex, videos: [{ ...baseVideo, corrections: undefined }] } as any);
    await post(VIDEO_ID, { outputFolder: OUTPUT_FOLDER, corrections: '' });
    expect(mockUpdateVideoAnnotations).not.toHaveBeenCalled();
  });

  it('404s when the annotations write reports the row was not found', async () => {
    mockUpdateVideoAnnotations.mockResolvedValue({ found: false });
    const res = await post(VIDEO_ID, { outputFolder: OUTPUT_FOLDER, corrections: 'fix X' });
    expect(res.status).toBe(404);
    expect((await res.json()).error).toBe('video not found');
  });

  it('does NOT reach Gemini when the annotations write 404s', async () => {
    // Added beyond the plan: the 404 is a PRE-Gemini guard, and a test asserting only the status
    // would pass on an implementation that returned 404 AFTER paying for the correction.
    mockUpdateVideoAnnotations.mockResolvedValue({ found: false });
    await post(VIDEO_ID, { outputFolder: OUTPUT_FOLDER, corrections: 'fix X' });
    expect(mockFixSummary).not.toHaveBeenCalled();
  });
});
