import { summaryCore } from '../../lib/ingestion/summary-core';

const baseInput = {
  videoId: 'vid',
  title: 'T',
  youtubeUrl: 'https://y/watch?v=vid',
  channel: 'C',
  durationSeconds: 90,
  baseName: '1_t',
};

const segments = [{ text: 'hi', offset: 0, duration: 5 }];

function makeDeps(overrides: Partial<{
  resolveTranscriptSegments: jest.Mock;
  generateSummary: jest.Mock;
  extractQuickView: jest.Mock;
}> = {}) {
  return {
    resolveTranscriptSegments: overrides.resolveTranscriptSegments
      ?? jest.fn().mockResolvedValue({ segments, source: 'captions' }),
    generateSummary: overrides.generateSummary
      ?? jest.fn().mockResolvedValue({
        summary: '## 1. Alpha\n▶ [0:00](u)\nAlpha body.\n---\n## Conclusion\n▶ [1:00](u)\nWrap.',
        ratings: { usefulness: 4, depth: 4, originality: 4, recency: 4, completeness: 4 },
        overallScore: 4, videoType: 'Analysis', audience: 'Intermediate',
        tags: ['x'], tldr: 'This video explains alpha.', takeaways: ['Do alpha'],
      }),
    extractQuickView: overrides.extractQuickView ?? jest.fn().mockResolvedValue({
      tldr: 'Fallback tldr', takeaways: ['Fallback takeaway'],
    }),
  };
}

