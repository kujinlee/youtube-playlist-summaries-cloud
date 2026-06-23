# Deep-Dive Transcript Fallback Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deep-dive docs get ▶ timestamps even when YouTube captions are gated, by sourcing the transcript through the captions→Gemini cascade instead of captions-only.

**Architecture:** Swap `fetchTranscriptSegments(videoId)` → `resolveTranscriptSegments(videoId, youtubeUrl, durationSeconds)` in `lib/deep-dive/write-doc.ts`, keeping the existing `try/catch` so a total failure still degrades to the video-only path. Tests move to the project's standard boundary (mock `lib/youtube` + `lib/gemini`, run the real resolver).

**Tech Stack:** TypeScript, Jest (SWC transform), `@google/generative-ai`.

## Global Constraints

- **Mock boundary:** tests mock `../../../lib/youtube` and `../../../lib/gemini` and run the **REAL** `resolveTranscriptSegments` (it's in `lib/transcript-source.ts`, which stays unmocked). Do NOT `jest.mock('../../../lib/transcript-source')`.
- **Graceful floor preserved:** when the resolver throws (captions AND Gemini both fail), `segments` stays `null` → existing video-only path runs. The ONLY remaining no-▶ case.
- **Cost:** net-new cost on a gated video = one `transcribeViaGemini` flash call; captioned videos (≥1 segment) make no extra call.
- **No version bump / no mass regen** in this branch (existing-doc repair is verification + an explicit user offer).
- **Gate:** `npx tsc --noEmit` clean AND full `npm test` green before commit. Dual review.

---

## File Structure

| File | Responsibility | Change |
|------|----------------|--------|
| `lib/deep-dive/write-doc.ts` | Source the transcript via the resolver (captions→Gemini) | Modify (import + ~line 42) |
| `tests/lib/deep-dive/write-doc.test.ts` | Cover the new fallback behavior at the youtube+gemini boundary | Modify |

---

## Task 1: Deep-dive sources transcript via the cascade resolver

**Files:**
- Modify: `lib/deep-dive/write-doc.ts` (import line 4; transcript fetch lines 41-43)
- Test: `tests/lib/deep-dive/write-doc.test.ts` (mock handles ~line 18; beforeEach line 57-63; tests at :70, :103, :116, :168, :180)

**Interfaces:**
- Consumes: `resolveTranscriptSegments(videoId: string, youtubeUrl: string, durationSeconds: number): Promise<{ segments: TranscriptSegment[]; source: 'captions' | 'gemini' }>` from `../transcript-source`; `transcribeViaGemini` from `../gemini` (used only via the real resolver).
- Produces: no signature change to `writeDeepDiveDoc`.

- [ ] **Step 1: Add the `transcribeViaGemini` mock handle + a Gemini-segments fixture**

In `tests/lib/deep-dive/write-doc.test.ts`, after line 18 add:

```ts
const mockTranscribeViaGemini = jest.mocked(gemini.transcribeViaGemini);
```

After the `SEGMENTS` constant (line 23) add a distinct fixture representing Gemini-sourced segments:

```ts
const GEMINI_SEGMENTS: TranscriptSegment[] = [{ text: 'gemini transcript', offset: 0, duration: 30 }];
```

(`lib/gemini` and `lib/youtube` are already `jest.mock`'d at lines 8-9, so `transcribeViaGemini` is auto-mocked; the real `resolveTranscriptSegments` will delegate to these mocks.)

- [ ] **Step 2: Write the failing fallback tests (flip `:103` and `:116`, add the floor test)**

Replace the test at `:103` ("video-only path when transcript fetch fails…") with:

```ts
it('captions gated (fetch throws) → Gemini fallback → combined path with ▶', async () => {
  mockFetchTranscriptSegments.mockRejectedValueOnce(new Error('no captions'));
  mockTranscribeViaGemini.mockResolvedValueOnce(GEMINI_SEGMENTS);

  await writeDeepDiveDoc(makeVideo(), outputFolder, () => {});

  expect(mockTranscribeViaGemini).toHaveBeenCalledWith(YOUTUBE_URL, VIDEO_ID, 300);
  expect(mockGenerateDeepDiveCombined).toHaveBeenCalledWith(YOUTUBE_URL, GEMINI_SEGMENTS, 'en', VIDEO_ID);
  expect(mockGenerateDeepDive).not.toHaveBeenCalled();
  const content = fs.readFileSync(path.join(outputFolder, `${SUMMARY_BASE}-deep-dive.md`), 'utf-8');
  expect(content).toContain('▶ [0:00]');
});
```

Replace the test at `:116` ("video-only path when transcript is empty ([])…") with:

```ts
it('captions empty ([]) → Gemini fallback → combined path with ▶', async () => {
  mockFetchTranscriptSegments.mockResolvedValueOnce([]);
  mockTranscribeViaGemini.mockResolvedValueOnce(GEMINI_SEGMENTS);

  await writeDeepDiveDoc(makeVideo(), outputFolder, () => {});

  expect(mockTranscribeViaGemini).toHaveBeenCalledWith(YOUTUBE_URL, VIDEO_ID, 300);
  expect(mockGenerateDeepDiveCombined).toHaveBeenCalledWith(YOUTUBE_URL, GEMINI_SEGMENTS, 'en', VIDEO_ID);
  expect(mockGenerateDeepDive).not.toHaveBeenCalled();
  const content = fs.readFileSync(path.join(outputFolder, `${SUMMARY_BASE}-deep-dive.md`), 'utf-8');
  expect(content).toContain('▶ [0:00]');
});
```

Add a NEW test immediately after, for the graceful floor (both sources fail):

```ts
it('captions AND Gemini both fail → video-only path, no ▶ (graceful floor)', async () => {
  mockFetchTranscriptSegments.mockRejectedValueOnce(new Error('no captions'));
  mockTranscribeViaGemini.mockRejectedValueOnce(new Error('gemini transcribe failed'));

  await writeDeepDiveDoc(makeVideo(), outputFolder, () => {});

  expect(mockGenerateDeepDive).toHaveBeenCalledWith(YOUTUBE_URL, 'en');
  expect(mockGenerateDeepDiveCombined).not.toHaveBeenCalled();
  expect(mockGenerateDeepDiveFromTranscript).not.toHaveBeenCalled();
  const content = fs.readFileSync(path.join(outputFolder, `${SUMMARY_BASE}-deep-dive.md`), 'utf-8');
  expect(content).toContain('Video-only analysis');
  expect(content).not.toContain('▶');
});
```

- [ ] **Step 3: Update the two OTHER video-only-forcing tests so both sources fail (`:168`, `:180`)**

These intend to reach the video-only path; under the real resolver, a caption rejection alone now triggers `transcribeViaGemini`. Make Gemini fail too.

In `it('surfaces the chosen mode in a step event on the video-only path', …)` (`:168`), after the `mockFetchTranscriptSegments.mockRejectedValueOnce(...)` line add:

```ts
    mockTranscribeViaGemini.mockRejectedValueOnce(new Error('gemini transcribe failed'));
```

In `it('no transcript AND video-only also fails → throws with both error messages', …)` (`:180`), after its `mockFetchTranscriptSegments.mockRejectedValueOnce(...)` line add:

```ts
    mockTranscribeViaGemini.mockRejectedValueOnce(new Error('gemini transcribe failed'));
```

- [ ] **Step 4: Strengthen the combined-path test (`:70`) — prove no extra cost on captioned videos**

In `it('combined path: writes the .md with the resolved ▶ body…')` (`:70`), after line 76 (`expect(mockGenerateDeepDive).not.toHaveBeenCalled();`) add:

```ts
    expect(mockTranscribeViaGemini).not.toHaveBeenCalled();
```

(Captions succeed via `beforeEach` → resolver returns them → Gemini transcribe is never called. The existing `expect(mockFetchTranscriptSegments).toHaveBeenCalledWith(VIDEO_ID)` still holds because the real resolver calls it.)

- [ ] **Step 5: Run the test file to verify the new/flipped tests FAIL for the right reason**

Run: `npx jest tests/lib/deep-dive/write-doc.test.ts`
Expected: FAIL — the two flipped tests and the floor test fail because `write-doc.ts` still uses captions-only `fetchTranscriptSegments`: on a caption rejection it currently goes straight to the video-only path, so `generateDeepDiveCombined` is NOT called and no ▶ is written. (`:168`/`:180` may now pass or error depending on the unmocked transcribe; that's expected pre-fix noise.)

- [ ] **Step 6: Implement the swap in `lib/deep-dive/write-doc.ts`**

Replace the import on line 4:

```ts
import { resolveTranscriptSegments } from '../transcript-source';
```

(Remove `import { fetchTranscriptSegments } from '../youtube';` — it is the only use of that import in this file.)

Replace the transcript fetch (lines 41-43):

```ts
  let segments: TranscriptSegment[] | null = null;
  try {
    const resolved = await resolveTranscriptSegments(videoId, video.youtubeUrl, video.durationSeconds);
    segments = resolved.segments;
  } catch (e) { errors.push(`transcript fetch: ${msg(e)}`); }
```

Everything else (the `segments !== null && segments.length > 0` guard, the combined→transcript-only→video-only cascade, filename, frontmatter, HTML invalidation) is unchanged.

- [ ] **Step 7: Run the test file to verify it PASSES**

Run: `npx jest tests/lib/deep-dive/write-doc.test.ts`
Expected: PASS — all tests green, including the two flipped fallback tests, the new floor test, and the unchanged tiering tests (`:92`, `:132`, `:194`) which still reach the cascade because captions succeed in `beforeEach`.

- [ ] **Step 8: Typecheck + full suite**

Run: `npx tsc --noEmit && npm test`
Expected: tsc clean; full suite green (no regressions in `pipeline.test.ts`, `transcript-source.test.ts`, `ensure*.test.ts`, deep-dive E2E).

- [ ] **Step 9: Commit**

```bash
git add lib/deep-dive/write-doc.ts tests/lib/deep-dive/write-doc.test.ts
git commit -m "fix(deep-dive): source transcript via captions→Gemini resolver so gated videos get ▶ timestamps"
```

---

## Self-Review (completed during planning)

**Spec coverage:**
- Swap `fetchTranscriptSegments` → `resolveTranscriptSegments` → Task 1 Step 6 ✓
- Graceful video-only floor preserved (resolver throws → catch → null) → Step 6 + floor test Step 2 ✓
- B1 (mock youtube+gemini, real resolver) → already the file's topology; Step 1 adds the transcribe handle ✓
- H1 (empty `[]` now triggers Gemini) → flipped `:116` test Step 2 ✓
- H3 (all FOUR affected tests) → `:103`/`:116` flipped (Step 2), `:168`/`:180` dual-fail (Step 3); `:70` strengthened (Step 4) ✓
- H2 (keep combined) → Step 6 leaves the cascade order unchanged; combined runs on resolver segments ✓
- Cost discipline (captioned → no transcribe) → `:70` assertion Step 4 ✓
- Verification repair of visible docs → Phase 4 (post-merge-gate), not a code task — handled by the controller after the suite is green.

**Placeholder scan:** none — every step carries exact code/commands.

**Type consistency:** `resolveTranscriptSegments(videoId, youtubeUrl, durationSeconds)` arg order matches its definition and the `transcribeViaGemini(youtubeUrl, videoId, durationSeconds)` assertion in the flipped tests matches its real signature. `GEMINI_SEGMENTS` is `TranscriptSegment[]`. `makeVideo()` sets `durationSeconds: 300`, matching the `300` asserted in the transcribe calls.
