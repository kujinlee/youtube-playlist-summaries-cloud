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
});
