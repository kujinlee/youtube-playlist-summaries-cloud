import { extractScriptUrls } from '@/lib/security/bundle-secret-scan';

const BASE = 'https://example.fly.dev';

describe('extractScriptUrls', () => {
  it('resolves a root-relative Next.js chunk against the base URL', () => {
    const html = '<script src="/_next/static/chunks/main-abc123.js"></script>';
    expect(extractScriptUrls(html, BASE)).toEqual([
      'https://example.fly.dev/_next/static/chunks/main-abc123.js',
    ]);
  });

  it('keeps an absolute same-origin URL as-is', () => {
    const html = `<script src="${BASE}/_next/static/chunks/x.js"></script>`;
    expect(extractScriptUrls(html, BASE)).toEqual([`${BASE}/_next/static/chunks/x.js`]);
  });

  it('handles single quotes and extra attributes', () => {
    const html = `<script defer src='/a.js' crossorigin></script><script src="/b.js" async></script>`;
    expect(extractScriptUrls(html, BASE)).toEqual([`${BASE}/a.js`, `${BASE}/b.js`]);
  });

  it('skips inline scripts, which have no src', () => {
    expect(extractScriptUrls('<script>var x=1</script>', BASE)).toEqual([]);
  });

  it('does not follow scripts hosted on another origin', () => {
    const html = '<script src="https://cdn.example.com/evil.js"></script>';
    expect(extractScriptUrls(html, BASE)).toEqual([]);
  });

  it('de-duplicates a chunk referenced twice', () => {
    const html = '<script src="/a.js"></script><script src="/a.js"></script>';
    expect(extractScriptUrls(html, BASE)).toEqual([`${BASE}/a.js`]);
  });

  // These four pin reference styles Next.js CAN emit. On the 2026-08-11 build they gain nothing —
  // /login yields the same 9 URLs with or without them, because every _next path and href there is
  // already a script tag. They are here because the failure they prevent is SILENT: a chunk that is
  // preloaded but never script-tagged would be skipped by a <script src>-only reader, which would
  // then print "clean" having missed it. Cheap to keep, and the regression would be invisible.
  it('includes chunks referenced by a preload link, not just script tags', () => {
    const html = '<link rel="preload" as="script" href="/_next/static/chunks/lazy-1.js"/>';
    expect(extractScriptUrls(html, BASE)).toEqual([`${BASE}/_next/static/chunks/lazy-1.js`]);
  });

  it('includes a chunk path that appears only inside an inline flight payload', () => {
    const html = '<script>self.__next_f.push([1,"a:\\"/_next/static/chunks/deep-2.js\\""])</script>';
    expect(extractScriptUrls(html, BASE)).toEqual([`${BASE}/_next/static/chunks/deep-2.js`]);
  });

  it('still ignores a foreign-origin chunk path', () => {
    const html = '<link rel="preload" as="script" href="https://cdn.example.com/x.js"/>';
    expect(extractScriptUrls(html, BASE)).toEqual([]);
  });

  it('does not double-count a chunk that is both preloaded and script-tagged', () => {
    const html =
      '<link rel="preload" as="script" href="/_next/static/chunks/a.js"/>' +
      '<script src="/_next/static/chunks/a.js"></script>';
    expect(extractScriptUrls(html, BASE)).toEqual([`${BASE}/_next/static/chunks/a.js`]);
  });
});
