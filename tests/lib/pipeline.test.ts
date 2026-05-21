import crypto from 'crypto';
import * as fs from 'fs';
import * as os from 'os';
import * as path from 'path';
import type { ProgressEvent, VideoMeta, GeminiSummaryResponse } from '../../types';

jest.mock('../../lib/youtube');
jest.mock('../../lib/gemini');
jest.mock('../../lib/pdf');
jest.mock('../../lib/index-store');

import { runIngestion, slugify, formatDuration } from '../../lib/pipeline';
import * as youtube from '../../lib/youtube';
import * as gemini from '../../lib/gemini';
import * as pdf from '../../lib/pdf';
import * as indexStore from '../../lib/index-store';

const mockFetchPlaylistVideos = jest.mocked(youtube.fetchPlaylistVideos);
const mockFetchTranscript = jest.mocked(youtube.fetchTranscript);
const mockDetectLanguage = jest.mocked(youtube.detectLanguage);
const mockGenerateSummary = jest.mocked(gemini.generateSummary);
const mockGeneratePdf = jest.mocked(pdf.generatePdf);
const mockUpsertVideo = jest.mocked(indexStore.upsertVideo);
const mockAssertOutputFolder = jest.mocked(indexStore.assertOutputFolder);
const mockReadIndex = jest.mocked(indexStore.readIndex);
const mockWriteIndex = jest.mocked(indexStore.writeIndex);

const PLAYLIST_URL = 'https://youtube.com/playlist?list=PLtest';

// Use os.tmpdir() — assertOutputFolder is mocked so homedir restriction doesn't apply
function makeTempDir(): string {
  const dir = path.join(os.tmpdir(), `pipeline-test-${crypto.randomUUID()}`);
  fs.mkdirSync(dir, { recursive: true });
  return dir;
}

function makeVideoMeta(id: string): VideoMeta {
  return {
    videoId: id,
    title: `Video ${id}`,
    youtubeUrl: `https://youtube.com/watch?v=${id}`,
    durationSeconds: 300,
  };
}

function makeSummaryResponse(overrides: Partial<GeminiSummaryResponse> = {}): GeminiSummaryResponse {
  return {
    summary: 'A great summary',
    ratings: { usefulness: 3, depth: 3, originality: 3, recency: 3, completeness: 3 },
    overallScore: 3,
    ...overrides,
  };
}

