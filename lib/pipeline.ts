import fs from 'fs';
import path from 'path';
import { fetchPlaylistVideos, fetchPlaylistTitle } from './youtube';
import { generateSummary, extractQuickView } from './gemini';
import { resolveTranscriptSegments } from './transcript-source';
import { assertVideoId } from './index-store';
import { getPrincipal, getStorageBundle } from '@/lib/storage/resolve';
import { localPrincipal } from '@/lib/storage/principal';
import type { BlobStore } from '@/lib/storage/blob-store';
import { slugify } from './slugify';
import { applySerial, padSerial } from './serial-filename';
import type { ProgressEvent, Video, VideoMeta, RatingValue, VideoType, Audience, GeminiSummaryResponse } from '../types';
import { CURRENT_DOC_VERSION } from './doc-version';
import { runHtmlDoc } from './html-doc/generate';
import { formatDuration } from './format-duration';
import { summaryCore } from './ingestion/summary-core';

const VALID_VIDEO_TYPES: VideoType[] = ['Tutorial', 'Analysis', 'Case Study', 'Framework', 'Demo', 'Interview'];
const VALID_AUDIENCES: Audience[] = ['Beginner', 'Intermediate', 'Advanced'];

export interface SummaryDocInput {
  videoId: string;
  title: string;
  youtubeUrl: string;
  channel?: string;
  durationSeconds: number;
  outputFolder: string;
  baseName: string;
  blobStore?: BlobStore;
}
export interface SummaryDocResult {
  language: 'en' | 'ko';
  ratings: GeminiSummaryResponse['ratings'];
  overallScore: number;
  videoType?: VideoType;
  audience?: Audience;
  tags?: string[];
  tldr?: string;
  takeaways?: string[];
  mdContent: string;
  summaryMd: string;
}

/**
 * Fetch transcript → generateSummary (emits ▶ timestamps) → build the summary .md → write it at
 * <baseName>.md. Shared by ingestion (new slug) and re-summarize (existing baseName).
 */
export async function writeSummaryDoc(input: SummaryDocInput): Promise<SummaryDocResult> {
  const { videoId, title, youtubeUrl, channel, durationSeconds, outputFolder, baseName, blobStore = getStorageBundle().blobStore } = input;
  const result = await summaryCore(
    { videoId, title, youtubeUrl, channel, durationSeconds, baseName },
    { resolveTranscriptSegments, generateSummary, extractQuickView },
  );
  const { language, ratings, overallScore, videoType, audience, tags, tldr, takeaways } = result.geminiFields;

  await blobStore.put(localPrincipal(outputFolder), `${baseName}.md`, Buffer.from(result.mdContent, 'utf-8'), 'text/markdown');
  return { language, ratings, overallScore, videoType, audience, tags, tldr, takeaways, mdContent: result.mdContent, summaryMd: `${baseName}.md` };
}

export function parseFrontmatterField(content: string, key: string): string | null {
  const match = content.match(new RegExp(`^${key}:\\s*"?([^"\\n]*)"?\\s*$`, 'm'));
  return match?.[1]?.trim() ?? null;
}

function parseDurationString(dur: string): number {
  const parts = dur.split(':').map(Number);
  if (parts.length === 2) return (parts[0] ?? 0) * 60 + (parts[1] ?? 0);
  if (parts.length === 3) return (parts[0] ?? 0) * 3600 + (parts[1] ?? 0) * 60 + (parts[2] ?? 0);
  return 0;
}

