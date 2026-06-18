# Versioned HTML-Doc Regeneration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** One unified "HTML doc" action that brings a video's doc to the current `major.minor` version — re-summarizing (to gain `▶` timestamps) or re-rendering (style-only) as needed — so existing summaries get onboarded to timestamps on demand.

**Architecture:** A shared `DocVersion` (`{major,minor}`, current `{2,0}`) stored per video. `writeSummaryDoc` is extracted from `runIngestion` (single source of truth, no PDF). `ensureHtmlDoc` reads the stored version and does the minimum: major-stale → re-summarize + full HTML rebuild; minor-stale/no-HTML → re-render from cached model (or full build); current → nothing. The existing SSE `html-doc` route drives it; the menu collapses to one version-aware item with a per-row hourglass while busy.

**Tech Stack:** Next.js/TypeScript, Zod, Jest + ts-jest (SWC transform → `tsc --noEmit` is the real typecheck), @testing-library/react, Playwright. Gemini/YouTube mocked at the lib boundary.

**Scope:** Phase 1 (per-video). Bulk sweep is Phase 2 (deferred).

---

### Task 1: `DocVersion` core + index field

**Files:**
- Create: `lib/doc-version.ts`
- Modify: `types/index.ts` (add `DocVersionSchema`; add `docVersion` to `VideoSchema:41-69`)
- Test: `tests/lib/doc-version.test.ts`

- [ ] **Step 1: Write the failing test** — create `tests/lib/doc-version.test.ts`:

```ts
import { CURRENT_DOC_VERSION, isOlder, needsResummarize } from '../../lib/doc-version';

describe('doc-version', () => {
  it('CURRENT_DOC_VERSION is 2.0 (timestamps = first major bump)', () => {
    expect(CURRENT_DOC_VERSION).toEqual({ major: 2, minor: 0 });
  });
  it('isOlder compares major then minor', () => {
    expect(isOlder({ major: 1, minor: 0 }, { major: 2, minor: 0 })).toBe(true);   // pre-feature
    expect(isOlder({ major: 2, minor: 0 }, { major: 2, minor: 1 })).toBe(true);   // style bump
    expect(isOlder({ major: 2, minor: 0 }, { major: 2, minor: 0 })).toBe(false);  // current
    expect(isOlder({ major: 3, minor: 0 }, { major: 2, minor: 9 })).toBe(false);  // newer
  });
  it('needsResummarize is true only when the major advanced', () => {
    expect(needsResummarize({ major: 1, minor: 0 }, { major: 2, minor: 0 })).toBe(true);
    expect(needsResummarize({ major: 2, minor: 0 }, { major: 2, minor: 5 })).toBe(false); // minor only
    expect(needsResummarize({ major: 2, minor: 0 }, { major: 2, minor: 0 })).toBe(false);
  });
});
```

- [ ] **Step 2: Run — expect FAIL** `npx jest doc-version` → "Cannot find module '../../lib/doc-version'".

- [ ] **Step 3: Implement** — create `lib/doc-version.ts`:

```ts
/** Document output version. MAJOR = summary/.md format (bump ⇒ re-summarize). MINOR = HTML render/style (bump ⇒ re-render). */
export interface DocVersion {
  major: number;
  minor: number;
}

/** The version current code produces. major 2 = ▶ timestamps (the first major bump). Bump minor for style/template-only changes. */
export const CURRENT_DOC_VERSION: DocVersion = { major: 2, minor: 0 };

/** True when `a` is an older doc version than `b` (major dominates, then minor). */
export function isOlder(a: DocVersion, b: DocVersion): boolean {
  return a.major < b.major || (a.major === b.major && a.minor < b.minor);
}

/** True when reaching `current` from `stored` requires regenerating the .md (a summary-format / major advance). */
export function needsResummarize(stored: DocVersion, current: DocVersion): boolean {
  return stored.major < current.major;
}
```

- [ ] **Step 4: Add the schema + index field** in `types/index.ts`. Immediately before `export const VideoSchema` (line 41) add:

```ts
export const DocVersionSchema = z.object({
  major: z.number().int().nonnegative(),
  minor: z.number().int().nonnegative(),
});
```

Inside `VideoSchema`, after the `corrections` line (line 68), add:

```ts
  docVersion: DocVersionSchema.optional(), // absent ⇒ pre-feature {1,0}; stamped to CURRENT_DOC_VERSION on (re)generation
```

