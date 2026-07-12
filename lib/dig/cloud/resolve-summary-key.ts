import { assertCloudSummaryMdKey } from '@/lib/html-doc/assert-cloud-summary-md-key';

/** Resolves the summary md KEY for a video: the artifact record's key (`artifacts.summaryMd.key`),
 *  falling back to the top-level `summaryMd` — validated via `assertCloudSummaryMdKey`. Returns
 *  null when absent or when the key fails the single-component guard.
 *
 *  Does NOT gate on `artifacts.summaryMd.status === 'promoted'` the way `loadSummaryForServe`
 *  does (serve-summary-core.ts:49-51) — a strict status gate here would break the legitimate
 *  top-level `summaryMd` fallback for videos with no artifact record. The dig TRIGGER owns that
 *  gate: it enqueues a dig job only when `loadSummaryForServe` reports the summary promoted, so by
 *  the time this worker runs, the summary is already promoted. */
export function resolveSummaryMdKey(video: unknown): string | null {
  const v = video as { artifacts?: { summaryMd?: { key?: string } }; summaryMd?: string | null };
  const key = v.artifacts?.summaryMd?.key ?? v.summaryMd ?? null;
  if (!key) return null;
  try { assertCloudSummaryMdKey(key); } catch { return null; }
  return key;
}
