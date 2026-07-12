import { assertCloudSummaryMdKey } from '@/lib/html-doc/assert-cloud-summary-md-key';
describe('assertCloudSummaryMdKey', () => {
  // Accept the exact shapes the ingestion pipeline produces — including unicode (Korean) bases,
  // which slugify preserves (\p{L}). An ASCII-only allowlist would wrongly 409 these.
  it.each([
    ['ascii serial+slug', '0007_intro.md'],
    ['hyphenated slug', '0007_deep-learning.md'],
    ['korean/CJK base', '0007_한국어제목.md'],
    ['empty slug (serial only)', '0007_.md'],
    // max realistic pipeline key: padSerial + '_' + slugify's 60-char cap — must not false-reject.
    ['max-length slug', `0007_${'a'.repeat(60)}.md`],
  ])('accepts a legit single-component .md basename: %s', (_l, key) => {
    expect(() => assertCloudSummaryMdKey(key)).not.toThrow();
  });

  it.each([
    ['nested', 'nested/foo.md'], ['backslash', 'a\\b.md'], ['parent', '../foo.md'],
    ['double-dot', 'foo..md'], ['NUL', 'foo\0.md'], ['newline', 'foo\nbar.md'],
    ['tab', 'foo\tbar.md'], ['leading-space', ' foo.md'], ['encoded-slash', 'nested%2ffoo.md'],
    ['homoglyph-slash-FF0F', 'a／b.md'], ['fraction-slash-2044', 'a⁄b.md'],
    ['division-slash-2215', 'a∕b.md'], ['non-md', 'foo.pdf'], ['no-suffix', 'foo'],
    ['empty-base', '.md'], ['leading-dot', '.foo.md'], ['empty', ''],
    ['too-long', `${'a'.repeat(300)}.md`],
  ])('rejects %s with statusCode 409', (_l, key) => {
    try { assertCloudSummaryMdKey(key); throw new Error('did not throw'); }
    catch (e: any) { expect(e.statusCode).toBe(409); }
  });

  it.each([['null', null], ['undefined', undefined], ['number', 123], ['object', {}]])(
    'rejects non-string %s with statusCode 409', (_l, key) => {
    try { assertCloudSummaryMdKey(key as any); throw new Error('did not throw'); }
    catch (e: any) { expect(e.statusCode).toBe(409); }
  });
});