export function reconstructVideo(content: string, file: string, mdPath: string): Video | null {
  const videoId = parseFrontmatterField(content, 'video_id');
  if (!videoId) return null;

  const langRaw = parseFrontmatterField(content, 'lang');
  const language = langRaw?.toLowerCase() === 'ko' ? 'ko' : 'en';

  const scoreRaw = parseFrontmatterField(content, 'score');
  const overallScore = parseFloat(scoreRaw ?? '3') || 3;
  const rRaw = Math.max(1, Math.min(5, Math.round(overallScore)));
  const r = rRaw as RatingValue;
  const ratings = { usefulness: r, depth: r, originality: r, recency: r, completeness: r };

  const urlMatch = content.match(/\*\*URL:\*\*\s*(https?:\/\/\S+)/);
  const youtubeUrl = urlMatch?.[1] ?? `https://www.youtube.com/watch?v=${videoId}`;

  const durMatch = content.match(/\*\*Duration:\*\*\s*([\d:]+)/);
  const durationSeconds = durMatch ? parseDurationString(durMatch[1]) : 0;

  const titleMatch = content.match(/^#\s+(.+)$/m);
  const title = titleMatch?.[1]?.trim() ?? file.replace(/\.md$/, '');

  const videoTypeRaw = parseFrontmatterField(content, 'type');
  const audienceRaw = parseFrontmatterField(content, 'audience');
  const channelRaw = parseFrontmatterField(content, 'channel');

  const videoType = VALID_VIDEO_TYPES.includes(videoTypeRaw as VideoType)
    ? (videoTypeRaw as VideoType) : undefined;
  const audience = VALID_AUDIENCES.includes(audienceRaw as Audience)
    ? (audienceRaw as Audience) : undefined;

  const summaryMd = file;

  const serialMatch = file.match(/^(\d+)_/);
  const serialNumber = serialMatch ? parseInt(serialMatch[1], 10) : undefined;

  const processedAt = fs.statSync(mdPath).mtime.toISOString();

  return {
    id: videoId,
    title,
    youtubeUrl,
    language,
    durationSeconds,
    archived: false,
    ratings,
    overallScore,
    summaryMd,
    processedAt,
    ...(videoType !== undefined && { videoType }),
    ...(audience !== undefined && { audience }),
    ...(channelRaw ? { channel: channelRaw } : {}),
    ...(serialNumber !== undefined && { serialNumber }),
  };
}

export async function recoverOrphanedVideos(outputFolder: string): Promise<void> {
  const principal = getPrincipal(outputFolder);
  const { metadataStore: store } = getStorageBundle();
  const index = await store.readIndex(principal);
  const indexedIds = new Set(index.videos.map((v) => v.id));

  let files: string[];
  try {
    files = fs.readdirSync(outputFolder).filter(
      (f) => f.endsWith('.md') && !f.includes('-deep-dive'),
    );
  } catch {
    return;
  }

  for (const file of files) {
    const mdPath = path.join(outputFolder, file);
    try {
      const content = fs.readFileSync(mdPath, 'utf-8');
      const videoId = parseFrontmatterField(content, 'video_id');
      if (!videoId || indexedIds.has(videoId)) continue;

      const video = reconstructVideo(content, file, mdPath);
      if (video) {
        await store.upsertVideo(principal, video);
        indexedIds.add(videoId);
      }
    } catch {
      // Skip files that can't be parsed or indexed
    }
  }
}

export { slugify };

// formatDuration lives in its own pure module so client components can import it
// without pulling pipeline's server-only deps; re-exported here for existing importers.
export { formatDuration };


/**
 * Remove an existing Quick Reference callout block from markdown content.
 * Reverses `insertQuickViewCallout` so the callout can be re-generated
 * after corrections are applied. Returns content unchanged if no callout
 * is present or the format is unexpected.
 */
export function stripQuickViewCallout(mdContent: string): string {
  const START_MARKER = '\n\n> [!summary] Quick Reference';
  const END_MARKER = '\n\n---\n';
  const startIdx = mdContent.indexOf(START_MARKER);
  if (startIdx === -1) return mdContent; // no callout present
  const endIdx = mdContent.indexOf(END_MARKER, startIdx);
  if (endIdx === -1) return mdContent; // malformed — leave unchanged
  return mdContent.slice(0, startIdx) + mdContent.slice(endIdx);
}

export function insertQuickViewCallout(
  mdContent: string,
  tldr: string,
  takeaways: string[],
  tags: string[],
): string {
  // Idempotency guard: don't insert if callout already present
  if (mdContent.includes('> [!summary] Quick Reference')) return mdContent;

  // Find first "\n\n---\n" — the divider between metadata line and summary body
  const dividerIdx = mdContent.indexOf('\n\n---\n');
  if (dividerIdx === -1) return mdContent; // unexpected format, leave unchanged

  const lines = [
    '',
    '> [!summary] Quick Reference',
    `> **TL;DR:** ${tldr}`,
    '>',
    '> **Key Takeaways:**',
    ...takeaways.map((t) => `> - ${t}`),
  ];
  if (tags.length > 0) {
    lines.push('>');
    lines.push(`> **Concepts:** ${tags.join(' · ')}`);
  }

  return mdContent.slice(0, dividerIdx) + '\n' + lines.join('\n') + mdContent.slice(dividerIdx);
}

export async function runIngestion(
  playlistUrl: string,
  outputFolder: string,
  onProgress: (event: ProgressEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  // Check cheap env guard before I/O-bound assertOutputFolder
  const apiKey = process.env.YOUTUBE_API_KEY;
  if (!apiKey) throw new Error('YOUTUBE_API_KEY is not set');

  const principal = getPrincipal(outputFolder);
  const { metadataStore: store } = getStorageBundle();
  fs.mkdirSync(outputFolder, { recursive: true });

  const metas = await fetchPlaylistVideos(playlistUrl, apiKey);

  // Stamp playlistUrl + human title into the index before processing. Title fetch
  // degrades to OMITTED on failure (network/auth/quota) — never persists a bare id.
  const playlistId = (() => { try { return new URL(playlistUrl).searchParams.get('list'); } catch { return null; } })();
  let playlistTitle: string | undefined;
  if (playlistId) {
    try { playlistTitle = await fetchPlaylistTitle(playlistId, apiKey); } catch { playlistTitle = undefined; }
  }
  await store.setPlaylistMeta(principal, { playlistUrl, playlistTitle });

  // Recover any .md files written in a prior interrupted run before processing new videos.
  await recoverOrphanedVideos(outputFolder);

  // Build the set of already-indexed IDs so we can skip re-processing them.
  const alreadyIndexed = new Set((await store.readIndex(principal)).videos.map((v) => v.id));

  // Progress is over NEW (not-yet-indexed) distinct videos only — skips are instant and
  // must not inflate the bar. playlistPos (below) stays the true playlist position.
  const newTotal = new Set(metas.filter((m) => !alreadyIndexed.has(m.videoId)).map((m) => m.videoId)).size;
  let newIndex = 0;

  onProgress({ type: 'start', total: newTotal });

  for (let i = 0; i < metas.length; i++) {
    // Check cancellation between videos — after any current video finishes cleanly.
    if (signal?.aborted) {
      onProgress({ type: 'cancelled' });
      return;
    }
    const meta = metas[i];
    const playlistPos = i + 1;
    // Tracks whether claimVideoSlot reserved a stub for this video in this run.
    // Set to false again once upsertVideo commits the full record — after that point
    // the video is fully indexed and must NOT be deleted on failure.
    let slotReservedThisRun = false;
    try {
      assertVideoId(meta.videoId); // defense-in-depth before any path construction

      if (alreadyIndexed.has(meta.videoId)) {
        continue;
      }

      newIndex += 1;

      onProgress({ type: 'step', videoId: meta.videoId, title: meta.title, step: 'Fetching transcript…', current: newIndex, total: newTotal });
      const { serialNumber } = await store.claimVideoSlot(principal, meta.videoId);
      slotReservedThisRun = true;
      const slug = slugify(meta.title);
      let baseSlug = slug;
      let counter = 2;
      // serialNumber makes filenames unique; collision suffix kept for slug readability only.
      while (fs.existsSync(path.join(outputFolder, applySerial(`${baseSlug}.md`, serialNumber)))) {
        baseSlug = `${slug}-${counter}`;
        counter++;
      }
      const baseName = `${padSerial(serialNumber)}_${baseSlug}`;
      onProgress({ type: 'step', videoId: meta.videoId, title: meta.title, step: 'Generating summary…', current: newIndex, total: newTotal });
      const { language, ratings, overallScore, videoType, audience, tags, tldr, takeaways } =
        await writeSummaryDoc({
          videoId: meta.videoId, title: meta.title, youtubeUrl: meta.youtubeUrl,
          channel: meta.channelTitle, durationSeconds: meta.durationSeconds, outputFolder, baseName,
        });

      const video: Video = {
        id: meta.videoId,
        title: meta.title,
        youtubeUrl: meta.youtubeUrl,
        language,
        durationSeconds: meta.durationSeconds,
        archived: false,
        ratings,
        overallScore,
        // serialNumber from claimVideoSlot must be threaded through — upsertVideo does a
        // full-replacement write, so omitting it here would silently erase the reserved serial.
        serialNumber,
        summaryMd: `${baseName}.md`,
        processedAt: new Date().toISOString(),
        docVersion: CURRENT_DOC_VERSION,
        playlistIndex: playlistPos,
        ...(videoType !== undefined && { videoType }),
        ...(audience !== undefined && { audience }),
        ...(meta.channelTitle !== undefined && { channel: meta.channelTitle }),
        ...(tags !== undefined && { tags }),
        ...(tldr !== undefined && { tldr }),
        ...(takeaways !== undefined && { takeaways }),
        ...(meta.videoPublishedAt !== undefined && { videoPublishedAt: meta.videoPublishedAt }),
        ...(meta.addedToPlaylistAt !== undefined && { addedToPlaylistAt: meta.addedToPlaylistAt }),
      };
      // Index updated immediately after md write
      await store.upsertVideo(principal, video);
      // Mark as processed so within-run duplicates (same video appearing twice in the playlist) are skipped.
      alreadyIndexed.add(meta.videoId);
      slotReservedThisRun = false; // fully committed — nothing to roll back

      // Pre-generate the summary HTML doc so it opens instantly (no on-demand Gemini wait).
      // Best-effort: the .md is already written and the video already upserted, so a transform
      // failure must never fail the video or abort the batch — it just defers HTML to on-demand.
      // No-op onProgress keeps runHtmlDoc's own events off the ingest stream. Opt out with
      // PREGEN_SUMMARY_HTML=off (mirrors DIG_CROP=off).
      if (process.env.PREGEN_SUMMARY_HTML !== 'off') {
        onProgress({ type: 'step', videoId: meta.videoId, title: meta.title, step: 'Generating HTML doc…', current: newIndex, total: newTotal });
        try {
          await runHtmlDoc(meta.videoId, outputFolder, () => {});
        } catch (err) {
          // Best-effort: defer to on-demand. Log with videoId so the deferred SSE step is
          // correlatable to a cause (the underlying Gemini failure also logs upstream).
          console.warn(`[pregen-html] deferred for ${meta.videoId}: ${err instanceof Error ? err.message : String(err)}`);
          onProgress({ type: 'step', videoId: meta.videoId, title: meta.title, step: 'HTML doc deferred (will generate on open)', current: newIndex, total: newTotal });
        }
      }

      onProgress({ type: 'step', videoId: meta.videoId, title: meta.title, step: 'Saved', current: newIndex, total: newTotal });
    } catch (err) {
      // Roll back the reserved stub so the video is retried on the next sync.
      // Best-effort: a delete failure must not shadow the original error.
      if (slotReservedThisRun) {
        try { await store.deleteVideo(principal, meta.videoId); } catch { /* ignore */ }
      }
      const log = err instanceof Error ? err.message : String(err);
      onProgress({ type: 'error', videoId: meta.videoId, title: meta.title, log });
    }
  }

  // Reconcile removedFromPlaylist: auto-archive on removal, clear flag if video returns.
  await store.reconcilePlaylistMembership(principal, metas.map((m) => m.videoId));

  // Stamp playlistIndex for all videos (new videos already stamped above; this covers
  // already-indexed videos that were skipped during the main loop).
  const positionMap = new Map(metas.map((m, idx) => [m.videoId, idx + 1]));
  const publishedMap = new Map(metas.map((m) => [m.videoId, m.videoPublishedAt]));
  const addedMap = new Map(metas.map((m) => [m.videoId, m.addedToPlaylistAt]));
  const afterReconcile = await store.readIndex(principal);
  // playlistIndex tracks the CURRENT playlist position: in-playlist videos (always in
  // positionMap) are re-derived each sync; videos removed from the playlist (absent from
  // positionMap) keep their last-known index. videoPublishedAt/addedToPlaylistAt remain
  // write-once (stable per video).
  const patches = afterReconcile.videos.map((v) => ({
    videoId: v.id,
    fields: {
      playlistIndex: positionMap.get(v.id) ?? v.playlistIndex,
      videoPublishedAt: v.videoPublishedAt ?? publishedMap.get(v.id),
      addedToPlaylistAt: v.addedToPlaylistAt ?? addedMap.get(v.id),
    },
  }));
  await store.bulkUpdateVideoFields(principal, patches);

  onProgress({ type: 'done', total: newTotal });
}
