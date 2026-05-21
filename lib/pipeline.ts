import fs from 'fs';
import path from 'path';
import { fetchPlaylistVideos, fetchTranscript, detectLanguage } from './youtube';
import { generateSummary } from './gemini';
import { generatePdf } from './pdf';
import { assertOutputFolder, assertVideoId, upsertVideo, readIndex, writeIndex } from './index-store';
import type { ProgressEvent, Video } from '../types';

export function slugify(title: string): string {
  return title
    .toLowerCase()
    .replace(/[^\p{L}\p{N}]+/gu, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 60);
}

export function formatDuration(secs: number): string {
  const h = Math.floor(secs / 3600);
  const m = Math.floor((secs % 3600) / 60);
  const s = secs % 60;
  return h > 0
    ? `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
    : `${m}:${String(s).padStart(2, '0')}`;
}

export async function runIngestion(
  playlistUrl: string,
  outputFolder: string,
  onProgress: (event: ProgressEvent) => void,
): Promise<void> {
  // Check cheap env guard before I/O-bound assertOutputFolder
  const apiKey = process.env.YOUTUBE_API_KEY;
  if (!apiKey) throw new Error('YOUTUBE_API_KEY is not set');

  assertOutputFolder(outputFolder);

  const metas = await fetchPlaylistVideos(playlistUrl, apiKey);
  const total = metas.length;

  // Stamp playlistUrl into the index before processing — upsertVideo reads-then-writes
  // and would silently carry forward the empty string it gets from a new index.
  const existing = readIndex(outputFolder);
  writeIndex(outputFolder, { ...existing, playlistUrl, outputFolder });

  onProgress({ type: 'start', total });

  for (let i = 0; i < metas.length; i++) {
    const meta = metas[i];
    const current = i + 1;
    try {
      assertVideoId(meta.videoId); // defense-in-depth before any path construction

      onProgress({ type: 'step', videoId: meta.videoId, title: meta.title, step: 'Fetching transcript…', current, total });
      const transcript = await fetchTranscript(meta.videoId);

      const language = detectLanguage(transcript);

      onProgress({ type: 'step', videoId: meta.videoId, title: meta.title, step: 'Generating summary…', current, total });
      const { summary, ratings, overallScore, videoType, audience, tags } = await generateSummary(transcript, language);

      const rank = String(i + 1).padStart(3, '0');
      const slug = slugify(meta.title);
      const baseName = `${rank}_${slug}`;
      const mdPath = path.join(outputFolder, `${baseName}.md`);
      const pdfPath = path.join(outputFolder, `${baseName}.pdf`);

      const structuralTags = ['video-summary', language];
      const allTags = [...structuralTags, ...(tags ?? [])];

      const frontmatterLines = [
        '---',
        'tags:',
        ...allTags.map((t) => `  - ${t}`),
        `video_id: "${meta.videoId}"`,
        ...(meta.channelTitle ? [`channel: "${meta.channelTitle}"`] : []),
        `lang: ${language.toUpperCase()}`,
        ...(videoType ? [`type: ${videoType}`] : []),
        ...(audience ? [`audience: ${audience}`] : []),
        `score: ${overallScore}`,
        '---',
      ];

      const metaParts = [
        meta.channelTitle && `**Channel:** ${meta.channelTitle}`,
        `**Duration:** ${formatDuration(meta.durationSeconds)}`,
        `**URL:** ${meta.youtubeUrl}`,
      ].filter(Boolean).join(' | ');

      const mdContent = [
        frontmatterLines.join('\n'),
        '',
        `# ${meta.title}`,
        '',
        metaParts,
        '',
        '---',
        '',
        summary,
      ].join('\n');

      await fs.promises.writeFile(mdPath, mdContent, 'utf-8');

      onProgress({ type: 'step', videoId: meta.videoId, title: meta.title, step: 'Generating PDF…', current, total });
      await generatePdf(mdContent, pdfPath);

      const video: Video = {
        id: meta.videoId,
        title: meta.title,
        youtubeUrl: meta.youtubeUrl,
        language,
        durationSeconds: meta.durationSeconds,
        archived: false,
        ratings,
        overallScore,
        summaryMd: `${baseName}.md`,
        summaryPdf: `${baseName}.pdf`,
        deepDiveMd: null,
        deepDivePdf: null,
        processedAt: new Date().toISOString(),
        ...(videoType !== undefined && { videoType }),
        ...(audience !== undefined && { audience }),
        ...(meta.channelTitle !== undefined && { channel: meta.channelTitle }),
        ...(tags !== undefined && { tags }),
      };
      upsertVideo(outputFolder, video);

      onProgress({ type: 'step', videoId: meta.videoId, title: meta.title, step: 'Saved', current, total });
    } catch (err) {
      const log = err instanceof Error ? err.message : String(err);
      onProgress({ type: 'error', videoId: meta.videoId, title: meta.title, log });
    }
  }

  onProgress({ type: 'done', total });
}
