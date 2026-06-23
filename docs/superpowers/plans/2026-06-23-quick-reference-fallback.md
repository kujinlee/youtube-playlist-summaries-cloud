# Quick Reference Fallback — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax.

**Goal:** `writeSummaryDoc` always emits the Quick Reference callout — when `generateSummary` omits `tldr`/`takeaways`, derive them via `extractQuickView`; graceful (no callout, no throw) if that also fails.

## Global Constraints
- `extractQuickView(baseContent)` (full md), matching `backfill`/`regenerate` consumers.
- `try` wraps ONLY the derive; `writeFile` stays outside (never skip the .md write).
- Discard the partial on throw (return `undefined` → keeps the doc backfill-eligible).
- Full `npm test` + `npx tsc --noEmit` green before commit.

---

### Task 1: Fallback to `extractQuickView` in `writeSummaryDoc`

**Files:**
- Modify: `lib/pipeline.ts` (import line 4; `writeSummaryDoc` ~68-72)
- Test: `tests/lib/pipeline.test.ts`

**Interfaces:** `writeSummaryDoc` signature/return shape unchanged (already returns `{tldr, takeaways, …}`).

- [ ] **Step 1: Blast-radius guard + new test scaffolding** in `tests/lib/pipeline.test.ts`.
  - Add the mock handle near the others: `const mockExtractQuickView = jest.mocked(gemini.extractQuickView);`
  - Add `tldr` + `takeaways` to `makeSummaryResponse()`'s default so existing tests stay on the both-present path:
    ```ts
    function makeSummaryResponse(overrides: Partial<GeminiSummaryResponse> = {}): GeminiSummaryResponse {
      return {
        summary: 'A great summary',
        ratings: { usefulness: 3, depth: 3, originality: 3, recency: 3, completeness: 3 },
        overallScore: 3,
        tldr: 'This video explains the topic.',
        takeaways: ['Point one', 'Point two'],
        ...overrides,
      };
    }
    ```
  - In the `runIngestion` `beforeEach`, add a defensive default: `mockExtractQuickView.mockResolvedValue({ tldr: 'QV tldr', takeaways: ['qa', 'qb'] });`