describe('runIngestion', () => {
  let outputFolder: string;

  beforeEach(() => {
    outputFolder = makeTempDir();
    process.env.YOUTUBE_API_KEY = 'test-key';

    mockAssertOutputFolder.mockImplementation(() => {});
    mockDetectLanguage.mockReturnValue('en');
    mockGeneratePdf.mockResolvedValue(undefined);
    mockUpsertVideo.mockImplementation(() => {});
    mockReadIndex.mockReturnValue({ playlistUrl: '', outputFolder, videos: [] });
    mockWriteIndex.mockImplementation(() => {});
  });

  afterEach(() => {
    fs.rmSync(outputFolder, { recursive: true, force: true });
    jest.clearAllMocks();
  });

  it('emits start event first and done event last for a successful pipeline', async () => {
    mockFetchPlaylistVideos.mockResolvedValue([makeVideoMeta('vid1'), makeVideoMeta('vid2')]);
    mockFetchTranscript.mockResolvedValue('transcript');
    mockGenerateSummary.mockResolvedValue(makeSummaryResponse());

    const events: ProgressEvent[] = [];
    await runIngestion(PLAYLIST_URL, outputFolder, (e) => events.push(e));

    expect(events[0]).toMatchObject({ type: 'start', total: 2 });
    expect(events[events.length - 1]).toMatchObject({ type: 'done' });
    expect(events.some((e) => e.type === 'step' && 'videoId' in e && e.videoId === 'vid1')).toBe(true);
    expect(events.some((e) => e.type === 'step' && 'videoId' in e && e.videoId === 'vid2')).toBe(true);
    // Per-video completion event
    expect(events.some((e) => e.type === 'step' && 'step' in e && e.step === 'Saved' && 'videoId' in e && e.videoId === 'vid1')).toBe(true);
  });

  it('continues to next video when one video fails', async () => {
    mockFetchPlaylistVideos.mockResolvedValue([makeVideoMeta('vid1'), makeVideoMeta('vid2')]);
    mockFetchTranscript
      .mockRejectedValueOnce(new Error('No transcript available'))
      .mockResolvedValueOnce('transcript');
    mockGenerateSummary.mockResolvedValue(makeSummaryResponse());

    const events: ProgressEvent[] = [];
    await runIngestion(PLAYLIST_URL, outputFolder, (e) => events.push(e));

    const errorEvents = events.filter((e) => e.type === 'error');
    expect(errorEvents).toHaveLength(1);
    expect(errorEvents[0]).toMatchObject({ type: 'error', videoId: 'vid1' });

    expect(mockUpsertVideo).toHaveBeenCalledTimes(1);
    expect(mockUpsertVideo).toHaveBeenCalledWith(outputFolder, expect.objectContaining({ id: 'vid2' }));
    expect(events[events.length - 1]).toMatchObject({ type: 'done' });
  });

  it('upserts all successfully processed videos to the index', async () => {
    mockFetchPlaylistVideos.mockResolvedValue([makeVideoMeta('vid1'), makeVideoMeta('vid2')]);
    mockFetchTranscript.mockResolvedValue('transcript');
    mockGenerateSummary.mockResolvedValue(makeSummaryResponse());

    await runIngestion(PLAYLIST_URL, outputFolder, () => {});

    expect(mockUpsertVideo).toHaveBeenCalledTimes(2);
    expect(mockUpsertVideo).toHaveBeenCalledWith(outputFolder, expect.objectContaining({ id: 'vid1' }));
    expect(mockUpsertVideo).toHaveBeenCalledWith(outputFolder, expect.objectContaining({ id: 'vid2' }));
  });

  it('stores overallScore from generateSummary in the index entry', async () => {
    const ratings = { usefulness: 4, depth: 3, originality: 5, recency: 2, completeness: 1 } as const;
    const overallScore = (4 + 3 + 5 + 2 + 1) / 5; // 3
    mockFetchPlaylistVideos.mockResolvedValue([makeVideoMeta('vid1')]);
    mockFetchTranscript.mockResolvedValue('transcript');
    mockGenerateSummary.mockResolvedValue({ summary: 'S', ratings, overallScore });

    await runIngestion(PLAYLIST_URL, outputFolder, () => {});

    expect(mockUpsertVideo).toHaveBeenCalledWith(
      outputFolder,
      expect.objectContaining({ overallScore }),
    );
  });

  it('stores videoType and audience from generateSummary in the index entry', async () => {
    mockFetchPlaylistVideos.mockResolvedValue([makeVideoMeta('vid1')]);
    mockFetchTranscript.mockResolvedValue('transcript');
    mockGenerateSummary.mockResolvedValue(
      makeSummaryResponse({ videoType: 'Tutorial', audience: 'Advanced' }),
    );

    await runIngestion(PLAYLIST_URL, outputFolder, () => {});

    expect(mockUpsertVideo).toHaveBeenCalledWith(
      outputFolder,
      expect.objectContaining({ videoType: 'Tutorial', audience: 'Advanced' }),
    );
  });

  it('omits videoType and audience from index entry when generateSummary does not return them', async () => {
    mockFetchPlaylistVideos.mockResolvedValue([makeVideoMeta('vid1')]);
    mockFetchTranscript.mockResolvedValue('transcript');
    mockGenerateSummary.mockResolvedValue(makeSummaryResponse());

    await runIngestion(PLAYLIST_URL, outputFolder, () => {});

    const call = mockUpsertVideo.mock.calls[0][1];
    expect(call.videoType).toBeUndefined();
    expect(call.audience).toBeUndefined();
  });

  it('stamps playlistUrl into the index before processing videos', async () => {
    mockFetchPlaylistVideos.mockResolvedValue([]);
    mockReadIndex.mockReturnValue({ playlistUrl: '', outputFolder, videos: [] });

    await runIngestion(PLAYLIST_URL, outputFolder, () => {});

    expect(mockWriteIndex).toHaveBeenCalledWith(
      outputFolder,
      expect.objectContaining({ playlistUrl: PLAYLIST_URL }),
    );
  });

  it('uses rank-prefixed slug filename for first video (i=0 → 001)', async () => {
    const meta = { ...makeVideoMeta('vid1'), title: 'Hello World' };
    mockFetchPlaylistVideos.mockResolvedValue([meta]);
    mockFetchTranscript.mockResolvedValue('transcript');
    mockGenerateSummary.mockResolvedValue(makeSummaryResponse());

    await runIngestion(PLAYLIST_URL, outputFolder, () => {});

    expect(mockUpsertVideo).toHaveBeenCalledWith(
      outputFolder,
      expect.objectContaining({
        summaryMd: expect.stringMatching(/^001_hello-world\.md$/),
        summaryPdf: expect.stringMatching(/^001_hello-world\.pdf$/),
      }),
    );
  });

  it('writes markdown file starting with YAML frontmatter (--- tags:)', async () => {
    const meta = { ...makeVideoMeta('vid1'), title: 'Test Video', channelTitle: 'Test Channel' };
    mockFetchPlaylistVideos.mockResolvedValue([meta]);
    mockFetchTranscript.mockResolvedValue('transcript');
    mockGenerateSummary.mockResolvedValue(
      makeSummaryResponse({ videoType: 'Tutorial', audience: 'Beginner', tags: ['ml', 'python'] }),
    );

    await runIngestion(PLAYLIST_URL, outputFolder, () => {});

    const files = fs.readdirSync(outputFolder).filter((f) => f.endsWith('.md'));
    expect(files).toHaveLength(1);
    const content = fs.readFileSync(path.join(outputFolder, files[0]), 'utf-8');
    expect(content).toMatch(/^---\ntags:/);
    expect(content).toMatch(/video_id: "vid1"/);
    expect(content).toMatch(/channel: "Test Channel"/);
    expect(content).toMatch(/lang: EN/);
    expect(content).toMatch(/type: Tutorial/);
    expect(content).toMatch(/audience: Beginner/);
    expect(content).toMatch(/score:/);
  });

  it('omits channel line from frontmatter when channelTitle is absent', async () => {
    const meta = makeVideoMeta('vid1');
    mockFetchPlaylistVideos.mockResolvedValue([meta]);
    mockFetchTranscript.mockResolvedValue('transcript');
    mockGenerateSummary.mockResolvedValue(makeSummaryResponse());

    await runIngestion(PLAYLIST_URL, outputFolder, () => {});

    const files = fs.readdirSync(outputFolder).filter((f) => f.endsWith('.md'));
    const content = fs.readFileSync(path.join(outputFolder, files[0]), 'utf-8');
    expect(content).not.toMatch(/^channel:/m);
  });

  it('always includes video-summary structural tag in frontmatter', async () => {
    const meta = makeVideoMeta('vid1');
    mockFetchPlaylistVideos.mockResolvedValue([meta]);
    mockFetchTranscript.mockResolvedValue('transcript');
    mockGenerateSummary.mockResolvedValue(makeSummaryResponse());

    await runIngestion(PLAYLIST_URL, outputFolder, () => {});

    const files = fs.readdirSync(outputFolder).filter((f) => f.endsWith('.md'));
    const content = fs.readFileSync(path.join(outputFolder, files[0]), 'utf-8');
    expect(content).toMatch(/- video-summary/);
  });

  it('stores channel and tags from generateSummary in the index entry', async () => {
    const meta = { ...makeVideoMeta('vid1'), channelTitle: 'MyChannel' };
    mockFetchPlaylistVideos.mockResolvedValue([meta]);
    mockFetchTranscript.mockResolvedValue('transcript');
    mockGenerateSummary.mockResolvedValue(makeSummaryResponse({ tags: ['react', 'hooks'] }));

    await runIngestion(PLAYLIST_URL, outputFolder, () => {});

    expect(mockUpsertVideo).toHaveBeenCalledWith(
      outputFolder,
      expect.objectContaining({ channel: 'MyChannel', tags: ['react', 'hooks'] }),
    );
  });
});

describe('slugify', () => {
  it('lowercases and replaces spaces/punctuation with hyphens', () => {
    expect(slugify('Hello World!')).toBe('hello-world');
  });

  it('handles Unicode letters (Korean)', () => {
    expect(slugify('안녕 World')).toBe('안녕-world');
  });

  it('truncates to 60 characters', () => {
    expect(slugify('A'.repeat(80))).toHaveLength(60);
  });

  it('strips leading/trailing hyphens', () => {
    expect(slugify('  hello  ')).toBe('hello');
  });
});

describe('formatDuration', () => {
  it('formats seconds-only as M:SS', () => {
    expect(formatDuration(45)).toBe('0:45');
  });

  it('formats minutes and seconds as M:SS', () => {
    expect(formatDuration(300)).toBe('5:00');
  });

  it('formats hours as H:MM:SS', () => {
    expect(formatDuration(3661)).toBe('1:01:01');
  });
});