- [ ] **Step 5: Run — expect PASS** `npx jest doc-version` → green. Then `npx tsc --noEmit` → only the 2 pre-existing `theme.test.ts` errors (the structural `{major,minor}` of `DocVersion` and `z.infer<DocVersionSchema>` match).

- [ ] **Step 6: Commit**

```bash
git add lib/doc-version.ts types/index.ts tests/lib/doc-version.test.ts
git commit -m "feat(docversion): DocVersion core + Video.docVersion field"
```

---

### Task 2: Extract `writeSummaryDoc` (no PDF) from `runIngestion`

**Files:**
- Modify: `lib/pipeline.ts` (extract function; rewire loop at `244-334`; stamp `docVersion`)
- Test: `tests/lib/pipeline.test.ts` (writeSummaryDoc unit + ingestion regression)

The per-video summary work moves into a reusable function. **Ingestion output stays byte-identical**; only the code location moves, plus it now stamps `docVersion` on the new `Video`.

- [ ] **Step 1: Write the failing test** — append to `tests/lib/pipeline.test.ts` (it already `jest.mock`s `../../lib/youtube`, `../../lib/gemini`, `../../lib/pdf`):

```ts
import { writeSummaryDoc } from '../../lib/pipeline';
import * as fsReal from 'fs';

describe('writeSummaryDoc', () => {
  it('writes <baseName>.md with the generated summary and returns AI fields; writes NO pdf', async () => {
    mockFetchTranscriptSegments.mockResolvedValue([{ text: 'hello world', offset: 0, duration: 5 }]);
    mockDetectLanguage.mockReturnValue('en');
    mockGenerateSummary.mockResolvedValue(makeSummaryResponse({ summary: '## 1. A\n▶ [0:00–0:05](u)\nbody' }));

    const result = await writeSummaryDoc({
      videoId: 'vid11111111', title: 'T', youtubeUrl: 'https://youtu.be/x',
      channel: 'Chan', durationSeconds: 5, outputFolder, baseName: 'my-base',
    });

    expect(result.summaryMd).toBe('my-base.md');
    expect(result.language).toBe('en');
    expect(result.ratings).toBeDefined();
    const md = fsReal.readFileSync(`${outputFolder}/my-base.md`, 'utf-8');
    expect(md).toContain('# T');
    expect(md).toContain('## 1. A');
    expect(md).toContain('▶ [0:00–0:05]');
    expect(mockGeneratePdf).not.toHaveBeenCalled(); // PDF is the caller's job now
    expect(mockGenerateSummary).toHaveBeenCalledWith(
      [{ text: 'hello world', offset: 0, duration: 5 }], 'en', 'vid11111111',
    );
  });
});
```