describe('summaryCore', () => {
  it('builds mdContent + geminiFields when generateSummary returns tldr/takeaways', async () => {
    const deps = makeDeps();
    const res = await summaryCore(baseInput, deps);

    expect(res.mdContent).toContain('Alpha body.\n\n---\n\n## Conclusion');
    expect(res.mdContent).toContain('> **Concepts:**');
    expect(res.mdContent.indexOf('This video explains alpha.')).toBeLessThan(
      res.mdContent.indexOf('## 1. Alpha'),
    );
    expect(res.quickView).toEqual({ tldr: 'This video explains alpha.', takeaways: ['Do alpha'] });
    expect(res.geminiFields).toEqual({
      language: 'en',
      ratings: { usefulness: 4, depth: 4, originality: 4, recency: 4, completeness: 4 },
      overallScore: 4,
      videoType: 'Analysis',
      audience: 'Intermediate',
      tags: ['x'],
      tldr: 'This video explains alpha.',
      takeaways: ['Do alpha'],
    });
    expect(deps.extractQuickView).not.toHaveBeenCalled();
    expect(res.frontmatter.startsWith('---\ntags:')).toBe(true);
    expect(res.markdown).not.toContain('> [!summary] Quick Reference');
  });

  it('falls back to extractQuickView when generateSummary omits tldr/takeaways', async () => {
    const generateSummary = jest.fn().mockResolvedValue({
      summary: '## 1. Alpha\n▶ [0:00](u)\nAlpha body.\n---\n## Conclusion\n▶ [1:00](u)\nWrap.',
      ratings: { usefulness: 4, depth: 4, originality: 4, recency: 4, completeness: 4 },
      overallScore: 4, videoType: 'Analysis', audience: 'Intermediate', tags: ['x'],
      tldr: undefined, takeaways: undefined,
    });
    const deps = makeDeps({ generateSummary });
    const res = await summaryCore(baseInput, deps);

    expect(deps.extractQuickView).toHaveBeenCalledTimes(1);
    expect(res.mdContent).toContain('> **Concepts:**');
    expect(res.mdContent).toContain('Fallback tldr');
    expect(res.quickView).toEqual({ tldr: 'Fallback tldr', takeaways: ['Fallback takeaway'] });
    expect(res.geminiFields.tldr).toBe('Fallback tldr');
    expect(res.geminiFields.takeaways).toEqual(['Fallback takeaway']);
  });

  it('clears tldr/takeaways and omits the callout when extractQuickView fallback throws', async () => {
    const generateSummary = jest.fn().mockResolvedValue({
      summary: '## 1. Alpha\n▶ [0:00](u)\nAlpha body.\n---\n## Conclusion\n▶ [1:00](u)\nWrap.',
      ratings: { usefulness: 4, depth: 4, originality: 4, recency: 4, completeness: 4 },
      overallScore: 4, videoType: 'Analysis', audience: 'Intermediate', tags: ['x'],
      tldr: undefined, takeaways: undefined,
    });
    const extractQuickView = jest.fn().mockRejectedValue(new Error('boom'));
    const deps = makeDeps({ generateSummary, extractQuickView });
    const res = await summaryCore(baseInput, deps);

    expect(res.mdContent).not.toContain('> [!summary] Quick Reference');
    expect(res.mdContent).toBe(res.markdown);
    expect(res.quickView).toBeNull();
    expect(res.geminiFields.tldr).toBeUndefined();
    expect(res.geminiFields.takeaways).toBeUndefined();
  });

  it('with caps: truncates the segment list and forwards caps to all three deps', async () => {
    // Two segments whose rendered buildIndexedTranscript exceeds transcriptInputBytes so the
    // second is dropped; the TRUNCATED list must flow into generateSummary (which builds both
    // the prompt and resolveTranscriptTokens from the same array).
    const bigSegments = [
      { text: 'hello world one', offset: 0, duration: 5 },   // `[0 @0:00] hello world one` = 25 bytes
      { text: 'second segment two', offset: 10, duration: 5 }, // dropped: full = 54 bytes > 30
    ];
    const caps = {
      transcribeInputTokens: 300000,
      transcribeOutputTokens: 32768,
      transcriptInputBytes: 30,
      summaryOutputTokens: 8192,
    };
    const resolveTranscriptSegments = jest.fn().mockResolvedValue({ segments: bigSegments, source: 'captions' });
    const generateSummary = jest.fn().mockResolvedValue({
      summary: '## 1. Alpha\n▶ [0:00](u)\nAlpha body.\n---\n## Conclusion\n▶ [1:00](u)\nWrap.',
      ratings: { usefulness: 4, depth: 4, originality: 4, recency: 4, completeness: 4 },
      overallScore: 4, tldr: undefined, takeaways: undefined, // force the extractQuickView fallback
    });
    const extractQuickView = jest.fn().mockResolvedValue({ tldr: 'x', takeaways: ['y'] });
    const deps = makeDeps({ resolveTranscriptSegments, generateSummary, extractQuickView });

    await summaryCore(baseInput, deps, { caps });

    // caps forwarded in opts to resolveTranscriptSegments (no signal ⇒ opts is exactly { caps })
    expect(resolveTranscriptSegments).toHaveBeenCalledWith('vid', baseInput.youtubeUrl, 90, { caps });
    // generateSummary receives the TRUNCATED list (first segment only) + caps in opts
    const gsArgs = generateSummary.mock.calls[0];
    expect(gsArgs[0]).toEqual([bigSegments[0]]);
    expect(gsArgs[1]).toBe('en');
    expect(gsArgs[2]).toBe('vid');
    expect(gsArgs[3]).toEqual({ caps });
    // extractQuickView receives caps as its 2nd positional arg
    expect(extractQuickView).toHaveBeenCalledWith(expect.any(String), caps);
  });

  it('without caps: no truncation, no caps forwarded (local pipeline unchanged)', async () => {
    const multi = [
      { text: 'aaa', offset: 0, duration: 5 },
      { text: 'bbb', offset: 10, duration: 5 },
    ];
    const resolveTranscriptSegments = jest.fn().mockResolvedValue({ segments: multi, source: 'captions' });
    const generateSummary = jest.fn().mockResolvedValue({
      summary: '## 1. Alpha\n▶ [0:00](u)\nAlpha body.\n---\n## Conclusion\n▶ [1:00](u)\nWrap.',
      ratings: { usefulness: 4, depth: 4, originality: 4, recency: 4, completeness: 4 },
      overallScore: 4, tldr: 'This video explains alpha.', takeaways: ['Do alpha'],
    });
    const deps = makeDeps({ resolveTranscriptSegments, generateSummary });

    await summaryCore(baseInput, deps);

    // Exactly 3 args (no opts object) on both deps ⇒ byte-identical to the pre-1D local call shape.
    expect(resolveTranscriptSegments).toHaveBeenCalledWith('vid', baseInput.youtubeUrl, 90);
    expect(generateSummary).toHaveBeenCalledWith(multi, 'en', 'vid'); // full set — no truncation
  });

  it('threads opts.signal into resolveTranscriptSegments and generateSummary but not extractQuickView', async () => {
    const controller = new AbortController();
    const resolveTranscriptSegments = jest.fn().mockResolvedValue({ segments, source: 'captions' });
    const generateSummary = jest.fn().mockResolvedValue({
      summary: 'body',
      ratings: { usefulness: 4, depth: 4, originality: 4, recency: 4, completeness: 4 },
      overallScore: 4, tldr: 'x', takeaways: ['y'],
    });
    const deps = makeDeps({ resolveTranscriptSegments, generateSummary });
    await summaryCore(baseInput, deps, { signal: controller.signal });

    expect(resolveTranscriptSegments).toHaveBeenCalledWith(
      'vid', baseInput.youtubeUrl, 90, { signal: controller.signal },
    );
    expect(generateSummary).toHaveBeenCalledWith(
      segments, 'en', 'vid', { signal: controller.signal },
    );
  });
});
