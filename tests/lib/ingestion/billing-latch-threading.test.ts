// The billing latch's set-point (Task 7) is proven at the `generateJson` primitive by
// tests/lib/gemini-billing-latch.test.ts. That proves ONLY the set-point — it says nothing
// about whether the latch reference actually survives being threaded through summaryCore's
// field-by-field `rtsOpts`/`gsOpts` construction on its way to the real Gemini calls. This
// suite drives the REAL `summaryCore` (lib/ingestion/summary-core.ts) with a deps double that
// stands in for the primitive set-point, and asserts the CALLER's latch object flips — the
// M6-1 under-count guard: if an implementer drops `gsOpts.billing = opts.billing` (or the
// `rtsOpts` equivalent), only this test fails.
import { summaryCore, type SummaryCoreDeps, type SummaryCoreInput } from '@/lib/ingestion/summary-core';
import type { BillingLatch } from '@/lib/job-queue/billing-latch';
import type { CloudGeminiCaps } from '@/lib/gemini-cost';

const SOME_CAPS: CloudGeminiCaps = {
  transcribeInputTokens: 300000,
  transcribeOutputTokens: 32768,
  transcriptInputBytes: 40960,
  summaryOutputTokens: 8192,
};

const input: SummaryCoreInput = {
  videoId: 'v',
  title: 't',
  youtubeUrl: 'https://x',
  channel: 'c',
  durationSeconds: 60,
  baseName: 'v',
};

it('a metered-then-503 summary KEEPS: billing latch flips through summaryCore threading (gsOpts)', async () => {
  const billing: BillingLatch = { metered: false };
  const deps: SummaryCoreDeps = {
    resolveTranscriptSegments: (async () => ({ segments: [{ offset: 0, duration: 1, text: 'x' }], source: 'captions' })) as SummaryCoreDeps['resolveTranscriptSegments'],
    generateSummary: (async (_s: unknown, _l: unknown, _v: unknown, opts?: { billing?: BillingLatch }) => {
      if (opts?.billing) opts.billing.metered = true;                 // stands in for the primitive set-point
      throw Object.assign(new Error('overloaded'), { name: 'GoogleGenerativeAIFetchError', status: 503 });
    }) as SummaryCoreDeps['generateSummary'],
    extractQuickView: (async () => ({ tldr: '', takeaways: [] })) as SummaryCoreDeps['extractQuickView'],
  };
  // caps truthy → summaryCore takes the gsOpts branch and passes gsOpts (with billing) to generateSummary.
  await expect(summaryCore(input, deps, { caps: SOME_CAPS, billing })).rejects.toBeTruthy();
  expect(billing.metered).toBe(true);   // FAILS if summaryCore drops billing into gsOpts (M6-1)
});

it('a metered-then-throw transcript resolution KEEPS: billing latch flips through summaryCore threading (rtsOpts)', async () => {
  const billing: BillingLatch = { metered: false };
  const deps: SummaryCoreDeps = {
    resolveTranscriptSegments: (async (_v: unknown, _u: unknown, _d: unknown, opts?: { billing?: BillingLatch }) => {
      if (opts?.billing) opts.billing.metered = true;                 // stands in for the primitive set-point
      throw new Error('transcript source blew up');
    }) as SummaryCoreDeps['resolveTranscriptSegments'],
    generateSummary: (async () => {
      throw new Error('should never be reached — resolveTranscriptSegments threw first');
    }) as SummaryCoreDeps['generateSummary'],
    extractQuickView: (async () => ({ tldr: '', takeaways: [] })) as SummaryCoreDeps['extractQuickView'],
  };
  // caps truthy → summaryCore takes the rtsOpts branch and passes rtsOpts (with billing) to resolveTranscriptSegments.
  await expect(summaryCore(input, deps, { caps: SOME_CAPS, billing })).rejects.toBeTruthy();
  expect(billing.metered).toBe(true);   // FAILS if summaryCore drops billing into rtsOpts (M6-1)
});