(If `makeSummaryResponse` doesn't accept an override arg, extend it to shallow-merge `{...base, ...override}`.)

- [ ] **Step 2: Run — expect FAIL** `npx jest pipeline.test -t writeSummaryDoc` → `writeSummaryDoc is not a function`.

- [ ] **Step 3: Implement** in `lib/pipeline.ts`. Add the input/result interfaces and the function (near the top, after imports):

```ts
import { CURRENT_DOC_VERSION } from './doc-version';

export interface SummaryDocInput {
  videoId: string;
  title: string;
  youtubeUrl: string;
  channel?: string;
  durationSeconds: number;
  outputFolder: string;
  baseName: string;
}
export interface SummaryDocResult {
  language: 'en' | 'ko';
  ratings: GeminiSummaryResponse['ratings'];
  overallScore: number;
  videoType?: GeminiSummaryResponse['videoType'];
  audience?: GeminiSummaryResponse['audience'];
  tags?: string[];
  tldr?: string;
  takeaways?: string[];
  mdContent: string;
  summaryMd: string;
}

/**
 * Fetch transcript → generateSummary (emits ▶ timestamps) → build the summary .md → write it at
 * <baseName>.md. Shared by ingestion (new slug) and re-summarize (existing baseName). Does NOT write
 * the PDF — the caller owns that (ingestion keeps generating PDFs; re-summarize skips them).
 */
export async function writeSummaryDoc(input: SummaryDocInput): Promise<SummaryDocResult> {
  const { videoId, title, youtubeUrl, channel, durationSeconds, outputFolder, baseName } = input;
  const segments = await fetchTranscriptSegments(videoId);
  const transcript = segments.map((s) => s.text).join(' '); // plain text for language detection only
  const language = detectLanguage(transcript);
  const { summary, ratings, overallScore, videoType, audience, tags, tldr, takeaways } =
    await generateSummary(segments, language, videoId);

  const structuralTags = ['video-summary', language];
  const allTags = [...structuralTags, ...(tags ?? [])];
  const frontmatterLines = [
    '---', 'tags:', ...allTags.map((t) => `  - ${t}`),
    `video_id: "${videoId}"`,
    ...(channel ? [`channel: "${channel}"`] : []),
    `lang: ${language.toUpperCase()}`,
    ...(videoType ? [`type: ${videoType}`] : []),
    ...(audience ? [`audience: ${audience}`] : []),
    `score: ${overallScore}`, '---',
  ];
  const metaParts = [
    channel && `**Channel:** ${channel}`,
    `**Duration:** ${formatDuration(durationSeconds)}`,
    `**URL:** ${youtubeUrl}`,
  ].filter(Boolean).join(' | ');
  const baseContent = [frontmatterLines.join('\n'), '', `# ${title}`, '', metaParts, '', '---', '', summary].join('\n');
  const mdContent = (tldr && takeaways)
    ? insertQuickViewCallout(baseContent, tldr, takeaways, tags ?? [])
    : baseContent;

  await fs.promises.writeFile(path.join(outputFolder, `${baseName}.md`), mdContent, 'utf-8');
  return { language, ratings, overallScore, videoType, audience, tags, tldr, takeaways, mdContent, summaryMd: `${baseName}.md` };
}
```

Now rewire the `runIngestion` loop (`244-334`) to delegate. Replace the block from the "Fetching transcript…" progress event through the `await fs.promises.writeFile(mdPath, mdContent, 'utf-8');` line with:

```ts
      onProgress({ type: 'step', videoId: meta.videoId, title: meta.title, step: 'Fetching transcript…', current, total });
      const slug = slugify(meta.title);
      let baseName = slug;
      let counter = 2;
      while (fs.existsSync(path.join(outputFolder, `${baseName}.md`))) {
        baseName = `${slug}-${counter}`;
        counter++;
      }
      onProgress({ type: 'step', videoId: meta.videoId, title: meta.title, step: 'Generating summary…', current, total });
      const { language, ratings, overallScore, videoType, audience, tags, tldr, takeaways, mdContent } =
        await writeSummaryDoc({
          videoId: meta.videoId, title: meta.title, youtubeUrl: meta.youtubeUrl,
          channel: meta.channelTitle, durationSeconds: meta.durationSeconds, outputFolder, baseName,
        });
      fs.mkdirSync(path.join(outputFolder, 'pdfs'), { recursive: true });
      const pdfPath = path.join(outputFolder, 'pdfs', `${baseName}.pdf`);
```

Then in the `const video: Video = { … }` object (still in the loop), add `docVersion: CURRENT_DOC_VERSION,` (e.g. right after `processedAt`). The existing `generatePdf(mdContent, pdfPath)` call below stays. Remove the now-duplicated frontmatter/metaParts/baseContent/mdContent/mdPath lines that `writeSummaryDoc` replaced.

- [ ] **Step 4: Run — expect PASS** `npx jest pipeline.test` → green (writeSummaryDoc test + all existing ingestion tests still pass — byte-identical output). Then `npx tsc --noEmit` (only the 2 known errors).

- [ ] **Step 5: Commit**

```bash
git add lib/pipeline.ts tests/lib/pipeline.test.ts
git commit -m "refactor(pipeline): extract writeSummaryDoc (no PDF); stamp docVersion on ingest"
```

---

### Task 3: `ensureHtmlDoc` — the version-driven orchestrator

**Files:**
- Create: `lib/html-doc/ensure.ts`
- Test: `tests/lib/html-doc/ensure.test.ts`

`ensureHtmlDoc` does the minimum work to bring a video to `CURRENT_DOC_VERSION`, then leaves `summaryHtml` + `docVersion` current.

- [ ] **Step 1: Write the failing test** — create `tests/lib/html-doc/ensure.test.ts`. Mock the collaborators:

```ts
import { ensureHtmlDoc } from '../../../lib/html-doc/ensure';
import * as pipeline from '../../../lib/pipeline';
import * as generate from '../../../lib/html-doc/generate';
import * as rerender from '../../../lib/html-doc/rerender';
import * as indexStore from '../../../lib/index-store';

