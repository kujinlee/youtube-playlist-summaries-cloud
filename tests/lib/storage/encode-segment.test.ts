import { encodeSegment, SAFE, LIMIT } from '@/lib/storage/supabase/encode-segment';

describe('encodeSegment', () => {
  it('behavior 1 — a SAFE segment within LIMIT is byte-identical', () => {
    expect(encodeSegment('003_intro-part2.md')).toBe('003_intro-part2.md');
  });

  it('passes an empty segment through, so a trailing slash survives', () => {
    expect(encodeSegment('')).toBe('');
  });

  it('behavior 2 — a non-ASCII segment becomes an ASCII physical key', () => {
    const out = encodeSegment('003_한국어.md');   // Korean, a literal — not a control character
    expect(out).toMatch(/^[A-Za-z0-9._=-]+$/);
    expect(out).toContain('=h');
    expect(out.endsWith('.md')).toBe(true);
  });

  it('behavior 3 — NFC and NFD forms encode DIFFERENTLY', () => {
    const nfc = 'café.md'.normalize('NFC');
    const nfd = 'café.md'.normalize('NFD');
    expect(nfc).not.toBe(nfd);
    expect(encodeSegment(nfc)).not.toBe(encodeSegment(nfd));
  });

  it('behavior 4 — identity and hash branches are DISJOINT: `=` is not in SAFE', () => {
    expect(SAFE.test('a=b')).toBe(false);
    expect(encodeSegment('한.md')).toContain('=');
  });

  it('behavior 4 — the hash branch is deterministic', () => {
    expect(encodeSegment('한.md')).toBe(encodeSegment('한.md'));
  });

  it('behavior 5 — every encoded segment is at most 65 characters', () => {
    // 65 is TIGHT, not slack: a 32-char SAFE head + `=h` + 22 digest chars + an 8-char
    // extension is exactly 65, and MEASURED at 65. This fixture is far under it (the
    // Korean head is empty, so it encodes to 27) — the worst case is asserted below.
    expect(encodeSegment('한'.repeat(400) + '.md').length).toBeLessThanOrEqual(65);
    expect(encodeSegment('a'.repeat(32) + '\u{1F600}' + '.abcdefgh').length).toBe(65);
  });

  it('behavior 5 — an over-LIMIT ASCII segment is hashed, not passed through', () => {
    const long = 'a'.repeat(LIMIT + 1);
    expect(encodeSegment(long)).not.toBe(long);
    expect(encodeSegment(long)).toContain('=h');
  });

  it('hashes utf16le, so two DIFFERENT lone surrogates differ', () => {
    // The reason §3.2 chose utf16le: utf8 maps both to U+FFFD and they collide.
    expect(encodeSegment('x\uD840.md')).not.toBe(encodeSegment('x\uD850.md'));
  });

  it('behavior 1 + 5 — property SAMPLE over the codepoint space', () => {
    // ⚠ Round-1 L2: a stride SAMPLES, it does not cover. This visits ~1.6% of the space and is
    // labelled a smoke sweep for that reason.
    for (let cp = 0; cp <= 0x10ffff; cp += 0x40) {
      if (cp >= 0xd800 && cp <= 0xdfff) continue;
      const out = encodeSegment(`003_x${String.fromCodePoint(cp)}.md`);
      // The PHYSICAL alphabet is SAFE plus `=`, the hash-branch marker. Testing `SAFE.test(out)`
      // here contradicts behavior 4 two tests above — `=` is excluded from SAFE ON PURPOSE, so
      // that assertion fails on 100% of non-ASCII iterations after a CORRECT implementation.
      expect(out).toMatch(/^[A-Za-z0-9._=-]+$/);
      expect(out.length).toBeLessThanOrEqual(65);
    }
  });
});
