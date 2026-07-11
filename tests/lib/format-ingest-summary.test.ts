import { formatIngestSummary } from '@/lib/client/format-ingest-summary';
const base = { enqueued: 0, joined: 0, skipped: 0, failed: 0, quotaBlocked: 0, capBlocked: 0, tooLong: 0 };

describe('formatIngestSummary', () => {
  it('base case — only enqueued', () => {
    expect(formatIngestSummary({ ...base, enqueued: 42 })).toEqual({ line: 'Queued 42', challengeLine: null });
  });
  it('appends non-zero buckets in the spec order', () => {
    expect(formatIngestSummary({ enqueued: 42, joined: 1, skipped: 3, tooLong: 2, quotaBlocked: 4, capBlocked: 5, failed: 6 }).line).toBe(
      'Queued 42 · 1 already in progress · 3 skipped (no captions) · 2 too long (>30 min) · 4 blocked (quota) · 5 blocked (daily cap reached) · 6 failed');
  });
  it('omits zero buckets', () => {
    expect(formatIngestSummary({ ...base, enqueued: 5, skipped: 2 }).line).toBe('Queued 5 · 2 skipped (no captions)');
  });
  it('shows daily-cap clause when dailyCapReached even if capBlocked is 0', () => {
    expect(formatIngestSummary({ ...base, enqueued: 1 }, true).line).toBe('Queued 1 · 0 blocked (daily cap reached)');
  });
  it('does not double the daily-cap clause when both capBlocked>0 and dailyCapReached', () => {
    const line = formatIngestSummary({ ...base, enqueued: 1, capBlocked: 3 }, true).line;
    expect(line).toBe('Queued 1 · 3 blocked (daily cap reached)');
    expect(line.match(/daily cap reached/g)).toHaveLength(1);
  });
  it('zero-queued still renders', () => {
    expect(formatIngestSummary({ ...base, tooLong: 2, skipped: 3 }).line).toBe('Queued 0 · 3 skipped (no captions) · 2 too long (>30 min)');
  });
  it('challengeRequired adds a soft second line', () => {
    expect(formatIngestSummary({ ...base, enqueued: 1 }, false, true).challengeLine).toBe("You're adding playlists quickly.");
  });
});
