# Task 17: E2E Tests — Codex Adversarial Review

## High

**[CB1] Obsidian test only checks URI scheme, not vault/file params**
`tests/e2e/playlist-viewer.spec.ts:297-299`.
`expect(href).toMatch(/^obsidian:\/\//)` passes even if `vault` or `file` query params are missing or wrong.
Fix: Parse the href and assert `vault === OUTPUT_FOLDER` and `file === 'vid-1'`.

**[FR1] Ingest progress assertion races against atomically delivered SSE body**
`tests/e2e/playlist-viewer.spec.ts:160-163`.
Static SSE body delivers step+done together; React may batch the state transitions, collapsing running→done in one render. Progress bar might never be observable on CI.
Fix: Separate the progress bar assertion before the done event, or accept that progress visibility is not reliably testable with static SSE mocking.

**[MB1] No E2E for SSE stream failure after a successful POST**
No test exercises EventSource error (network drop, 404 stream) after a successful ingest or deep-dive POST.
Fix: Add tests for stream failure, asserting correct error alert and no stale progress.

**[VP1] Deep dive test asserts only the done state, not that progress was ever shown**
`tests/e2e/playlist-viewer.spec.ts:226`.
If progress UI is removed, the test still passes.
Fix: Assert progressbar visible before asserting done state.

**[SSE1] Static route.fulfill() SSE cannot test real EventSource lifecycle**
Delivering a complete `text/event-stream` body at once models body parsing, not streaming. Incremental delivery, retry, server disconnect, and duplicate terminal events are untested.
Deferred: requires browser-level EventSource control beyond Playwright's current interception API.

## Important

**[CB2] PDF link test uses loose substring match**
`tests/e2e/playlist-viewer.spec.ts:279-282`.
`toContain` allows malformed hrefs.
Fix: Assert `pathname === '/api/pdf/vid-1'` and `searchParams.get('type') === 'summary'` via URL parsing.

**[CB3] Sort test proves request sent, not that rendered order changed**
`tests/e2e/playlist-viewer.spec.ts:181-203`. Always returns one video, only checks `sortColumn=overall`.
Fix: Return two videos in different order pre/post sort; assert rendered row order changes.

**[CB4] Archive test does not verify request body**
`tests/e2e/playlist-viewer.spec.ts:246-249`. Archive route fires but body (`action`, `outputFolder`) is not verified.
Fix: Assert POST body in the route handler.

**[RP2] Unexpected API calls continue to real Next.js server**
`route.continue()` for unmatched paths lets real filesystem-backed routes run on CI.
Fix: Return 500 for unexpected requests to catch wrong URLs early.

**[MB2] Settings failure test does not wait for the request to complete**
`tests/e2e/playlist-viewer.spec.ts:303-315`. Asserts empty folder without confirming settings 500 was received.
Fix: `page.waitForResponse('**/api/settings')` before asserting fallback.

**[MB3] Ingest POST failure test does not assert stream is never opened**
A regression that opens the SSE stream after a failed POST would still pass.
Fix: Register a stream route that fails the test if called.

**[CI1] E2E suite runs against `next dev`, not production build**
Dev mode has HMR, StrictMode double-invoke, and compilation latency. Production regressions may be missed.
Deferred: add production E2E job as a follow-on.

## Low

**[CB-L1] Checklist `(If complex)` cross-reference missing** (already in Claude review — [I2])
**[RP1] Route handlers do not check HTTP method** — accepts any method, weakens contract verification.
**[SSE2] No test for out-of-order or duplicate terminal SSE events.**
**[VP2] Settings failure test could pass if settings fetch is removed entirely.**

## Verdict

E2E suite provides useful smoke coverage — all 9 tests pass against the running app. Structural weaknesses: static SSE mocking cannot exercise real streaming lifecycle (known tradeoff), and several assertions check presence/scheme rather than the full semantics. High items CB1 and VP1 are actionable and tighten existing tests. FR1 reflects an inherent limitation of the SSE mocking approach. Address High/Important as feasible before committing; defer SSE1 and CI1 as known limitations.
