/**
 * Clipped Gemini REST call for "dig deeper" section elaboration.
 *
 * Uses direct fetch (not the @google/generative-ai SDK) because the SDK
 * lacks `video_metadata` types needed for temporal clipping.
 */

import { buildIndexedTranscript } from '@/lib/transcript-timestamps';
import type { SectionWindow } from '@/lib/dig/section-window';

/** Dig generation policy version. Bump when the slide/code policy changes so existing
 *  dug sections become stale and can be deliberately refreshed. */
export const DIG_GENERATOR_VERSION = 9;

// Exported so the LOCAL dig-section path (lib/dig/dig-section.ts) and tests can reference the
// default/env-overridable model. The cloud dig-handler does NOT read this export for pricing
// purposes — it pins the billed model explicitly via `opts.model: PRICED_DIG_MODEL`
// (lib/gemini-cost.ts), so an env override here can never drift the cloud spend bound; only the
// local, unpriced path is affected by GEMINI_DEEPDIVE_MODEL.
export const DEEPDIVE_MODEL =
  process.env.GEMINI_DEEPDIVE_MODEL ?? 'gemini-2.5-pro';

const GEMINI_REST_BASE =
  'https://generativelanguage.googleapis.com/v1beta/models';

/** Transient HTTP status codes that warrant one retry. */
const TRANSIENT_STATUSES = new Set([429, 500, 502, 503, 504]);

/**
 * Per-attempt fetch timeout. Mirrors REQUEST_TIMEOUT_MS in lib/gemini.ts (60 s).
 * An AbortError from this timeout is treated as a transient failure and retried once.
 */
const REQUEST_TIMEOUT_MS = 60_000;

function getApiKey(): string {
  const key = process.env.GEMINI_API_KEY;
  if (!key) throw new Error('GEMINI_API_KEY is not set');
  return key;
}

// ── Prompt ────────────────────────────────────────────────────────────────────

/**
 * Build the text prompt for a dig-deeper request.
 *
 * The prompt:
 * - names the clip range [startSec, endSec]
 * - includes [[SLIDE:M:SS|M:SS|caption]] visual-capture instructions
 * - curates to at most 4 slides
 * - instructs Korean output when lang='ko'
 *
 * Note: inline [[TS:i]] transcript citations were removed (DIG_GENERATOR_VERSION 8). Gemini
 * echoed the indexed-transcript display format as `[[i @m:ss]]`, which leaked as literal text,
 * and resolveTranscriptTokens only ever rendered OWN-LINE citations (it strips inline ones).
 * Each dug section already carries the summary's own-line ▶ timestamp link directly above it.
 * Note: v9 adds length-conditional ### sub-headings to long sections (re-dig to apply).
 */
export function buildDigPrompt(
  lang: 'en' | 'ko',
  startSec: number,
  endSec: number,
): string {
  const langInstruction =
    lang === 'ko'
      ? 'Write your entire response in Korean (한국어로 작성하세요).'
      : 'Write your entire response in English.';

  return `You are elaborating on one section of a YouTube video for a reader who has already seen a brief summary.

This clip covers seconds ${startSec} to ${endSec} of the video.

${langInstruction}

Your task:
- Elaborate this ONE section in depth, grounded in the transcript and video content provided.
- Cover at least everything the summary section states, then go deeper with specifics, examples, and reasoning from the clip.
- Emit [[SLIDE:M:SS|M:SS|caption]] when an on-screen visual carries meaning words alone cannot fully convey — a diagram, chart, architecture/flow figure, data visualization, a UI/result screenshot whose spatial layout matters, OR a slide showing code, a command, terminal/CLI output, or config whose on-screen text is the point. Emit ONLY when that content is actually shown on screen — do NOT transcribe code into a fenced block, and do NOT invent a slide for code that is merely spoken. NEVER for title cards, bullet lists, quotes, tips, or a speaker on camera (including a split-screen with a speaker) unless the slide content itself is the point. The FIRST M:SS is the moment the visual is FULLY BUILT and settled; the SECOND M:SS is when it is replaced or leaves the screen.
- Usually emit ONE token per visual, at its settled moment. EXCEPTION: if a visual builds in stages and the intermediate stages each teach something the final frame cannot (e.g. a diagram that reveals a relationship piece by piece), emit one token per instructive stage, each pointed at the moment that stage is complete. If the build merely animates into place, the final settled frame alone is enough.
- The caption is a short plain-English description of the slide. It MUST NOT contain the characters [ ] ( ) or | — describe the slide in words; never paste raw code, YAML, or shell into the caption. (example: [[SLIDE:3:51|4:02|Diagram showing four capabilities]])
- Select at most 4 — typically 1-3 — only the most essential visuals. In a slide-heavy talk, do NOT reproduce every slide; curate the handful a reader most needs, and omit any visual whose point the prose already carries. Most sections need zero or one; emitting none is fine.
- For a LONG elaboration, structure the prose with short \`###\` sub-headings (e.g. "How it works", "Where it breaks down", "What to use instead") that group it into labeled subsections. Use \`###\` ONLY — never \`#\` or \`##\` (the section title is rendered separately). Keep each sub-heading short, plain, and descriptive, in the SAME language as the rest of your response (do NOT switch to English), with no markdown, code, or the characters [ ] ( ) |. Add sub-headings ONLY when the section is long enough to benefit — a short one-or-two-paragraph section needs none. Sub-headings group THIS section's elaboration; they do not restate the section title or the summary's bullet points.
- Output markdown only — no preamble, no headings for the section title, no meta-commentary.

Transcript and summary follow:
`;
}

