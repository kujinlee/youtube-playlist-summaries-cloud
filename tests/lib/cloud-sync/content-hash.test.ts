import { mdHash, canonicalizeMd } from '@/lib/cloud-sync/content-hash';

describe('canonicalizeMd', () => {
  it('normalizes CRLF and CR to LF', () => {
    expect(canonicalizeMd('a\r\nb\rc')).toBe('a\nb\nc\n');
  });
  it('collapses trailing newlines to exactly one', () => {
    expect(canonicalizeMd('body\n\n\n')).toBe('body\n');
    expect(canonicalizeMd('body')).toBe('body\n');
  });
  it('applies Unicode NFC', () => {
    // "é" as combining sequence (U+0065 U+0301) → precomposed (U+00E9)
    expect(canonicalizeMd('é')).toBe('é\n');
  });
});

describe('mdHash', () => {
  it('is stable, hex, 64 chars', () => {
    const h = mdHash('# Title\n\nbody\n');
    expect(h).toMatch(/^[0-9a-f]{64}$/);
    expect(mdHash('# Title\n\nbody\n')).toBe(h);
  });
  it('is invariant to line-ending and trailing-newline differences (cross-backend equality)', () => {
    // Local file may store CRLF + trailing blank line; Postgres jsonb may store LF only.
    expect(mdHash('# T\r\n\r\nbody\r\n\r\n')).toBe(mdHash('# T\n\nbody\n'));
  });
  it('differs when the body content differs', () => {
    expect(mdHash('a\n')).not.toBe(mdHash('b\n'));
  });
});