jest.mock('../../../lib/pipeline');
jest.mock('../../../lib/html-doc/generate');
jest.mock('../../../lib/html-doc/rerender');
jest.mock('../../../lib/index-store');

const videoBase = {
  id: 'vid11111111', title: 'T', youtubeUrl: 'https://youtu.be/x', language: 'en' as const,
  durationSeconds: 5, archived: false, ratings: { usefulness: 3, depth: 3, originality: 3, recency: 3, completeness: 3 },
  overallScore: 3, summaryMd: 'base.md', summaryPdf: 'pdfs/base.pdf', deepDiveMd: null, deepDivePdf: null,
  processedAt: '2026-01-01T00:00:00.000Z', personalScore: 5,
};

beforeEach(() => {
  jest.clearAllMocks();
  (indexStore.assertOutputFolder as jest.Mock).mockReturnValue(undefined);
  (indexStore.assertVideoId as jest.Mock).mockReturnValue(undefined);
  (generate.runHtmlDoc as jest.Mock).mockResolvedValue(undefined);
  (pipeline.writeSummaryDoc as jest.Mock).mockResolvedValue({
    language: 'en', ratings: videoBase.ratings, overallScore: 4, tags: ['t'], summaryMd: 'base.md', mdContent: '#',
  });
});
function withVideo(v: object) {
  (indexStore.readIndex as jest.Mock).mockReturnValue({ videos: [{ ...videoBase, ...v }] });
}

describe('ensureHtmlDoc', () => {
  it('pre-feature (no docVersion) → re-summarizes, rebuilds, preserves personalScore, stamps current', async () => {
    withVideo({ docVersion: undefined, summaryHtml: 'htmls/base.html' });
    await ensureHtmlDoc('vid11111111', '/out', () => {});
    expect(pipeline.writeSummaryDoc).toHaveBeenCalledWith(expect.objectContaining({ baseName: 'base' }));
    expect(generate.runHtmlDoc).toHaveBeenCalled();          // full rebuild after re-summarize
    expect(rerender.reRenderSummaryHtml).not.toHaveBeenCalled();
    const patches = (indexStore.updateVideoFields as jest.Mock).mock.calls.map((c) => c[2]);
    expect(patches).toEqual(expect.arrayContaining([expect.objectContaining({ overallScore: 4 })]));         // AI fields merged
    expect(patches).toEqual(expect.arrayContaining([expect.objectContaining({ docVersion: { major: 2, minor: 0 } })])); // stamped
    expect(patches.every((p) => !('personalScore' in p))).toBe(true); // never overwrites personal review
  });

  it('current major but no HTML → full generate (no re-summarize), stamp', async () => {
    withVideo({ docVersion: { major: 2, minor: 0 }, summaryHtml: null });
    await ensureHtmlDoc('vid11111111', '/out', () => {});
    expect(pipeline.writeSummaryDoc).not.toHaveBeenCalled();
    expect(generate.runHtmlDoc).toHaveBeenCalled();
  });

  it('minor-stale with cached model → cheap re-render (no Gemini), stamp', async () => {
    withVideo({ docVersion: { major: 2, minor: 0 }, summaryHtml: 'htmls/base.html' });
    // CURRENT minor is 0 today, so simulate a minor bump by spying: treat stored {2,0} as older than {2,1}
    // (this test pins the branch; if CURRENT minor is 0 it falls to the no-op case below instead).
    (rerender.reRenderSummaryHtml as jest.Mock).mockReturnValue({ status: 'rerendered', htmlPath: 'htmls/base.html' });
    // Force minor-stale by stubbing isOlder via a stored version behind current:
    await ensureHtmlDoc('vid11111111', '/out', () => {}, { major: 2, minor: 1 } /* test-injected current */);
    expect(pipeline.writeSummaryDoc).not.toHaveBeenCalled();
    expect(rerender.reRenderSummaryHtml).toHaveBeenCalled();
    expect(generate.runHtmlDoc).not.toHaveBeenCalled();
  });

  it('current + HTML present → no work', async () => {
    withVideo({ docVersion: { major: 2, minor: 0 }, summaryHtml: 'htmls/base.html' });
    await ensureHtmlDoc('vid11111111', '/out', () => {});
    expect(pipeline.writeSummaryDoc).not.toHaveBeenCalled();
    expect(generate.runHtmlDoc).not.toHaveBeenCalled();
    expect(rerender.reRenderSummaryHtml).not.toHaveBeenCalled();
  });

  it('throws 422-style error when the video has no summaryMd', async () => {
    withVideo({ summaryMd: null });
    await expect(ensureHtmlDoc('vid11111111', '/out', () => {})).rejects.toThrow(/no summary/i);
  });
});
```

- [ ] **Step 2: Run — expect FAIL** `npx jest html-doc/ensure` → module not found.

- [ ] **Step 3: Implement** — create `lib/html-doc/ensure.ts`:

```ts
import fs from 'fs';
import path from 'path';
import { assertOutputFolder, assertVideoId, readIndex, updateVideoFields } from '../index-store';
import { writeSummaryDoc } from '../pipeline';
import { runHtmlDoc } from './generate';
import { reRenderSummaryHtml } from './rerender';
import { CURRENT_DOC_VERSION, isOlder, needsResummarize, type DocVersion } from '../doc-version';
import type { ProgressEvent } from '../../types';

