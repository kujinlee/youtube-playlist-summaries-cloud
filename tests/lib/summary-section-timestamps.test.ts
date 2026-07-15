import { allocateSectionStarts, sectionStartsComplete } from '@/lib/summary-section-timestamps';

const strictlyIncreasing = (a: number[]) => a.every((v, i) => i === 0 || v > a[i - 1]);

describe('allocateSectionStarts', () => {
  const D = 1000; // videoDuration

  it('all-known-good → returned unchanged (byte-identity in the common case)', () => {
    expect(allocateSectionStarts([100, 200, 300], 0, D)).toEqual([100, 200, 300]);
  });

  it('missing middle → synthesized strictly between neighbors', () => {
    const r = allocateSectionStarts([208, null, 369], 0, D);
    expect(r[0]).toBe(208); expect(r[2]).toBe(369);
    expect(r[1]).toBeGreaterThan(208); expect(r[1]).toBeLessThan(369);
    expect(strictlyIncreasing(r)).toBe(true);
  });

  it('duplicate known (floor collision) → the later one is reassigned upward, unique', () => {
    const r = allocateSectionStarts([100, 100, 400], 0, D);
    expect(r[0]).toBe(100);
    expect(strictlyIncreasing(r)).toBe(true);
    expect(new Set(r).size).toBe(3);
  });

  it('non-monotonic known → later value reassigned to restore strict increase', () => {
    const r = allocateSectionStarts([100, 50, 200], 0, D);
    expect(strictlyIncreasing(r)).toBe(true);
  });

  it('tight gap: [100, missing, 101] → the colliding known 101 is bumped, all unique', () => {
    const r = allocateSectionStarts([100, null, 101], 0, D);
    expect(r[0]).toBe(100);
    expect(strictlyIncreasing(r)).toBe(true);
    expect(new Set(r).size).toBe(3);
  });

  it('first missing → bounded at/after firstStart; last missing → below videoDuration', () => {
    const first = allocateSectionStarts([null, 400], 0, D);
    expect(first[0]).toBeGreaterThanOrEqual(0); expect(first[0]).toBeLessThan(400);
    const last = allocateSectionStarts([100, null], 0, D);
    expect(last[1]).toBeGreaterThan(100); expect(last[1]).toBeLessThan(D);
  });

  it('all missing → strictly increasing, unique, within (firstStart, videoDuration)', () => {
    const r = allocateSectionStarts([null, null, null], 0, D);
    expect(strictlyIncreasing(r)).toBe(true);
    expect(new Set(r).size).toBe(3);
    expect(r[r.length - 1]).toBeLessThan(D);
  });

  it('pathological (more sections than seconds) stays strictly increasing + unique', () => {
    const r = allocateSectionStarts([null, null, null, null], 0, 2);
    expect(strictlyIncreasing(r)).toBe(true);
    expect(new Set(r).size).toBe(4);
  });
});

import { timestampLine } from '@/lib/transcript-timestamps';
// videoId MUST match the id passed to ensureSectionTimestamps in the Task-2 tests ('vid'), so a
// genuinely-unchanged section's existing line is byte-identical to its canonical form → the finalizer's
// `lines[slot] === canonical → keep` branch is actually exercised (round-4 Low). A mismatched id would
// silently rewrite every "kept" section (behaviorally identical since start/end are preserved, but the
// keep branch would go uncovered).
const L = (start: number, end: number) => timestampLine(start, end, 'vid'); // real canonical ▶ line (correct label + matching id)
describe('sectionStartsComplete', () => {
  it('true only when every section has a ▶, starts strictly increasing + unique, AND end > start', () => {
    expect(sectionStartsComplete(['## 1. A', L(10, 30), 'a', '', '## Conclusion', L(30, 60), 'c'].join('\n'))).toBe(true);
    expect(sectionStartsComplete(['## 1. A', L(10, 30), 'a', '', '## 2. B', 'b'].join('\n'))).toBe(false);          // missing
    expect(sectionStartsComplete(['## 1. A', L(10, 30), 'a', '', '## 2. B', L(10, 30), 'b'].join('\n'))).toBe(false); // duplicate start
    expect(sectionStartsComplete(['## 1. A', L(30, 60), 'a', '', '## 2. B', L(10, 30), 'b'].join('\n'))).toBe(false); // out of order
    expect(sectionStartsComplete(['## 1. A', L(30, 30), 'a', '', '## 2. B', L(40, 60), 'b'].join('\n'))).toBe(false); // end <= start
  });
  it('malformed ▶ URL counts as missing (render-parser truth)', () => {
    expect(sectionStartsComplete(['## 1. A', '▶ [x](not-a-url?t=10s)', 'a'].join('\n'))).toBe(false);
  });
});

