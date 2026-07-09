import { detectLanguage } from '../youtube';
import type { resolveTranscriptSegments as ResolveTranscriptSegmentsFn } from '../transcript-source';
import type { generateSummary as GenerateSummaryFn, extractQuickView as ExtractQuickViewFn } from '../gemini';
import { truncateSegmentsToByteCap } from '../transcript-timestamps';
import type { CloudGeminiCaps } from '../gemini-cost';
import { checkSummaryCompleteness } from '../summary-completeness';
import { padDividers } from '../markdown-dividers';
import { formatDuration } from '../format-duration';
import { insertQuickViewCallout } from '@/lib/quick-view-callout';
import type { GeminiSummaryResponse, VideoType, Audience } from '../../types';

export interface SummaryCoreInput {
  videoId: string;
  title: string;
  youtubeUrl: string;
  channel?: string;
  durationSeconds: number;
  baseName: string;
}

export interface SummaryCoreDeps {
  resolveTranscriptSegments: typeof ResolveTranscriptSegmentsFn;
  generateSummary: typeof GenerateSummaryFn;
  extractQuickView: typeof ExtractQuickViewFn;
}

export interface SummaryCoreGeminiFields {
  language: 'en' | 'ko';
  ratings: GeminiSummaryResponse['ratings'];
  overallScore: number;
  videoType?: VideoType;
  audience?: Audience;
  tags?: string[];
  tldr?: string;
  takeaways?: string[];
}

export interface SummaryCoreResult {
  frontmatter: string;
  markdown: string;
  mdContent: string;
  quickView: { tldr: string; takeaways: string[] } | null;
  geminiFields: SummaryCoreGeminiFields;
}

/**
 * Store-agnostic core of the summary pipeline: fetch transcript → generateSummary (emits ▶
 * timestamps) → build the summary markdown (frontmatter + body + Quick Reference callout). Pure
 * of storage — callers persist `mdContent` however they see fit (local blobStore, Supabase RPC).
 *
 * Extracted from `writeSummaryDoc` (lib/pipeline.ts) so the cloud worker and the local pipeline
 * share one ingestion core. `writeSummaryDoc` still owns the local `blobStore.put`.
 */
export async function summaryCore(
  input: SummaryCoreInput,
  deps: SummaryCoreDeps,
  opts?: { signal?: AbortSignal; caps?: CloudGeminiCaps },
): Promise<SummaryCoreResult> {
  // baseName is accepted in the input shape (callers use it to key the persisted file) but is
  // not needed to build the markdown content itself, so it is intentionally not destructured here.
  const { videoId, title, youtubeUrl, channel, durationSeconds } = input;
  const caps = opts?.caps;
  // signal/caps threaded only when present — an explicit `undefined` opts arg is a DIFFERENT call
  // signature than omitting it (callers/tests assert exact arg lists), so build the opts object
  // conditionally. When both are absent, omit the 4th arg entirely → local pipeline byte-identical.
  const rtsOpts: { signal?: AbortSignal; caps?: CloudGeminiCaps } = {};
  if (opts?.signal) rtsOpts.signal = opts.signal;
  if (caps) rtsOpts.caps = caps;
  const { segments: rawSegments } = (opts?.signal || caps)
    ? await deps.resolveTranscriptSegments(videoId, youtubeUrl, durationSeconds, rtsOpts)
    : await deps.resolveTranscriptSegments(videoId, youtubeUrl, durationSeconds);
  // Cloud byte-cap truncation: drop whole trailing segments until the RENDERED indexed transcript
  // is within caps.transcriptInputBytes. The SAME truncated list feeds language detection, the
  // prompt build AND resolveTranscriptTokens (both inside generateSummary) — the correctness crux:
  // a [[TS:n]] citation can never reference a segment the prompt no longer contained. No caps ⇒ no
  // truncation (identity), so the local pipeline is behaviorally unchanged.
  const segments = caps ? truncateSegmentsToByteCap(rawSegments, caps.transcriptInputBytes) : rawSegments;
  const transcript = segments.map((s) => s.text).join(' '); // plain text for language detection only
  const language = detectLanguage(transcript);
  const gsOpts: { signal?: AbortSignal; caps?: CloudGeminiCaps } = {};
  if (opts?.signal) gsOpts.signal = opts.signal;
  if (caps) gsOpts.caps = caps;
  const { summary: rawSummary, ratings, overallScore, videoType, audience, tags, tldr, takeaways } = (opts?.signal || caps)
    ? await deps.generateSummary(segments, language, videoId, gsOpts)
    : await deps.generateSummary(segments, language, videoId);
  const summary = padDividers(rawSummary);
  // Non-blocking observability: flag a summary that looks truncated (see summary-completeness).
  // Never blocks the write. Layered on purpose: generateSummary (Stage 2) also warns after its
  // retry budget is exhausted; this pipeline check is the final gate on the exact text being
  // persisted (incl. padDividers). Two warnings for one truncation is expected, not a bug.
  const completeness = checkSummaryCompleteness(summary);
  if (!completeness.complete) {
    console.warn(`[summary-suspicious] ${videoId}: ${completeness.reason} (confidence=${completeness.confidence})`);
  }

  const structuralTags = ['video-summary', language];
  const allTags = [...structuralTags, ...(tags ?? [])];
  const frontmatterLines = [
    '---', 'tags:', ...allTags.map((t) => `  - ${t}`),
    `video_id: "${videoId}"`,
    ...(channel ? [`channel: "${channel}"`] : []),
    `lang: ${language.toUpperCase()}`,
    ...(videoType ? [`type: ${videoType}`] : []),
    ...(audience ? [`audience: ${audience}`] : []),
    `score: ${overallScore}`, '---',
  ];
  const frontmatter = frontmatterLines.join('\n');
  const metaParts = [
    channel && `**Channel:** ${channel}`,
    `**Duration:** ${formatDuration(durationSeconds)}`,
    `**URL:** ${youtubeUrl}`,
  ].filter(Boolean).join(' | ');
  const baseContent = [frontmatter, '', `# ${title}`, '', metaParts, '', '---', '', summary].join('\n');
  let outTldr = tldr;
  let outTakeaways = takeaways;
  let mdContent: string;
  if (tldr && takeaways) {
    mdContent = insertQuickViewCallout(baseContent, tldr, takeaways, tags ?? []);
  } else {
    // generateSummary omitted tldr/takeaways → derive them from the full md so the Quick
    // Reference callout is never silently skipped (same primitive the backfill route uses).
    try {
      const qv = caps ? await deps.extractQuickView(baseContent, caps) : await deps.extractQuickView(baseContent);
      outTldr = qv.tldr;
      outTakeaways = qv.takeaways;
      mdContent = insertQuickViewCallout(baseContent, qv.tldr, qv.takeaways, tags ?? []);
    } catch {
      // Extraction failed — write without the callout and clear the partial so the doc
      // stays eligible for the backfill route (filters on !v.tldr). Never fail the summary.
      mdContent = baseContent;
      outTldr = undefined;
      outTakeaways = undefined;
    }
  }

  const quickView = outTldr && outTakeaways ? { tldr: outTldr, takeaways: outTakeaways } : null;

  return {
    frontmatter,
    markdown: baseContent,
    mdContent,
    quickView,
    geminiFields: { language, ratings, overallScore, videoType, audience, tags, tldr: outTldr, takeaways: outTakeaways },
  };
}