const PRE_FEATURE: DocVersion = { major: 1, minor: 0 };

/**
 * Bring a video's summary HTML to `current` (default CURRENT_DOC_VERSION), doing the minimum work:
 * major-stale → re-summarize (.md, Gemini) + full HTML rebuild; minor-stale with a cached model →
 * cheap re-render; no HTML yet → full build; already current → nothing. Leaves summaryHtml + docVersion
 * current. `current` is injectable for tests. Throws if the video lacks a source note.
 */
export async function ensureHtmlDoc(
  videoId: string,
  outputFolder: string,
  onProgress: (e: ProgressEvent) => void,
  current: DocVersion = CURRENT_DOC_VERSION,
): Promise<void> {
  assertOutputFolder(outputFolder);
  assertVideoId(videoId);

  const video = readIndex(outputFolder).videos.find((v) => v.id === videoId);
  if (!video) throw new Error(`Video not found in index: ${videoId}`);
  if (!video.summaryMd) throw new Error('no summary note for this video');

  const stored: DocVersion = video.docVersion ?? PRE_FEATURE;
  const base = video.summaryMd.replace(/\.md$/, '');
  onProgress({ type: 'start' });

  if (needsResummarize(stored, current)) {
    onProgress({ type: 'step', videoId, step: 'Re-summarizing (adding timestamps)…', current: 1, total: 2 });
    const r = await writeSummaryDoc({
      videoId: video.id, title: video.title, youtubeUrl: video.youtubeUrl,
      channel: video.channel, durationSeconds: video.durationSeconds, outputFolder, baseName: base,
    });
    // Merge ONLY summary-derived AI fields; never touch personal review / deep-dive / playlist position.
    updateVideoFields(outputFolder, videoId, {
      language: r.language, ratings: r.ratings, overallScore: r.overallScore,
      videoType: r.videoType, audience: r.audience, tags: r.tags, tldr: r.tldr, takeaways: r.takeaways,
    });
    // The .md sections changed → the cached magazine model is stale; drop it so the rebuild regenerates it.
    try { fs.unlinkSync(path.join(outputFolder, 'models', `${base}.json`)); } catch { /* no model — fine */ }
    onProgress({ type: 'step', videoId, step: 'Building HTML…', current: 2, total: 2 });
    await runHtmlDoc(videoId, outputFolder, onProgress);
  } else if (!video.summaryHtml) {
    onProgress({ type: 'step', videoId, step: 'Building HTML…', current: 1, total: 1 });
    await runHtmlDoc(videoId, outputFolder, onProgress);
  } else if (isOlder(stored, current)) {
    onProgress({ type: 'step', videoId, step: 'Re-rendering HTML…', current: 1, total: 1 });
    const rr = reRenderSummaryHtml(videoId, outputFolder);
    if (rr.status !== 'rerendered') await runHtmlDoc(videoId, outputFolder, onProgress); // no model / drift → full build
  } else {
    onProgress({ type: 'done' });
    return; // already current with HTML — nothing to do
  }

  updateVideoFields(outputFolder, videoId, { docVersion: current });
  onProgress({ type: 'done' });
}
```

- [ ] **Step 4: Run — expect PASS** `npx jest html-doc/ensure` → green. `npx tsc --noEmit` (only the 2 known errors).

- [ ] **Step 5: Commit**

```bash
git add lib/html-doc/ensure.ts tests/lib/html-doc/ensure.test.ts
git commit -m "feat(html-doc): ensureHtmlDoc — version-driven re-summarize/re-render/build"
```

---

### Task 4: Route the unified action through `ensureHtmlDoc`

**Files:**
- Modify: `app/api/videos/[id]/html-doc/route.ts` (swap `runHtmlDoc` → `ensureHtmlDoc`)
- Test: `tests/lib/job-registry-html.test.ts` (existing html-doc route/job test — extend if present) or a new route test

The existing POST route already `createJob` + runs an orchestrator with `onProgress` → job events → SSE. Only the orchestrator call changes.

- [ ] **Step 1: Write/extend the test.** In the existing html-doc route test (or create `tests/app/html-doc-route.test.ts`), mock `lib/html-doc/ensure` and assert the route invokes `ensureHtmlDoc(videoId, outputFolder, <progress fn>)` and emits its events. Minimal new assertion:

```ts
jest.mock('../../lib/html-doc/ensure');
// … POST the route with { outputFolder } …
expect(ensureHtmlDoc).toHaveBeenCalledWith('vid11111111', outputFolder, expect.any(Function));
```

- [ ] **Step 2: Run — expect FAIL** (route still calls `runHtmlDoc`).

- [ ] **Step 3: Implement.** In `app/api/videos/[id]/html-doc/route.ts`, change the import `import { runHtmlDoc } from '../../../../../lib/html-doc/generate';` to `import { ensureHtmlDoc } from '../../../../../lib/html-doc/ensure';` and change the call `runHtmlDoc(videoId, outputFolder, (event) => {…})` to `ensureHtmlDoc(videoId, outputFolder, (event) => {…})`. Leave the job-registry/SSE wiring untouched.

- [ ] **Step 4: Run — expect PASS** `npx jest html-doc-route` (and the existing html-doc route/job tests). `npx tsc --noEmit`.

- [ ] **Step 5: Commit**

```bash
git add app/api/videos/\[id\]/html-doc/route.ts tests/
git commit -m "feat(api): html-doc route drives ensureHtmlDoc (version-aware)"
```

---

### Task 5: Corrections invalidates the cached HTML

**Files:**
- Modify: `app/api/videos/[id]/regenerate/route.ts`
- Test: `tests/lib/regenerate-route.test.ts` (or the existing corrections/regenerate test)

After "Edit corrections" rewrites the `.md`, the cached HTML is stale but the version is unchanged; clear `summaryHtml` so the unified action rebuilds it on next click.

- [ ] **Step 1: Write the failing test** — after a successful corrections POST, assert the index update includes `summaryHtml: null`:

```ts
// mock index-store.updateVideoFields; POST corrections; then:
expect(updateVideoFields).toHaveBeenCalledWith(outputFolder, videoId, expect.objectContaining({ summaryHtml: null }));
```

- [ ] **Step 2: Run — expect FAIL.**

- [ ] **Step 3: Implement.** In `regenerate/route.ts`, after the `await fs.promises.writeFile(mdPath, updatedContent, 'utf-8');` line, extend the existing index update so the refreshed-quick-view `updateVideoFields(outputFolder, videoId, { tldr, takeaways })` also clears the stale HTML:

```ts
    updateVideoFields(outputFolder, videoId, { tldr, takeaways, summaryHtml: null });
