jest.mock('../../lib/index-store');

import * as fs from 'fs';
import * as path from 'path';
import * as os from 'os';
import * as crypto from 'crypto';
import { GET } from '../../app/api/pdf/[id]/route';
import * as indexStore from '../../lib/index-store';
import type { PlaylistIndex } from '../../types';

const mockAssertOutputFolder = jest.mocked(indexStore.assertOutputFolder);
const mockAssertVideoId = jest.mocked(indexStore.assertVideoId);
const mockReadIndex = jest.mocked(indexStore.readIndex);

const OUTPUT_FOLDER = '/tmp/out';

function fakeIndex(summaryPdf: string | null, deepDivePdf: string | null = null): PlaylistIndex {
  return {
    playlistUrl: 'https://youtube.com/playlist?list=PL',
    outputFolder: OUTPUT_FOLDER,
    videos: [
      {
        id: 'vid1',
        title: 'Test',
        youtubeUrl: 'https://www.youtube.com/watch?v=vid1',
        language: 'en',
        durationSeconds: 600,
        archived: false,
        ratings: { usefulness: 4, depth: 4, originality: 4, recency: 4, completeness: 4 },
        overallScore: 4,
        summaryMd: summaryPdf?.replace(/\.pdf$/, '.md') ?? null,
        summaryPdf,
        deepDiveMd: deepDivePdf?.replace(/\.pdf$/, '.md') ?? null,
        deepDivePdf,
        processedAt: '2026-01-01T00:00:00.000Z',
      },
    ],
  };
}

function getPdf(videoId: string, params: Record<string, string> = {}) {
  const query = new URLSearchParams({ outputFolder: OUTPUT_FOLDER, ...params }).toString();
  return GET(
    new Request(`http://localhost/api/pdf/${videoId}?${query}`),
    { params: Promise.resolve({ id: videoId }) },
  );
}

describe('GET /api/pdf/[id]', () => {
  let tempDir: string;

  beforeEach(() => {
    tempDir = path.join(os.tmpdir(), `pdf-test-${crypto.randomUUID()}`);
    fs.mkdirSync(tempDir, { recursive: true });
    mockAssertOutputFolder.mockImplementation(() => {});
    mockAssertVideoId.mockImplementation(() => {});
    mockReadIndex.mockReturnValue(fakeIndex('vid1.pdf'));
  });

  afterEach(() => {
    fs.rmSync(tempDir, { recursive: true, force: true });
    jest.clearAllMocks();
  });

  it('returns 400 when outputFolder is missing', async () => {
    const res = await GET(
      new Request('http://localhost/api/pdf/vid1'),
      { params: Promise.resolve({ id: 'vid1' }) },
    );
    expect(res.status).toBe(400);
  });

  it('returns 400 for invalid videoId', async () => {
    mockAssertVideoId.mockImplementation(() => { throw Object.assign(new Error('invalid'), { statusCode: 400 }); });
    const res = await getPdf('../etc/passwd', { outputFolder: tempDir });
    expect(res.status).toBe(400);
  });

  it('returns 404 when video not found in index', async () => {
    mockReadIndex.mockReturnValue({ ...fakeIndex('vid1.pdf'), videos: [] });
    const res = await getPdf('vid1', { outputFolder: tempDir });
    expect(res.status).toBe(404);
    const body = await res.json();
    expect(body.error).toBe('video not found');
  });

  it('returns 404 when summaryPdf is null', async () => {
    mockReadIndex.mockReturnValue(fakeIndex(null));
    const res = await getPdf('vid1', { outputFolder: tempDir });
    expect(res.status).toBe(404);
    const body = await res.json();
    expect(body.error).toBe('pdf not available');
  });

  it('returns 404 when PDF file does not exist on disk', async () => {
    mockReadIndex.mockReturnValue(fakeIndex('vid1.pdf'));
    const res = await getPdf('vid1', { outputFolder: tempDir });
    expect(res.status).toBe(404);
  });

  it('returns 200 with application/pdf when summary file exists', async () => {
    mockReadIndex.mockReturnValue(fakeIndex('vid1.pdf'));
    fs.writeFileSync(path.join(tempDir, 'vid1.pdf'), '%PDF-1.4 fake content');

    const res = await getPdf('vid1', { outputFolder: tempDir });
    expect(res.status).toBe(200);
    expect(res.headers.get('Content-Type')).toBe('application/pdf');
  });

  it('returns 200 for deep-dive PDF when it exists', async () => {
    mockReadIndex.mockReturnValue(fakeIndex('vid1.pdf', 'vid1-deep-dive.pdf'));
    fs.writeFileSync(path.join(tempDir, 'vid1-deep-dive.pdf'), '%PDF-1.4 deep dive');

    const res = await getPdf('vid1', { outputFolder: tempDir, type: 'deep-dive' });
    expect(res.status).toBe(200);
    expect(res.headers.get('Content-Type')).toBe('application/pdf');
  });

  it('returns 404 when type=deep-dive and deepDivePdf is null', async () => {
    mockReadIndex.mockReturnValue(fakeIndex('vid1.pdf', null));
    const res = await getPdf('vid1', { outputFolder: tempDir, type: 'deep-dive' });
    expect(res.status).toBe(404);
    const body = await res.json();
    expect(body.error).toBe('pdf not available');
  });
});
