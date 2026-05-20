# Task 17: E2E Tests — Claude Code Review

## Critical

**[C1] `callCount` integer in ingest test breaks under React StrictMode double-invoke**
`tests/e2e/playlist-viewer.spec.ts` line 147.
In Next.js 15 dev mode, React StrictMode causes `useEffect` to fire twice on mount. `fetchVideos` is called twice before any user action. The second mount call increments `callCount` to 2, which is `> 1`, so it returns `[video]` — the video list is populated on initial page load before ingest starts. The post-ingest assertions vacuously pass and the ingest flow is never actually verified.
Fix: replace `callCount` with an explicit boolean flag set only after the SSE done event is confirmed.

## Important

**[I1] `sseBody` helper undocumented single-field constraint**
`tests/e2e/playlist-viewer.spec.ts` lines 41–43.
`sseBody` only supports single `data:` field per event. Adding `id:` or `event:` fields to future events would require updating the helper. No comment marks this constraint.
Fix: add a single-line comment documenting that each event must be a single `data:` field.

**[I2] dev-process.md checklist: `(If complex)` is vague, no cross-reference to definition**
`docs/dev-process.md` line 81.
The checklist item says `(If complex)` but the definition of "complex" is in the paragraph two lines below the checklist block. A reader scanning only the checklist may skip the behaviors review for a task with SSE state machines and multiple error paths.
Fix: change the checklist item to `(If complex — see "Behaviors adversarial review" below)`.

## Verdict

E2E tests pass all 9 scenarios. One critical timing issue (C1) affects the ingest test's integrity under Next.js dev-mode StrictMode. Two important documentation/robustness issues. Fix C1 before committing.