```

- [ ] **Step 4: Run — expect PASS** `npx jest regenerate`. `npx tsc --noEmit`.

- [ ] **Step 5: Commit**

```bash
git add app/api/videos/\[id\]/regenerate/route.ts tests/
git commit -m "fix(api): clear stale summaryHtml after corrections rewrite the .md"
```

---

### Task 6: Collapse the menu into one version-aware "HTML doc" item

**Files:**
- Modify: `components/VideoMenu.tsx`
- Test: `tests/components/VideoMenu.test.tsx` (create if absent)

Replace the three items (`View HTML doc` link, `Generate HTML doc` button, `Regenerate HTML doc` button) with **one** "HTML doc" item: a direct link when current, a button otherwise, disabled while busy or without a summary.

- [ ] **Step 1: Write the failing test** — `tests/components/VideoMenu.test.tsx`:

```tsx
import { render, screen } from '@testing-library/react';
import VideoMenu from '../../components/VideoMenu';

const base = {
  id: 'vid11111111', title: 'T', youtubeUrl: 'https://youtu.be/x', language: 'en',
  durationSeconds: 5, archived: false, ratings: { usefulness: 3, depth: 3, originality: 3, recency: 3, completeness: 3 },
  overallScore: 3, summaryMd: 'base.md', summaryPdf: null, deepDiveMd: null, deepDivePdf: null, processedAt: '2026-01-01T00:00:00.000Z',
};
const props = { outputFolder: '/o', baseOutputFolder: '/o', onDeepDive() {}, onArchive() {}, onEditCorrections() {}, onGenerateHtml() {}, onClose() {}, busy: false };