- [ ] **Step 2: Write the new failing tests** (a `describe('writeSummaryDoc — Quick Reference fallback', …)`; `writeSummaryDoc` is exported and imported in this file). Use a temp `outputFolder` (the file's `makeTempDir()`); stub transcript + detectLanguage as the suite does, or call `writeSummaryDoc` directly with mocked `lib/gemini`/`lib/youtube`.

```ts
describe('writeSummaryDoc — Quick Reference fallback', () => {
  let outputFolder: string;
  beforeEach(() => {
    outputFolder = makeTempDir();
    mockFetchTranscriptSegments.mockResolvedValue([{ text: 't', offset: 0, duration: 5 }]);
    mockDetectLanguage.mockReturnValue('en');
  });
  afterEach(() => { fs.rmSync(outputFolder, { recursive: true, force: true }); jest.clearAllMocks(); });

  const input = () => ({ videoId: 'vid1', title: 'T', youtubeUrl: 'https://y/watch?v=vid1', channel: 'C', durationSeconds: 300, outputFolder, baseName: 'doc' });
  const read = () => fs.readFileSync(path.join(outputFolder, 'doc.md'), 'utf-8');

  it('both present → no extractQuickView call, callout from generateSummary values', async () => {
    mockGenerateSummary.mockResolvedValue(makeSummaryResponse({ tldr: 'This video does X.', takeaways: ['a', 'b'] }));
    const r = await writeSummaryDoc(input());
    expect(mockExtractQuickView).not.toHaveBeenCalled();
    expect(read()).toContain('> **TL;DR:** This video does X.');
    expect(r.tldr).toBe('This video does X.');
  });

  it('neither present → extractQuickView(baseContent) fallback inserts callout', async () => {
    mockGenerateSummary.mockResolvedValue(makeSummaryResponse({ tldr: undefined, takeaways: undefined }));
    mockExtractQuickView.mockResolvedValue({ tldr: 'Derived tldr.', takeaways: ['d1', 'd2'] });
    const r = await writeSummaryDoc(input());
    expect(mockExtractQuickView).toHaveBeenCalledTimes(1);
    const arg = mockExtractQuickView.mock.calls[0][0];
    expect(arg).toContain('video_id: "vid1"'); // baseContent = full md (frontmatter present)
    expect(arg).toContain('# T');
    expect(read()).toContain('> **TL;DR:** Derived tldr.');
    expect(r.tldr).toBe('Derived tldr.');
    expect(r.takeaways).toEqual(['d1', 'd2']);
  });

  it('only tldr present → fallback derives both (partial discarded)', async () => {
    mockGenerateSummary.mockResolvedValue(makeSummaryResponse({ tldr: 'partial only', takeaways: undefined }));
    mockExtractQuickView.mockResolvedValue({ tldr: 'Derived.', takeaways: ['d1'] });
    const r = await writeSummaryDoc(input());
    expect(mockExtractQuickView).toHaveBeenCalledTimes(1);
    expect(read()).toContain('> **TL;DR:** Derived.');
    expect(r.tldr).toBe('Derived.'); // partial 'partial only' discarded
  });

  it('extractQuickView throws → graceful: md written without callout, no throw, undefined values', async () => {
    mockGenerateSummary.mockResolvedValue(makeSummaryResponse({ tldr: undefined, takeaways: undefined }));
    mockExtractQuickView.mockRejectedValue(new Error('qv failed'));
    const r = await writeSummaryDoc(input());
    expect(read()).not.toContain('> [!summary] Quick Reference');
    expect(read()).toContain('# T'); // file still written
    expect(r.tldr).toBeUndefined();
    expect(r.takeaways).toBeUndefined();
  });
});

it('ingestion persists DERIVED tldr/takeaways to the index when generateSummary omits them', async () => {
  mockReadIndex.mockReturnValue({ playlistUrl: PLAYLIST_URL, outputFolder, videos: [] });
  mockFetchPlaylistVideos.mockResolvedValue([makeVideoMeta('vid1')]);
  mockFetchTranscriptSegments.mockResolvedValue([{ text: 't', offset: 0, duration: 5 }]);
  mockGenerateSummary.mockResolvedValue(makeSummaryResponse({ tldr: undefined, takeaways: undefined }));
  mockExtractQuickView.mockResolvedValue({ tldr: 'Derived.', takeaways: ['d1', 'd2'] });
  await runIngestion(PLAYLIST_URL, outputFolder, () => {});
  expect(mockUpsertVideo).toHaveBeenCalledWith(
    outputFolder,
    expect.objectContaining({ id: 'vid1', tldr: 'Derived.', takeaways: ['d1', 'd2'] }),
  );
});
```
(Place the ingestion test inside the existing `describe('runIngestion', …)` block so it inherits its `beforeEach`/`outputFolder`.)

- [ ] **Step 3: Run — confirm RED** (`npx jest pipeline -t "Quick Reference fallback"` and the ingestion case). The fallback cases fail (current code writes no callout when tldr/takeaways absent and never calls extractQuickView).

- [ ] **Step 4: Implement.** In `lib/pipeline.ts`:
  - Line 4 import: `import { generateSummary, extractQuickView } from './gemini';`
  - Replace the `const mdContent = (tldr && takeaways) ? insertQuickViewCallout(...) : baseContent;` line and the `return {…}` (lines ~68-73) with the spec's control structure:

```ts
  let outTldr = tldr;
  let outTakeaways = takeaways;
  let mdContent: string;
  if (tldr && takeaways) {
    mdContent = insertQuickViewCallout(baseContent, tldr, takeaways, tags ?? []);
  } else {
    // generateSummary omitted tldr/takeaways → derive them from the full md so the Quick
    // Reference callout is never silently skipped (same primitive the backfill route uses).
    try {
      const qv = await extractQuickView(baseContent);
      outTldr = qv.tldr;
      outTakeaways = qv.takeaways;
      mdContent = insertQuickViewCallout(baseContent, qv.tldr, qv.takeaways, tags ?? []);
    } catch {
      // Extraction failed — write without the callout and clear the partial so the doc
      // stays eligible for the backfill route (filters on !v.tldr). Never fail the summary.
      mdContent = baseContent;
      outTldr = undefined;
      outTakeaways = undefined;
    }
  }

  await fs.promises.writeFile(path.join(outputFolder, `${baseName}.md`), mdContent, 'utf-8');
  return { language, ratings, overallScore, videoType, audience, tags, tldr: outTldr, takeaways: outTakeaways, mdContent, summaryMd: `${baseName}.md` };
```

- [ ] **Step 5: Run — GREEN** (`npx jest pipeline -t "Quick Reference fallback"` + the ingestion case).

- [ ] **Step 6: Full suite + types** — `npm test` then `npx tsc --noEmit`. Update any existing test that broke from the `makeSummaryResponse` default change (most use `toContain`; expected churn is small — fix by either asserting the now-present callout or overriding `tldr/takeaways: undefined` in that specific test if it must test the no-callout shape). All green.

- [ ] **Step 7: Commit** — `fix(pipeline): derive Quick Reference via extractQuickView when generateSummary omits tldr/takeaways`. `git commit -F -` quoted-EOF heredoc; end body with:
  ```
  Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_01LmbSdwfXunHoxGJxtb3zGc
  ```

## Post-implementation (migration — after merge)
Throwaway script (env sourced) over summaries whose `.md` lacks `> [!summary] Quick Reference`: read `.md` → `extractQuickView` → `insertQuickViewCallout` → write → `updateVideoFields({tldr, takeaways})`. Dry-run/print first (list eligible), then `--run`, then verify each now contains the callout.

## Self-review notes
- Spec coverage: import + control structure (Step 4) + 6 test cases (Steps 1-2) + blast-radius guard (Step 1). Type consistency: `outTldr/outTakeaways` typed `string | undefined` / `string[] | undefined` to match the return; `extractQuickView` returns `{tldr: string; takeaways: string[]}`.
