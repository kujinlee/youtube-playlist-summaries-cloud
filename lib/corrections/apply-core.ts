import { GoogleGenerativeAI } from '@google/generative-ai';
import { fixSummary, extractQuickView, assertCorrectionInputWithinCap, SUMMARY_MODEL } from '@/lib/gemini';
import {
  MAX_TRANSCRIBE_INPUT_TOKENS, MAX_TRANSCRIBE_OUTPUT_TOKENS, MAX_TRANSCRIPT_INPUT_BYTES,
  MAX_SUMMARY_OUTPUT_TOKENS, correctionActualCents,
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
}

export interface ApplyCorrectionResult {
  content: string;
  tldr: string;
  takeaways: string[];
  /** null means "the SDK reported no usage", NOT "free". */
  actualCents: number | null;
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

  const { text: fixed, usage } = await fixSummary(
    stripped, input.corrections, { signal: input.signal, caps: input.caps },
  );
  // Validate BEFORE paying for quick-view: a structural failure discards the correction, so there is
  // no reason to buy an extraction of a document that is about to be thrown away.
  assertStructurePreserved(stripped, fixed);
  const { tldr, takeaways } = await extractQuickView(fixed, input.caps);
  return {
    content: insertQuickViewCallout(fixed, tldr, takeaways, input.tags),
    tldr,
    takeaways,
    // Counts fixSummary only. extractQuickView's usage is NOT included — the SDK reports it on a
    // different call and nothing in this repo reads it yet; adding it is a separate measurement, not
    // an assumption to bury here.
    actualCents: usage ? correctionActualCents(usage) : null,
  };
}