it('shows a single "HTML doc" item — a direct link when current (html + docVersion 2.0)', () => {
  render(<VideoMenu {...props} video={{ ...base, summaryHtml: 'htmls/base.html', docVersion: { major: 2, minor: 0 } } as any} />);
  const el = screen.getByRole('link', { name: /HTML doc/i });
  expect(el).toHaveAttribute('href', expect.stringContaining('/api/html/'));
  expect(screen.queryByText(/Generate HTML doc|Regenerate HTML doc|View HTML doc/)).toBeNull();
});

it('renders a button when stale (pre-feature: no docVersion)', () => {
  render(<VideoMenu {...props} video={{ ...base, summaryHtml: 'htmls/base.html' } as any} />);
  expect(screen.getByRole('button', { name: /HTML doc/i })).toBeInTheDocument();
});

it('disables the item while busy', () => {
  render(<VideoMenu {...props} busy video={{ ...base, summaryHtml: 'htmls/base.html', docVersion: { major: 2, minor: 0 } } as any} />);
  expect(screen.getByText(/HTML doc/i).closest('a,button,span')).toHaveAttribute('aria-disabled', 'true');
});
```

- [ ] **Step 2: Run — expect FAIL** `npx jest VideoMenu`.

- [ ] **Step 3: Implement.** In `components/VideoMenu.tsx`: add imports `import { CURRENT_DOC_VERSION, isOlder } from '@/lib/doc-version';`. Add `busy?: boolean` to `VideoMenuProps`. Replace the three `<li>`s for the HTML-doc items (the `hasSummaryHtml ? View : hasSummary ? Generate : disabled` block **and** the separate `Regenerate HTML doc` block, currently lines 86-105) with a single item:

```tsx
      <li role="none">
        {(() => {
          const current = !!video.summaryHtml && !isOlder(video.docVersion ?? { major: 1, minor: 0 }, CURRENT_DOC_VERSION);
          if (!hasSummary) return <span aria-disabled="true" className={disabledClass}>HTML doc</span>;
          if (busy) return <span aria-disabled="true" className={disabledClass}>HTML doc <span aria-hidden="true">⏳</span></span>;
          return current
            ? <a href={htmlViewHref} onClick={onClose} target="_blank" rel="noopener noreferrer" className={itemClass}>HTML doc</a>
            : <button type="button" onClick={() => { onGenerateHtml(video.id); onClose(); }} className={itemClass}>HTML doc</button>;
        })()}
      </li>
```

Pass `busy` through from `VideoMenu`'s props (destructure it in the function signature). Keep the deep-dive HTML, Obsidian, PDF, corrections, archive items unchanged.

- [ ] **Step 4: Run — expect PASS** `npx jest VideoMenu`. `npx tsc --noEmit`.

- [ ] **Step 5: Commit**

```bash
git add components/VideoMenu.tsx tests/components/VideoMenu.test.tsx
git commit -m "feat(ui): single version-aware 'HTML doc' menu item"
```

---

### Task 7: Per-row hourglass + busy threading

**Files:**
- Modify: `components/VideoRow.tsx`, `components/VideoList.tsx`, `app/page.tsx`
- Test: `tests/components/VideoRow.test.tsx` (busy indicator)

While a row is regenerating (`htmlJob.videoId === video.id`), show an hourglass next to the ☰ trigger and mark the menu item busy. On completion the existing `handleHtmlClose` refetches videos → `docVersion` current → item becomes a direct link.

- [ ] **Step 1: Write the failing test** — `tests/components/VideoRow.test.tsx` renders a `<table><tbody>` wrapper with `<VideoRow busy ... />` and asserts an hourglass with `aria-label="Regenerating"` is present next to the menu; and `<VideoRow ...>` (not busy) has none. (Render inside a `table`/`tbody` to satisfy `<tr>`.)

```tsx
it('shows an hourglass next to the menu while busy', () => {
  render(<table><tbody><VideoRow {...rowProps} busy /></tbody></table>);
  expect(screen.getByLabelText('Regenerating')).toBeInTheDocument();
});
it('no hourglass when not busy', () => {
  render(<table><tbody><VideoRow {...rowProps} /></tbody></table>);
  expect(screen.queryByLabelText('Regenerating')).toBeNull();
});
```

- [ ] **Step 2: Run — expect FAIL.**

- [ ] **Step 3: Implement.**

`components/VideoRow.tsx`: add `busy?: boolean;` to `VideoRowProps`; destructure `busy` (default `false`). Next to the `☰` menu button (after it, inside the same flex container at lines 92-101) add:

```tsx
            {busy && <span role="status" aria-label="Regenerating" title="Regenerating…" className="shrink-0 text-amber-400 animate-pulse">⏳</span>}
