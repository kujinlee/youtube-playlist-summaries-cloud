jest.mock('@/lib/gemini');

import { applyCorrection } from '@/lib/corrections/apply-core';
import { StructuralValidationError } from '@/lib/corrections/structural-validation';
import * as gemini from '@/lib/gemini';

const mockFixSummary = jest.mocked(gemini.fixSummary);
const mockExtractQuickView = jest.mocked(gemini.extractQuickView);

// The real document shape (lib/ingestion/summary-core.ts:101-116), matching the structural-validation
// suite: tags list, QUOTED video_id, uppercase lang, score. The plan's draft used the older
// three-line frontmatter; the parser tolerates it, which is exactly why it is the wrong fixture —
// a green suite against a document this pipeline never produces proves nothing about this pipeline.
const BODY = `---
tags:
  - video-summary
  - en
video_id: "abc12345678"
lang: EN
score: 4.2
---

# A Title

**Channel:** Ch | **Duration:** 10:00 | **URL:** https://www.youtube.com/watch?v=abc12345678

---

## 1. Intro

▶ [0:00–5:00](https://www.youtube.com/watch?v=abc12345678&t=0s)

Clawcode is great.
`;

const CORRECTED = BODY.replace('Clawcode', 'Claude Code');

beforeEach(() => {
  jest.clearAllMocks();
  mockFixSummary.mockResolvedValue({ text: CORRECTED, usage: null });
  mockExtractQuickView.mockResolvedValue({ tldr: 'New TL;DR.', takeaways: ['New point'] });
});

describe('applyCorrection', () => {
  it('returns the corrected body with a re-inserted callout', async () => {
    const r = await applyCorrection({
      md: BODY, corrections: 'Clawcode -> Claude Code', tags: ['ai'],
      signal: new AbortController().signal,
    });
    expect(r.content).toContain('Claude Code');
    expect(r.content).toContain('> [!summary] Quick Reference');
    expect(r.content).toContain('> **TL;DR:** New TL;DR.');
    expect(r.tldr).toBe('New TL;DR.');
    expect(r.takeaways).toEqual(['New point']);
  });

  it('passes the CALLOUT-STRIPPED body to fixSummary, not the raw body', async () => {
    const withCallout = BODY.replace(
      '\n\n---\n\n## 1. Intro',
      '\n\n> [!summary] Quick Reference\n> **TL;DR:** Old.\n\n---\n\n## 1. Intro',
    );
    // The fixture must actually differ from BODY, or this asserts nothing.
    expect(withCallout).toContain('Quick Reference');
    await applyCorrection({
      md: withCallout, corrections: 'x', tags: [], signal: new AbortController().signal,
    });
    expect(mockFixSummary.mock.calls[0][0]).not.toContain('Quick Reference');
  });

  it('renders the Concepts line from tags', async () => {
    const r = await applyCorrection({
      md: BODY, corrections: 'x', tags: ['ai', 'rag'], signal: new AbortController().signal,
    });
    expect(r.content).toContain('> **Concepts:** ai · rag');
  });

  it('throws StructuralValidationError and never calls extractQuickView when structure moved', async () => {
    mockFixSummary.mockResolvedValue({ text: BODY.replace('## 1. Intro', '## 1. Introduction'), usage: null });
    await expect(applyCorrection({
      md: BODY, corrections: 'x', tags: [], signal: new AbortController().signal,
    })).rejects.toThrow(expect.objectContaining({ reason: 'section-title' }));
    expect(mockExtractQuickView).not.toHaveBeenCalled();
  });

  it('surfaces StructuralValidationError as its own class', async () => {
    mockFixSummary.mockResolvedValue({ text: BODY.replace('## 1. Intro', '## 1. Introduction'), usage: null });
    await expect(applyCorrection({
      md: BODY, corrections: 'x', tags: [], signal: new AbortController().signal,
    })).rejects.toBeInstanceOf(StructuralValidationError);
  });
});

describe('actual spend is measured, not estimated', () => {
  it('prices the real token counts', async () => {
    mockFixSummary.mockResolvedValue({
      text: CORRECTED,
      usage: { promptTokens: 10_000, outputTokens: 4_000 },
    });
    const r = await applyCorrection({
      md: BODY, corrections: 'x', tags: [], signal: new AbortController().signal,
    });
    // 10_000 * 30/1e6 + 4_000 * 250/1e6 = 0.3 + 1.0 = 1.3¢ → ceil 2
    expect(r.actualCents).toBe(2);
  });

  it('reports null rather than zero when the SDK returned no usageMetadata', async () => {
    mockFixSummary.mockResolvedValue({ text: CORRECTED, usage: null });
    const r = await applyCorrection({
      md: BODY, corrections: 'x', tags: [], signal: new AbortController().signal,
    });
    expect(r.actualCents).toBeNull();
  });
});
