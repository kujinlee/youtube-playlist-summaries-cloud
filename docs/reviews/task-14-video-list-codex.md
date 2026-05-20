# Task 14: Video List Component — Codex Adversarial Review

## Critical
None beyond prior Claude review's empty-`ul` behavior.

## Important

**[I1] components/VideoList.tsx:26** — Archived state conveyed only with `opacity-50`; screen reader users get no equivalent cue. Row reads as ordinary until they open the menu and find "Unarchive".
- Fix: add visually hidden `<span className="sr-only">Archived</span>` inside archived `<li>` wrapper.

**[I2] tests/components/VideoList.test.tsx:7-30** — Suite fully mocks VideoRow; no real integration test. Tests can pass while real VideoRow rendering or archive action is broken.
- Fix: add at least one integration-style test using the real VideoRow. (Deferred to Task 7 E2E per project TDD policy — layout/wiring components covered by Playwright E2E.)

**[I3] tests/components/VideoList.test.tsx:19-26, 86-98** — Callback tests rely on a mock that invents behavior (single click triggers both onDeepDive and onArchive). Tests prove mock received function props, not that user-facing actions work.
- Fix: rename as narrow prop-forwarding tests; real action coverage left to E2E (Task 7).

**[I4] tests/components/VideoList.test.tsx:126-136** — Grey-wrapper tests do not assert wrapper is a `<li>`. Would pass if implementation used a `<div>` instead, breaking list semantics.
- Fix: use `row.closest('li')` rather than `row.parentElement`.

## Minor

**[M1] components/VideoList.tsx:26** — `key={video.id}` assumes Video.id is globally unique; types/index.ts only types it as `string`. Duplicate IDs would cause React key collisions when toggling archive visibility.
- Low risk — ID uniqueness is an upstream invariant.

**[M2] tests/components/VideoList.test.tsx** — No rerender test for toggling `showArchive`. A stale memoization or stateful regression could pass one-shot render tests.
- Fix: add test that renders with `showArchive=false`, rerenders with `true`, then `false`.

## Overall Verdict

Not ready to commit in current state. Filtering logic is correct, but empty-list/accessibility issues plus heavy mocking leave the component under-protected. Address I1 (accessible archived state), empty-`ul` → null, `aria-label`, and I4 (`li` semantics assertion) before committing.