```

Pass `busy={busy}` into `<VideoMenu … />`.

`components/VideoList.tsx`: add `busyVideoId?: string | null;` to `VideoListProps`; destructure it; pass `busy={busyVideoId === video.id}` to each `<VideoRow … />`.

`app/page.tsx`: pass `busyVideoId={htmlJob?.videoId ?? null}` to `<VideoList … />`. (`htmlJob` already exists; `handleHtmlClose` already refetches videos so the row updates to current on completion.)

- [ ] **Step 4: Run — expect PASS** `npx jest VideoRow`. `npx tsc --noEmit`.

- [ ] **Step 5: Full suite** `npm test` → all green (no regressions). `npx tsc --noEmit` → only the 2 pre-existing errors.

- [ ] **Step 6: Commit**

```bash
git add components/VideoRow.tsx components/VideoList.tsx app/page.tsx tests/components/VideoRow.test.tsx
git commit -m "feat(ui): per-row hourglass + busy threading for HTML doc regeneration"
```

---

## Self-Review

**Spec coverage**

| Spec | Task |
|---|---|
| §3 `DocVersion`, `CURRENT_DOC_VERSION`, `isOlder`, `needsResummarize`, per-video `docVersion` | Task 1 |
| §4 `writeSummaryDoc` extraction (no PDF), ingestion byte-identical + stamps version | Task 2 |
| §5 `ensureHtmlDoc` three branches + merge/preserve + model invalidation + non-destructive | Task 3 |
| §5 route drives `ensureHtmlDoc` | Task 4 |
| §7 corrections clears `summaryHtml` | Task 5 |
| D5/§7 single version-aware "HTML doc" item (link/button/disabled) | Task 6 |
| §7 per-row hourglass, busy disable, busy→clickable on refresh | Task 7 |
| D7 PDF untouched | Tasks 2 (no PDF in writeSummaryDoc) + 3 (re-summarize path never calls generatePdf) |
| D8 no confirm/overlay | (no task adds one) |
| §6 output format identical | Task 2 (same builder) |

No spec requirement is without a task. Phase-2 bulk is out of scope by D3.

**Placeholder scan:** every code step has complete code. Two prose directions remain — both reference concrete, already-read code: Task 2 "remove the now-duplicated frontmatter/… lines `writeSummaryDoc` replaced" (the exact lines are `pipeline.ts:264-302`), and Task 4's import/call swap (one line each).

**Type consistency:** `DocVersion {major,minor}` (Task 1) is used identically in Tasks 3/6; `writeSummaryDoc(SummaryDocInput with baseName)` (Task 2) is called with `baseName` in Tasks 2/3; `ensureHtmlDoc(videoId, outputFolder, onProgress, current?)` (Task 3) is called by Task 4; `busy` prop flows VideoMenu (Task 6) ← VideoRow ← VideoList ← page (Task 7); `updateVideoFields(outputFolder, videoId, patch)` matches the existing index-store signature.

## Verification (Phase 4 — after all tasks)

Against the running app: open a pre-feature video's "HTML doc" → hourglass shows → on completion the item becomes a link → opening it shows `▶` timestamps; the `.md` is overwritten with `▶` lines; the PDF file is unchanged (stale); personal score/note survive; a second click opens instantly (no regen). Enumerate these as a `TaskCreate` list before clicking (per dev-process Phase 4).
