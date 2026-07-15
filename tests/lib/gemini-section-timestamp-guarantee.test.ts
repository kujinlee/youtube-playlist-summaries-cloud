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

import { GoogleGenerativeAI } from '@google/generative-ai';
import { generateSummary } from '@/lib/gemini';
import { parseSections } from '@/lib/html-doc/parse';
import { sectionStartsComplete } from '@/lib/summary-section-timestamps';
import type { TranscriptSegment } from '@/lib/transcript-timestamps';

jest.mock('@google/generative-ai', () => ({ ...jest.requireActual('@google/generative-ai'), GoogleGenerativeAI: jest.fn() }));
const mockGenerateContent = jest.fn();
const mockGetGenerativeModel = jest.fn();

describe('generateSummary end-to-end section-timestamp guarantee', () => {
  beforeEach(() => {
    jest.resetAllMocks();
    mockGetGenerativeModel.mockReturnValue({ generateContent: mockGenerateContent });
    (GoogleGenerativeAI as jest.Mock).mockImplementation(() => ({ getGenerativeModel: mockGetGenerativeModel }));
    process.env.GEMINI_API_KEY = 'test-api-key';
  });
  afterEach(() => { delete process.env.GEMINI_API_KEY; });

  const segs: TranscriptSegment[] = Array.from({ length: 12 }, (_, i) => ({ text: `seg ${i}`, offset: i * 100, duration: 100 }));

  it('every section gets a unique, monotonic ▶ (out-of-order + omitted tokens)', async () => {
    const body = [
      '## 1. Alpha', '[[TS:5]]', 'alpha', '', '---', '',
      '## 2. Beta', '[[TS:1]]', 'beta', '', '---', '',   // out-of-order → LIS drops → normalizer synthesizes
      '## 3. Gamma', 'gamma (no token)', '', '---', '',   // omitted → re-roll then synthesize
      '## Conclusion', '[[TS:10]]', 'wrap.', // terminal punctuation → checkSummaryCompleteness sees this as complete
    ].join('\n');
    mockGenerateContent.mockResolvedValue({ response: { text: () => JSON.stringify({
      summary: body, ratings: { usefulness: 4, depth: 4, originality: 4, recency: 4, completeness: 4 },
      videoType: 'Analysis', audience: 'Intermediate', tags: ['a', 'b', 'c'], tldr: 'This video explains things.', takeaways: ['x', 'y', 'z'],
    }) } });

    const r = await generateSummary(segs, 'en', 'vidABC');

    const sections = parseSections(r.summary);
    expect(sections.map((s) => s.title)).toEqual(['Alpha', 'Beta', 'Gamma', 'Conclusion']);
    expect(sectionStartsComplete(r.summary)).toBe(true);
    const starts = sections.map((s) => s.timeRange!.startSec);
    for (let i = 1; i < starts.length; i++) expect(starts[i]).toBeGreaterThan(starts[i - 1]);
    expect(new Set(starts).size).toBe(starts.length);
    for (const s of sections) expect(s.timeRange!.endSec).toBeGreaterThan(s.timeRange!.startSec);
    expect(mockGenerateContent.mock.calls.length).toBeLessThanOrEqual(2); // TIMESTAMP_MISS_CAP (money)
  });
});