// ── REST call ─────────────────────────────────────────────────────────────────

interface GeminiCandidate {
  content: { parts: Array<{ text?: string }> };
}

interface GeminiRestResponse {
  candidates?: GeminiCandidate[];
}

/**
 * Optional cost-governing knobs, additive to the base 3-arg `generateDig` signature. ALL fields
 * are optional and, when `opts` is absent/empty, change nothing about the request body or
 * behavior — the LOCAL dig-section path (`lib/dig/dig-section.ts:61`) calls `generateDig` with no
 * 4th argument and MUST stay byte-identical. Only the cloud `dig` job handler passes these, to
 * make the per-job Gemini spend mechanically bounded (docs/superpowers/specs/2026-07-12-dig-cost-
 * bound-hardening.md).
 */
export interface GenerateDigOpts {
  maxOutputTokens?: number;
  maxVideoSeconds?: number;
  mediaResolution?: 'LOW';
  /** Thinking-token budget, sourced from MAX_DIG_THINKING_TOKENS (lib/gemini-cost.ts) by the
   *  caller so digWorstCents()'s accounting can never drift from the actual request. The cloud
   *  path passes gemini-2.5-flash + `0`, which genuinely HARD-DISABLES thinking (Flash-family
   *  supports thinkingBudget: 0). Local dig (no opts) stays on gemini-2.5-pro, which cannot
   *  disable thinking (min budget 128) — this field is simply never set on that path. */
  thinkingBudget?: number;
  /** Model to call, e.g. `PRICED_DIG_MODEL` (lib/gemini-cost.ts) from the cloud handler, pinning
   *  the billed/priced model independent of the DEEPDIVE_MODEL env override. Absent → DEEPDIVE_MODEL
   *  (local dig-section path), unchanged. */
  model?: string;
  signal?: AbortSignal;
}

