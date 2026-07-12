import { assertCloudSummaryMdKey } from '@/lib/html-doc/assert-cloud-summary-md-key';
describe('assertCloudSummaryMdKey', () => {
  it('accepts a single-component .md basename', () => {
    expect(() => assertCloudSummaryMdKey('0007_intro.md')).not.toThrow();
  });
  it.each([['nested','nested/foo.md'],['backslash','a\\b.md'],['parent','../foo.md'],
    ['NUL','foo\0.md'],['non-md','foo.pdf'],['no-suffix','foo'],['empty-base','.md'],['empty','']])(
    'rejects %s with statusCode 409', (_l, key) => {
    try { assertCloudSummaryMdKey(key); throw new Error('did not throw'); }
    catch (e: any) { expect(e.statusCode).toBe(409); }
  });
});
