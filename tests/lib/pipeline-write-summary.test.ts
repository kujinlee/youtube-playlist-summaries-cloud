import os from 'os';
import fs from 'fs';
import path from 'path';
import { localBlobStore } from '@/lib/storage/local/local-blob-store';
import { localPrincipal } from '@/lib/storage/principal';

jest.mock('../../lib/youtube', () => ({
  fetchTranscriptSegments: jest.fn().mockResolvedValue([{ text: 'hi', offset: 0, duration: 5 }]),
  detectLanguage: jest.fn().mockReturnValue('en'),
  fetchPlaylistVideos: jest.fn(),
}));
jest.mock('../../lib/gemini', () => ({
  generateSummary: jest.fn().mockResolvedValue({
    summary: '## 1. Alpha\n▶ [0:00](u)\nAlpha body.\n---\n## Conclusion\n▶ [1:00](u)\nWrap.',
    ratings: { usefulness: 4, depth: 4, originality: 4, recency: 4, completeness: 4 },
    overallScore: 4, videoType: 'Analysis', audience: 'Intermediate',
    tags: ['x'], tldr: 'This video explains alpha.', takeaways: ['Do alpha'],
  }),
}));

import { writeSummaryDoc } from '../../lib/pipeline';

it('pads in-body --- dividers so section bodies are not setext headings', async () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'wsd-'));
  const res = await writeSummaryDoc({
    videoId: 'vid', title: 'T', youtubeUrl: 'https://y/watch?v=vid',
    channel: 'C', durationSeconds: 90, outputFolder: dir, baseName: '1_t',
  });
  expect(res.mdContent).toContain('Alpha body.\n\n---\n\n## Conclusion');
  expect(res.mdContent).not.toContain('Alpha body.\n---\n## Conclusion');
  // Quick-view callout still inserted at the metadata divider — BEFORE the first section heading.
  expect(res.mdContent).toContain('> **Concepts:**');
  expect(res.mdContent.indexOf('This video explains alpha.')).toBeLessThan(
    res.mdContent.indexOf('## 1. Alpha'),
  );
});

it('pads body dividers even when there is no quick-view (no tldr/takeaways)', async () => {
  const { generateSummary } = require('../../lib/gemini');
  (generateSummary as jest.Mock).mockResolvedValueOnce({
    summary: '## 1. Alpha\n▶ [0:00](u)\nAlpha body.\n---\n## Conclusion\n▶ [1:00](u)\nWrap.',
    ratings: { usefulness: 4, depth: 4, originality: 4, recency: 4, completeness: 4 },
    overallScore: 4, videoType: 'Analysis', audience: 'Intermediate', tags: ['x'],
    tldr: undefined, takeaways: undefined,
  });
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'wsd-'));
  const res = await writeSummaryDoc({
    videoId: 'vid', title: 'T', youtubeUrl: 'https://y/watch?v=vid',
    channel: 'C', durationSeconds: 90, outputFolder: dir, baseName: '1_t',
  });
  expect(res.mdContent).toContain('Alpha body.\n\n---\n\n## Conclusion');
  expect(res.mdContent).not.toContain('> **Concepts:**');
});

it('routes MD write through blobStore.put with key <baseName>.md', async () => {
  const fakePut = jest.fn(async (_p: unknown, _k: unknown, _b: unknown, _c: unknown) => {});
  const fakeBlobStore = Object.assign(Object.create(Object.getPrototypeOf(localBlobStore)), localBlobStore, { put: fakePut }) as typeof localBlobStore;
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'wsd-'));
  await writeSummaryDoc({
    videoId: 'vid', title: 'T', youtubeUrl: 'https://y/watch?v=vid',
    channel: 'C', durationSeconds: 90, outputFolder: dir, baseName: '1_t',
    blobStore: fakeBlobStore,
  });
  expect(fakePut).toHaveBeenCalledWith(
    localPrincipal(dir),
    '1_t.md',
    expect.any(Buffer),
    'text/markdown',
  );
  const buf = fakePut.mock.calls[0]?.[2] as Buffer | undefined;
  expect(buf?.toString('utf-8')).toContain('Alpha body.');
});
