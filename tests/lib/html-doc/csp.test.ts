import { buildSummaryCsp, buildDigCsp } from '@/lib/html-doc/csp';

describe('buildDigCsp (interactive cloud dig doc)', () => {
  it('permits same-origin fetch — connect-src \'self\' (the poll engine POSTs/polls /api and re-fetches location.href)', () => {
    const csp = buildDigCsp('NONCE1');
    expect(csp).toContain("connect-src 'self'");
    // still locked-down otherwise
    expect(csp).toContain("default-src 'none'");
    expect(csp).toContain("script-src 'nonce-NONCE1'");
    expect(csp).toContain("object-src 'none'");
    expect(csp).toContain("frame-ancestors 'none'");
  });
});

describe('buildSummaryCsp (static summary/share doc) — must NOT loosen', () => {
  it('has no connect-src (the static doc never fetches; keep default-src none authoritative)', () => {
    const csp = buildSummaryCsp('NONCE1');
    expect(csp).not.toContain('connect-src');
    expect(csp).toContain("default-src 'none'");
  });
});
