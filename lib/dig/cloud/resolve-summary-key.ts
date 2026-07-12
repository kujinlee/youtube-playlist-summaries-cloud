import { assertCloudSummaryMdKey } from '@/lib/html-doc/assert-cloud-summary-md-key';

/** The authoritative summary md key for a video: the artifact record's key, falling back to the
 *  top-level `summaryMd` — the EXACT rule loadSummaryForServe uses (serve-summary-core.ts:56).
 *  Returns null when absent or when the key fails the single-component guard. */
export function resolveSummaryMdKey(video: unknown): string | null {
  const v = video as { artifacts?: { summaryMd?: { key?: string } }; summaryMd?: string | null };
  const key = v.artifacts?.summaryMd?.key ?? v.summaryMd ?? null;
  if (!key) return null;
  try { assertCloudSummaryMdKey(key); } catch { return null; }
  return key;
}
