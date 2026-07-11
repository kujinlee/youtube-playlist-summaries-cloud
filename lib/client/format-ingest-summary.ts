import type { ProducerCounts } from '@/lib/job-queue/producer';

export function formatIngestSummary(
  counts: ProducerCounts,
  dailyCapReached = false,
  challengeRequired = false,
): { line: string; challengeLine: string | null } {
  const parts: string[] = [`Queued ${counts.enqueued}`];
  if (counts.joined > 0) parts.push(`${counts.joined} already in progress`);
  if (counts.skipped > 0) parts.push(`${counts.skipped} skipped (no captions)`);
  if (counts.tooLong > 0) parts.push(`${counts.tooLong} too long (>30 min)`);
  if (counts.quotaBlocked > 0) parts.push(`${counts.quotaBlocked} blocked (quota)`);
  if (counts.capBlocked > 0 || dailyCapReached) parts.push(`${counts.capBlocked} blocked (daily cap reached)`);
  if (counts.failed > 0) parts.push(`${counts.failed} failed`);
  return {
    line: parts.join(' · '),
    challengeLine: challengeRequired ? "You're adding playlists quickly." : null,
  };
}
