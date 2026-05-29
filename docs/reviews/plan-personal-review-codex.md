# Codex Adversarial Review — Personal Review Implementation Plan

**Date:** 2026-05-28
**Plan:** `docs/superpowers/plans/2026-05-28-personal-review.md`
**Phase:** Phase 2 (plan review)

---

## Findings

**Blocking**

- Task 1 creates `tests/types/index.test.ts` but `jest.config.ts` only matches `tests/lib`, `tests/api`, `tests/smoke.test.ts`, `tests/components`. The file would be ignored by `npm test`. Fix: put the type test under `tests/lib/` or extend jest config.

- Task 6 makes `VideoList` require `minPersonalScore` and `onAnnotationChange`, but commits before fixing `app/page.tsx` and `VideoList.test.tsx`. The repo is knowingly broken between Task 6 and Task 8. Fix: make the new props optional with safe defaults in VideoList, or move the call-site fixes into Task 6.

- Task 8.1 VideoList test snippet references `baseVideo` (doesn't exist in that file) and assumes VideoRow renders unshallowly, but VideoList.test.tsx mocks `@/components/VideoRow`. The radiogroup assertion will never find `StarRating`. Fix: rewrite the test to assert VideoList forwards the annotation callback to VideoRow props rather than asserting on StarRating internals.

- The plan never tests or specifies how optimistic annotation updates interact with active `personalScore` sorting. Sorting is server-side; `handleAnnotationChange` only patches local state, so changing a score while sorted by My Score leaves rows in stale order. Fix: document this as a known limitation (re-sort by clicking the header) or add a post-save refetch.

**High**

- Task 2 file map lists 404/500 coverage but the test suite has no test for a generic `updateVideoFields` error → 500. Add that case.

- Task 2 mocks deletion by asserting `{ personalScore: undefined }` but never tests that the value is actually absent from the written JSON. Consider a lib-level test for `updateVideoFields` with `undefined` to confirm JSON omission.

- NoteCell truncation test expects `btn.textContent.toHaveLength(27)` for 25 chars + `…`. The ellipsis `…` is one UTF-16 code unit, so actual length is `26`. Fix the assertion.

- Task 6.3 instructs adding `import type { Video } from '@/types'` to `VideoRow.tsx`, but `Video` is already imported there (`VideoType`, `Audience`, and `Video` are imported from `@/types`). Blind execution will create a duplicate identifier error.

- Task 6 modifies VideoList headers, sort behavior, and DESC_FIRST_COLS but adds no `VideoList.test.tsx` updates. Missing coverage: My Score header present, first click direction is desc, Note has no sort button, `dimUnscored` computed correctly, `onAnnotationChange` forwarded.

- Task 8 has no real tests for `minPersonalScore` page-level filtering. Missing: below-threshold scored videos are hidden; unscored videos remain visible (and receive `opacity-50`); clearing a score under an active filter makes the row visible/dimmed.

**Medium**

- Plan header says "Next.js 15" but `package.json` has `16.2.6`. AGENTS.md warns explicitly about this; fix the stated version.

- Task 3 expected failure says "falls through to ratings sort which errors" — but `a.ratings.personalScore` is `undefined` not a throw; sort may silently produce wrong order rather than error. Fix the wording.

- Test counts are inconsistent: Task 2 says "13 passing" but file map says 11; Task 4 says "7 passing" but the test block has more cases; Task 5 says "11 passing" but the block has more. Mismatches will confuse implementation agents.

- StarRating tests do not assert that clearing a star sends `personalScore: null` in the request body. The API body for clear is untested.

- NoteCell tests do not assert the request body (including `personalNote: ""` for clear) or the 500-char boundary behavior.

- NoteCell implementation uses `absolute left-0 w-72`; right-edge rows will overflow the viewport. Spec requires viewport constraint.

- Spec line ~91 still says `POST /api/videos/[id]/annotation` (old name). URL contracts table on line ~214 correctly says `/review`. Fix the stale reference.

**Low**

- Task 8.4 uses `grep` but repo tooling prefers `rg`.

- FilterBar `My score ≥` option for value 5 is labeled `5` while all others use `N+`. Clarify whether this is intentional.

---

## Verdict

**Not implementation-ready.** The four blocking issues (jest config, broken commit ordering, wrong VideoList test, stale sort after optimistic update) must be resolved. High issues should be fixed before handing to implementation agents; mediums should be addressed unless explicitly deferred.
