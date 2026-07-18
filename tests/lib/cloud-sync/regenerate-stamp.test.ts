// tests/lib/cloud-sync/regenerate-stamp.test.ts
//
// Drives the regenerate route (mocked at the index-store boundary, mirroring
// tests/api/regenerate.test.ts) and asserts the SECOND updateVideoFields call — the one
// that persists refreshed tldr/takeaways/summaryHtml — also stamps mdGeneratedAt and
// mdCorrectionsHash = mdHash(effectiveCorrections). This guards former-Blocking §5.3: a
// corrected MD that is never marked corrections-current is judged stale forever.
jest.mock('../../../lib/index-store');
jest.mock('../../../lib/gemini');
jest.mock('../../../lib/pipeline', () => ({
  ...jest.requireActual('../../../lib/pipeline'),
  stripQuickViewCallout: jest.fn((s: string) => s),
  insertQuickViewCallout: jest.fn((_md: string, tldr: string, takeaways: string[]) => `CALLOUT:${tldr}:${takeaways.join(',')}`),
}));
jest.mock('fs', () => ({
  ...jest.requireActual('fs'),
  promises: {
    readFile: jest.fn(),
    writeFile: jest.fn(),
  },
}));

import { POST } from '../../../app/api/videos/[id]/regenerate/route';
import * as indexStore from '../../../lib/index-store';
import * as gemini from '../../../lib/gemini';
import * as fs from 'fs';
import { mdHash } from '../../../lib/cloud-sync/content-hash';

const mockReadIndex = jest.mocked(indexStore.readIndex);
const mockAssertOutputFolder = jest.mocked(indexStore.assertOutputFolder);
const mockAssertVideoId = jest.mocked(indexStore.assertVideoId);
const mockUpdateVideoFields = jest.mocked(indexStore.updateVideoFields);
const mockFixSummary = jest.mocked(gemini.fixSummary);
const mockExtractQuickView = jest.mocked(gemini.extractQuickView);
const mockReadFile = jest.mocked(fs.promises.readFile);
const mockWriteFile = jest.mocked(fs.promises.writeFile);

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
  corrections: 'old corrections',
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
  mockFixSummary.mockResolvedValue(MD_CONTENT);
  mockExtractQuickView.mockResolvedValue({
    tldr: 'This video teaches X.',
    takeaways: ['Point one', 'Point two'],
  });
});

describe('regenerate route — currency stamping', () => {
  it('a regenerated MD is stamped corrections-current with the new corrections', async () => {
    const res = await post(VIDEO_ID, { outputFolder: OUTPUT_FOLDER, corrections: 'fix name' });
    expect(res.status).toBe(200);
    expect(mockUpdateVideoFields).toHaveBeenLastCalledWith(
      OUTPUT_FOLDER,
      VIDEO_ID,
      expect.objectContaining({
        mdCorrectionsHash: mdHash('fix name'),
        mdGeneratedAt: expect.any(String),
      }),
    );
  });

  it('a bare regenerate (no corrections param) stamps against the UNCHANGED stored corrections', async () => {
    await post(VIDEO_ID, { outputFolder: OUTPUT_FOLDER });
    expect(mockUpdateVideoFields).toHaveBeenLastCalledWith(
      OUTPUT_FOLDER,
      VIDEO_ID,
      expect.objectContaining({
        mdCorrectionsHash: mdHash('old corrections'),
        mdGeneratedAt: expect.any(String),
      }),
    );
  });

  it('an explicit clear (corrections === "") stamps against empty corrections', async () => {
    await post(VIDEO_ID, { outputFolder: OUTPUT_FOLDER, corrections: '' });
    expect(mockUpdateVideoFields).toHaveBeenLastCalledWith(
      OUTPUT_FOLDER,
      VIDEO_ID,
      expect.objectContaining({
        mdCorrectionsHash: mdHash(''),
        mdGeneratedAt: expect.any(String),
      }),
    );
  });

  it('the currency-stamp call does not also carry a Class-B key (it is a separate write)', async () => {
    await post(VIDEO_ID, { outputFolder: OUTPUT_FOLDER, corrections: 'fix name' });
    const lastCall = mockUpdateVideoFields.mock.calls[mockUpdateVideoFields.mock.calls.length - 1];
    expect(lastCall[2]).not.toHaveProperty('corrections');
  });
});
