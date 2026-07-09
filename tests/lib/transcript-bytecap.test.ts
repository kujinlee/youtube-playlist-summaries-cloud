import {
  truncateSegmentsToByteCap,
  buildIndexedTranscript,
  resolveTranscriptTokens,
  type TranscriptSegment,
} from '../../lib/transcript-timestamps';

// A CJK/emoji segment set chosen so the RENDERED buildIndexedTranscript output's UTF-8
// byte length exceeds the cap while its JS `.length` (UTF-16 code units) stays UNDER it.
// This proves a `.length`-based truncation would wrongly keep too much — the whole point of
// measuring Buffer.byteLength(..., 'utf8').
//
// Per-line bytes (`[<i> @<m:ss>] <text>`, prefix `[0 @0:00] ` = 10 ASCII bytes):
//   seg0: 10 + 6×3 (CJK) = 28 bytes
//   seg1: 10 + 6×3 (CJK) = 28 bytes
//   seg2: 10 + 3×4 (emoji) = 22 bytes
//   joins: 2 newlines = 2 bytes  ->  full = 80 bytes
const SEGMENTS: TranscriptSegment[] = [
  { text: '你好世界你好', offset: 0, duration: 5 },
  { text: '再见世界再见', offset: 10, duration: 5 },
  { text: '🎉🎉🎉', offset: 20, duration: 5 },
];

const CAP = 60;

describe('truncateSegmentsToByteCap', () => {
  it('drops whole trailing segments until rendered UTF-8 byte length <= cap (byte, not .length)', () => {
    const full = buildIndexedTranscript(SEGMENTS);
    // Guard the premise: a `.length` impl would think the full set fits (under-count), but bytes exceed.
    expect(full.length).toBeLessThanOrEqual(CAP);           // 50 <= 60  -> `.length` keeps all 3 (WRONG)
    expect(Buffer.byteLength(full, 'utf8')).toBeGreaterThan(CAP); // 80 > 60 -> must truncate

    const result = truncateSegmentsToByteCap(SEGMENTS, CAP);

    // Whole trailing segment(s) dropped — never split. Only seg0+seg1 (57 bytes) fit under 60.
    expect(result).toEqual([SEGMENTS[0], SEGMENTS[1]]);
    expect(Buffer.byteLength(buildIndexedTranscript(result), 'utf8')).toBeLessThanOrEqual(CAP);
  });

  it('returns the segment list unchanged when the rendered output is already <= cap', () => {
    const result = truncateSegmentsToByteCap(SEGMENTS, 10_000);
    expect(result).toBe(SEGMENTS); // identity — no copy on the no-op path
  });

  it('returns an empty prefix when even the first segment renders over the cap', () => {
    const result = truncateSegmentsToByteCap(SEGMENTS, 5);
    expect(result).toEqual([]);
  });

  it('keeps every [[TS:n]] index in range for the truncated list fed to resolveTranscriptTokens', () => {
    const result = truncateSegmentsToByteCap(SEGMENTS, CAP); // [seg0, seg1]

    // Tokens referencing kept indices 0 and 1 resolve to ▶ lines; nothing raw leaks.
    const md = '## A\n[[TS:0]]\nbody\n## B\n[[TS:1]]\nmore';
    const out = resolveTranscriptTokens(md, result, 'vid1');
    expect((out.match(/▶/g) ?? []).length).toBe(2);
    expect(out).not.toContain('[[TS:');

    // A token referencing the DROPPED segment (index 2 == result.length) is out of range and
    // stripped — never emits a ▶ pointing at a segment the prompt no longer contained.
    const mdOob = '## A\n[[TS:2]]\nx';
    const outOob = resolveTranscriptTokens(mdOob, result, 'vid1');
    expect(outOob).not.toContain('▶');
    expect(outOob).not.toContain('[[TS:');
  });
});
