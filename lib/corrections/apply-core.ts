import { GoogleGenerativeAI } from '@google/generative-ai';
import { fixSummary, extractQuickView, assertCorrectionInputWithinCap, SUMMARY_MODEL } from '@/lib/gemini';
import type { UsageMeter } from '@/lib/gemini';
import {
  MAX_TRANSCRIBE_INPUT_TOKENS, MAX_TRANSCRIBE_OUTPUT_TOKENS, MAX_TRANSCRIPT_INPUT_BYTES,
  MAX_SUMMARY_OUTPUT_TOKENS, PROMPT_SCHEMA_OVERHEAD_TOKENS, correctionActualCents,
} from '@/lib/gemini-cost';
import type { CloudGeminiCaps } from '@/lib/gemini-cost';
import { stripQuickViewCallout, insertQuickViewCallout } from '@/lib/quick-view-callout';
import { assertStructurePreserved } from './structural-validation';

/** Caps for the paid correction transform. Only `summaryOutputTokens` is load-bearing; the rest
 *  satisfy the CloudGeminiCaps type. Shaped like SERVE_CAPS (serve-doc.ts:26-33) on purpose — this
 *  OBJECT is what makes withCaps cap anything (gemini.ts:41). */
export const CORRECTION_CAPS: CloudGeminiCaps = {
  transcribeInputTokens: MAX_TRANSCRIBE_INPUT_TOKENS,
  transcribeOutputTokens: MAX_TRANSCRIBE_OUTPUT_TOKENS,
  transcriptInputBytes: MAX_TRANSCRIPT_INPUT_BYTES,
  summaryOutputTokens: MAX_SUMMARY_OUTPUT_TOKENS,
};

/** Server-side bound on the corrections field, matching the client's maxLength
 *  (CorrectionsPanel.tsx:105) and enforced where it BINDS. Counted in Unicode CODE POINTS
 *  (`[...s].length`), not UTF-16 units: the browser counts UTF-16, so this is marginally more
 *  permissive and a correction the browser accepted is never refused by the server. */
export const MAX_CORRECTIONS_CHARS = 1000;

/** STATED, never inherited. Inheriting REQUEST_TIMEOUT_MS (60 s, gemini.ts:105) would push §5.4's
 *  worst case to 422.4 s — over the 420 s maxDuration. This is a token count, not a generation. */
export const CORRECTION_PREFLIGHT_TIMEOUT_MS = 10_000;

/** `tags` and `signal` are REQUIRED. `tags` because omitting it deletes the callout's Concepts
 *  line; `signal` because an optional one lets a caller silently restore an uncancellable ~181 s
 *  paid call, and a required parameter makes that a compile error instead. */
export interface ApplyCorrectionInput {
  md: string;
  corrections: string;
  tags: string[];
  signal: AbortSignal;
  /** Absent on the LOCAL branch by design — withCaps then returns the base config unchanged. */
  caps?: CloudGeminiCaps;
  /** REQUIRED and CALLER-OWNED (backlog #62). It is filled as each paid attempt returns, so the
   *  caller can record spend after this function THROWS — the structural validator, a failed
   *  quick-view, an exhausted retry. A spend figure on the result would exist only on success. */
  meter: UsageMeter;
}

export interface ApplyCorrectionResult {
  content: string;
  tldr: string;
  takeaways: string[];
}

/** The most one fixSummary attempt can cost under CORRECTION_CAPS — the figure 0026's header derives
 *  its 12¢ per-call ceiling from (`correctionActualCents({8192+4000, 8192})` = 3¢, × 3 attempts).
 *  Prompt: the preflight refuses a document over `summaryOutputTokens` tokens, and
 *  PROMPT_SCHEMA_OVERHEAD_TOKENS (4,000) covers the instructions plus the ≤1,000-code-point
 *  corrections field. Output: `maxOutputTokens` is set to `summaryOutputTokens`, thinking budget 0. */
const CORRECTION_PROMPT_BOUND_TOKENS = CORRECTION_CAPS.summaryOutputTokens + PROMPT_SCHEMA_OVERHEAD_TOKENS;
const CORRECTION_OUTPUT_BOUND_TOKENS = CORRECTION_CAPS.summaryOutputTokens;
export const CORRECTION_WORST_ATTEMPT_CENTS = correctionActualCents({
  promptTokens: CORRECTION_PROMPT_BOUND_TOKENS, outputTokens: CORRECTION_OUTPUT_BOUND_TOKENS,
});

/**
 * Price a correction from its meter. Each attempt is priced as its own call and the ceilings summed:
 * that is how 0026 derives its 12¢ per-call ceiling (3 attempts × 3¢), and pricing the summed
 * tokens once would round below it.
 *
 * NEVER UNDER-COUNTS (round 1, Codex H2). A field the SDK did not report is charged at the bound
 * CORRECTION_CAPS enforces for that field, and the field it DID report is kept — so an attempt with
 * no metadata costs CORRECTION_WORST_ATTEMPT_CENTS, an over-count by construction, and is never
 * dropped. `estimated` counts the attempts whose figure includes a bound.
 *
 * Counts fixSummary only. extractQuickView's usage is NOT included — the SDK reports it on a
 * different call and nothing in this repo reads it yet; adding it is a separate measurement, not an
 * assumption to bury here.
 */
export function meteredCorrectionCents(meter: UsageMeter): { cents: number; estimated: number } {
  let cents = 0;
  let estimated = 0;
  for (const a of meter.attempts) {
    if (a.promptTokens == null || a.outputTokens == null) estimated++;
    cents += correctionActualCents({
      promptTokens: a.promptTokens ?? CORRECTION_PROMPT_BOUND_TOKENS,
      outputTokens: a.outputTokens ?? CORRECTION_OUTPUT_BOUND_TOKENS,
    });
  }
  return { cents, estimated };
}

/**
 * strip callout → fixSummary → structural validation → extractQuickView → re-insert callout.
 *
 * STORE-AGNOSTIC: no `fs`, no BlobStore, no Supabase. Import the callout transforms from
 * `@/lib/quick-view-callout`, never from `lib/pipeline` — pipeline drags in `fs` and storage.
 *
 * Call this ONLY when the request's corrections are non-empty after trimming. A bare press must not
 * reach it: `fixSummary` runs ⟺ trimmed corrections are non-empty (spec §3).
 */
export async function applyCorrection(input: ApplyCorrectionInput): Promise<ApplyCorrectionResult> {
  const stripped = stripQuickViewCallout(input.md);

  if (input.caps) {
    const client = new GoogleGenerativeAI(process.env.GEMINI_API_KEY ?? '');
    const model = client.getGenerativeModel({ model: SUMMARY_MODEL });
    await assertCorrectionInputWithinCap(
      model, stripped, {}, input.caps,
      { signal: input.signal, timeoutMs: CORRECTION_PREFLIGHT_TIMEOUT_MS },
    );
  }

  const { text: fixed } = await fixSummary(
    stripped, input.corrections, { signal: input.signal, caps: input.caps, meter: input.meter },
  );
  // Validate BEFORE paying for quick-view: a structural failure discards the correction, so there is
  // no reason to buy an extraction of a document that is about to be thrown away.
  assertStructurePreserved(stripped, fixed);
  const { tldr, takeaways } = await extractQuickView(fixed, input.caps);
  return {
    content: insertQuickViewCallout(fixed, tldr, takeaways, input.tags),
    tldr,
    takeaways,
  };
}