function buildRequestBody(
  window: SectionWindow,
  videoId: string,
  lang: 'en' | 'ko',
  opts?: GenerateDigOpts,
): object {
  const { startSec, endSec, transcriptWindow, summaryProse } = window;
  const transcriptBlock = buildIndexedTranscript(transcriptWindow);
  const promptText =
    buildDigPrompt(lang, startSec, endSec) +
    (transcriptBlock ? `\n${transcriptBlock}\n` : '') +
    `\nSummary section:\n${summaryProse}`;

  // Clamp the video segment's end offset to a bounded duration when requested (cloud cost bound —
  // video input is the dominant, duration-scaling cost term). Absent opts.maxVideoSeconds: the
  // original endSec is used unchanged, matching today's local behavior exactly.
  const clampedEndSec =
    opts?.maxVideoSeconds !== undefined
      ? Math.min(endSec, startSec + opts.maxVideoSeconds)
      : endSec;

  // generationConfig is entirely OMITTED when no opts request it — the local path's request body
  // stays byte-identical to today. Unlike the file_data/video_metadata/start_offset/end_offset/
  // mime_type/file_uri parts above (snake_case, proven-working across 9 versions — left untouched),
  // generationConfig itself uses the documented camelCase REST field names (maxOutputTokens,
  // mediaResolution, thinkingConfig) — the SAME form the production summary cloud path sends
  // (lib/gemini.ts:26-40, :633-645, "honored by the API"). thinkingConfig.thinkingBudget DISABLES
  // thinking on the cloud path: the cloud caller passes gemini-2.5-flash + thinkingBudget: 0, and
  // flash genuinely honors 0 as a hard off-switch (unlike gemini-2.5-pro, which cannot disable
  // thinking — min budget 128). The value is set ONLY when the caller supplies opts.thinkingBudget
  // (0 !== undefined, so 0 IS emitted — do not change this to a truthy check) — never hardcoded
  // here — so the local no-opts path stays byte-identical and the budget always traces back to the
  // caller's constant (MAX_DIG_THINKING_TOKENS).
  const generationConfig: Record<string, unknown> = {};
  if (opts?.maxOutputTokens !== undefined) {
    generationConfig.maxOutputTokens = opts.maxOutputTokens;
  }
  if (opts?.mediaResolution === 'LOW') {
    generationConfig.mediaResolution = 'MEDIA_RESOLUTION_LOW';
  }
  if (opts?.thinkingBudget !== undefined) {
    generationConfig.thinkingConfig = { thinkingBudget: opts.thinkingBudget };
  }
  const hasGenerationConfig = Object.keys(generationConfig).length > 0;

  return {
    contents: [
      {
        role: 'user',
        parts: [
          {
            file_data: {
              file_uri: `https://www.youtube.com/watch?v=${videoId}`,
              mime_type: 'video/mp4',
            },
            video_metadata: {
              start_offset: { seconds: startSec },
              end_offset: { seconds: clampedEndSec },
            },
          },
          { text: promptText },
        ],
      },
    ],
    ...(hasGenerationConfig ? { generationConfig } : {}),
  };
}

async function callGeminiRest(
  model: string,
  apiKey: string,
  body: object,
  externalSignal?: AbortSignal,
): Promise<Response> {
  const url = `${GEMINI_REST_BASE}/${model}:generateContent`;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  // Compose the per-request timeout signal with an optional external signal (e.g. the cloud job's
  // lease/shutdown signal) so EITHER aborts the fetch. Absent externalSignal, behavior is unchanged
  // (AbortSignal.any with a single real signal behaves like that signal alone).
  const signal = externalSignal
    ? AbortSignal.any([controller.signal, externalSignal])
    : controller.signal;
  try {
    return await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-goog-api-key': apiKey,
      },
      body: JSON.stringify(body),
      signal,
    });
  } finally {
    clearTimeout(timer);
  }
}

function extractText(data: GeminiRestResponse): string {
  const candidate = data.candidates?.[0];
  const text = candidate?.content?.parts?.[0]?.text;
  if (typeof text !== 'string') {
    throw new Error('generateDig: no text in Gemini response candidates');
  }
  return text;
}

/**
 * Generate a "dig deeper" markdown elaboration for one video section.
 *
 * Retries once on transient HTTP errors (429/5xx). Throws on non-200
 * after retry or on missing candidates.
 *
 * @param window   Section window produced by Task 2's windowForSection.
 * @param videoId  YouTube video ID (11 chars).
 * @param lang     Output language.
 * @param opts     Optional cost-governing caps + external abort signal (cloud path only — see
 *                 GenerateDigOpts). Absent/empty: behavior is unchanged from before this param existed.
 * @returns        Raw markdown string.
 */
export async function generateDig(
  window: SectionWindow,
  videoId: string,
  lang: 'en' | 'ko',
  opts?: GenerateDigOpts,
): Promise<string> {
  const apiKey = getApiKey();
  const model = opts?.model ?? DEEPDIVE_MODEL;
  const body = buildRequestBody(window, videoId, lang, opts);
  const signal = opts?.signal;

  let res: Response;

  try {
    res = await callGeminiRest(model, apiKey, body, signal);
  } catch (err) {
    // Network or timeout error on first attempt — retry once.
    res = await callGeminiRest(model, apiKey, body, signal);
  }

  // One retry on transient HTTP failure.
  if (!res.ok && TRANSIENT_STATUSES.has(res.status)) {
    res = await callGeminiRest(model, apiKey, body, signal);
  }

  if (!res.ok) {
    throw new Error(
      `generateDig: Gemini REST returned HTTP ${res.status}`,
    );
  }

  const data = (await res.json()) as GeminiRestResponse;
  return extractText(data);
}
