import { fixSummary, extractQuickView } from '@/lib/gemini';
import { stripQuickViewCallout, insertQuickViewCallout } from '@/lib/quick-view-callout';
import { assertStructurePreserved } from './structural-validation';

/** `tags` and `signal` are REQUIRED. `tags` because omitting it deletes the callout's Concepts
 *  line; `signal` because an optional one lets a caller silently restore an uncancellable ~181 s
 *  paid call, and a required parameter makes that a compile error instead. */
export interface ApplyCorrectionInput {
  md: string;
  corrections: string;
  tags: string[];
  signal: AbortSignal;
}

export interface ApplyCorrectionResult {
  content: string;
  tldr: string;
  takeaways: string[];
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
  const fixed = await fixSummary(stripped, input.corrections);
  // Validate BEFORE paying for quick-view: a structural failure discards the correction, so there is
  // no reason to buy an extraction of a document that is about to be thrown away.
  assertStructurePreserved(stripped, fixed);
  const { tldr, takeaways } = await extractQuickView(fixed);
  return {
    content: insertQuickViewCallout(fixed, tldr, takeaways, input.tags),
    tldr,
    takeaways,
  };
}
