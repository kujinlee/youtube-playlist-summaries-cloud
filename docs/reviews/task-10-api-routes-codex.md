# Task 10: API Routes — Codex Adversarial Review

## High / P1 Findings (6)

**[H1] — `app/api/settings/route.ts:10` — POST /api/settings persists unvalidated outputFolder (security)**
`outputFolder` passed to `writeSettings` without homedir containment validation. Any path including `/etc` or `/root` would be persisted and used by all subsequent routes.
Fix applied: `assertOutputFolder(outputFolder)` called before `writeSettings`; 400 on failure.

**[H2] — `app/api/ingest/stream/route.ts:17` — Ingest SSE stream has no `cancel()` cleanup**
`ReadableStream` registers `emitter.on('progress', onProgress)` with no `cancel()` callback. On client disconnect, listener remains attached and subsequent emits throw `TypeError: Cannot enqueue into a cancelled readable stream`.
Fix applied: added `cancel() { emitter.removeListener('progress', onProgress); }` to ReadableStream.

**[H3] — `app/api/videos/[id]/deep-dive/stream/route.ts:19` — Deep-dive SSE stream has no `cancel()` cleanup**
Same issue as H2 on the deep-dive stream route.
Fix applied: same `cancel()` callback added.

**[H4] — `app/api/ingest/route.ts:31` — Background `.catch()` can emit into stale SSE listeners**
`.catch()` handler unconditionally emits after the job may already have been deleted and the stream controller closed. Stale listener calls `controller.enqueue` on a disconnected controller.
Fix applied: `let finished = false` guard in progress callback; terminal events set flag and guard prevents double-emit.

**[H5] — `app/api/videos/[id]/deep-dive/route.ts:32` — Deep-dive `.catch()` can emit into stale SSE listeners**
Same race as H4 on the deep-dive route.
Fix applied: same `finished` guard added.

**[H6] — `app/api/settings/route.ts:10` — `outputFolder` not narrowed to string before `writeSettings`**
`body?.outputFolder` typed as `unknown` at runtime. `{ "outputFolder": 42 }` would pass truthy check and write a number.
Fix applied: `typeof outputFolder !== 'string'` check → 400.

## Medium / P2 Findings

- `tests/api/settings.test.ts` — no test for outside-homedir path → 400 (test added)
- `tests/api/ingest.test.ts` — no SSE disconnect cleanup test (deferred to E2E)
- `tests/api/deep-dive.test.ts` — no SSE disconnect cleanup test (deferred to E2E)

## Assessment

**Ready to merge: With fixes** (all 6 High findings addressed before commit)
