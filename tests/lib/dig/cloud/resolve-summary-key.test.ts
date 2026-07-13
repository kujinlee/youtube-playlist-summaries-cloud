import { resolveSummaryMdKey } from '@/lib/dig/cloud/resolve-summary-key';

describe('resolveSummaryMdKey', () => {
  it('prefers artifacts.summaryMd.key over the top-level summaryMd fallback', () => {
    const video = { summaryMd: '0001_old.md', artifacts: { summaryMd: { key: '0001_new.md' } } };
    expect(resolveSummaryMdKey(video)).toBe('0001_new.md');
  });

  it('falls back to the top-level summaryMd when the artifact key is absent', () => {
    const video = { summaryMd: '0001_old.md' };
    expect(resolveSummaryMdKey(video)).toBe('0001_old.md');
  });

  it('returns null when no key is present at all', () => {
    const video = { summaryMd: null };
    expect(resolveSummaryMdKey(video)).toBeNull();
  });

  it('returns null for a corrupt (nested) key that fails the single-component guard', () => {
    const video = { summaryMd: 'nested/foo.md' };
    expect(resolveSummaryMdKey(video)).toBeNull();
  });
});