import { ensureSectionTimestamps } from '@/lib/summary-section-timestamps';
import { parseSections } from '@/lib/html-doc/parse';
// NOTE: `L` (= timestampLine(start,end,'v')) and `timestampLine` are already imported/declared
// earlier in this file (Task 1 Step 6 append). Do not redeclare them.
// Deviation from brief: `parseSections` was NOT already imported in Task 1's committed test file
// (only `timestampLine` was) — added here since these tests genuinely need it.

const startsOf = (md: string) => parseSections(md).map((s) => s.timeRange?.startSec ?? null);
const B = { firstStart: 0, videoDuration: 1000 };
const uniqueIncreasing = (md: string) => {
  const s = startsOf(md) as number[];
  return s.every((v) => v !== null) && s.every((v, i) => i === 0 || v > s[i - 1]) && new Set(s).size === s.length;
};
const endsWellFormed = (md: string) => parseSections(md).every((x) => x.timeRange!.endSec > x.timeRange!.startSec);

describe('ensureSectionTimestamps', () => {
  it('idempotent no-op when already complete + canonical (end = next start)', () => {
    const md = ['## 1. A', L(10, 30), 'a', '', '## Conclusion', L(30, 1000), 'c'].join('\n');
    expect(ensureSectionTimestamps(md, 'vid', B)).toBe(md);
  });

  it('missing middle → inserts ▶ strictly between neighbors AND updates the previous end (no overlap)', () => {
    const md = ['## 1. A', L(208, 369), 'a', '', '## 2. B', 'b', '', '## 3. C', L(369, 1000), 'c'].join('\n');
    const out = ensureSectionTimestamps(md, 'vid', B);
    expect(uniqueIncreasing(out)).toBe(true);
    expect(endsWellFormed(out)).toBe(true);
    const p = parseSections(out);
    expect(p[0].timeRange!.endSec).toBe(p[1].timeRange!.startSec);   // A's end canonicalized to B's start (was 369 → overlap)
    expect(p[1].timeRange!.startSec).toBeGreaterThan(208);
    expect(p[1].timeRange!.startSec).toBeLessThan(369);
    expect(p[2].timeRange!.startSec).toBe(369);
  });

  it('DUPLICATE existing ▶ (floor collision) → REWRITES the later line, all unique, one ▶ each (R2-H1)', () => {
    const md = ['## 1. A', L(100, 200), 'a', '', '## 2. B', L(100, 300), 'b', '', '## 3. C', L(400, 1000), 'c'].join('\n');
    const out = ensureSectionTimestamps(md, 'vid', B);
    expect(uniqueIncreasing(out)).toBe(true);
    expect(endsWellFormed(out)).toBe(true);
    expect((out.match(/^▶/gm) ?? []).length).toBe(3);
  });

  it('tight gap [100, missing, 101] → known 101 MINIMALLY bumped to 102, all unique (R2-B1 + Codex M1)', () => {
    const md = ['## 1. A', L(100, 200), 'a', '', '## 2. B', 'b', '', '## 3. C', L(101, 1000), 'c'].join('\n');
    const out = ensureSectionTimestamps(md, 'vid', B);
    expect(startsOf(out)).toEqual([100, 101, 102]); // minimal editorial drift, not a jump to mid-duration
  });

  it('malformed existing ▶ → REPLACED in place, not duplicated', () => {
    const md = ['## 1. A', '▶ [x](not-a-url?t=10s)', 'a', '', '## Conclusion', L(300, 1000), 'c'].join('\n');
    const out = ensureSectionTimestamps(md, 'vid', B);
    expect(uniqueIncreasing(out)).toBe(true);
    expect(endsWellFormed(out)).toBe(true);
    expect((out.match(/^▶/gm) ?? []).length).toBe(2);
  });

  it('every section has endSec > startSec after normalization (R2-M2)', () => {
    const md = ['## 1. A', L(208, 369), 'a', '', '## 2. B', 'b', '', '## 3. C', L(369, 1000), 'c'].join('\n');
    expect(endsWellFormed(ensureSectionTimestamps(md, 'vid', B))).toBe(true);
  });

  it('pathological videoDuration ≤ section count → still unique+increasing, last end > start (Codex M2/Claude L1)', () => {
    const md = ['## 1. A', 'a', '', '## 2. B', 'b', '', '## 3. C', 'c'].join('\n');
    const out = ensureSectionTimestamps(md, 'vid', { firstStart: 0, videoDuration: 2 });
    expect(uniqueIncreasing(out)).toBe(true);
    expect(endsWellFormed(out)).toBe(true);
  });

  it('--- divider before the ▶ is respected (render-parser parity)', () => {
    const md = ['## 1. A', '', '---', '', L(10, 1000), 'a', '', '## Conclusion', 'c'].join('\n');
    const out = ensureSectionTimestamps(md, 'vid', B);
    expect(uniqueIncreasing(out)).toBe(true);
    expect(endsWellFormed(out)).toBe(true);
  });
});
