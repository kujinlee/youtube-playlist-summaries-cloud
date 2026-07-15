import { __test } from '@/lib/gemini';
import { timestampLine } from '@/lib/transcript-timestamps';

// Real canonical ▶ line (correct label + matching id) — a hand-rolled label like "0:00–0:00" would
// make extractTimeRange compute endSec=0 for every start, which always trips the endSec<=startSec
// guard in sectionStartsComplete regardless of start value. See tests/lib/summary-section-timestamps.test.ts.
const TS = (start: number, end: number) => timestampLine(start, end, 'v');
const mk = (body: string) => ({ summary: body, ratings: { usefulness: 3, depth: 3, originality: 3, recency: 3, completeness: 3 } } as never);

describe('scoreSummary uniqueness+monotonic timestamp criterion', () => {
  it('index 3 = 0 for missing, duplicate, or out-of-order starts; 1 only when unique+increasing', () => {
    expect(__test.scoreSummary(mk(['## 1. A', TS(10, 20), 'a', '', '## C', TS(30, 40), 'c'].join('\n')), true)[3]).toBe(1);
    expect(__test.scoreSummary(mk(['## 1. A', TS(10, 20), 'a', '', '## C', 'c'].join('\n')), true)[3]).toBe(0);       // missing
    expect(__test.scoreSummary(mk(['## 1. A', TS(10, 20), 'a', '', '## C', TS(10, 20), 'c'].join('\n')), true)[3]).toBe(0); // duplicate
  });
  it('no-segments short-circuits index 3 to 1 (E7)', () => {
    expect(__test.scoreSummary(mk(['## 1. A', 'a', '', '## C', 'c'].join('\n')), false)[3]).toBe(1);
  });
});
