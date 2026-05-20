# Task 10: API Routes — Claude Code Review

## Strengths

1. All 8 routes implemented and present. Full surface area from the implementation plan is covered.
2. Security validation is solid where applied. `assertOutputFolder` uses `path.resolve` + `os.homedir()` + `realpathSync.native`. `assertVideoId` rejects anything not matching `/^[A-Za-z0-9_-]{1,20}$/`. Both called consistently in every route that handles user-supplied paths.
3. Next.js 16 `params` contract respected everywhere — all dynamic-segment routes type `params` as `Promise<{ id: string }>` and `await` it.
4. `deleteJob` idempotency is safe — `Map.delete` on a missing key is a no-op.
5. Listener cleanup on terminal events — `emitter.removeListener('progress', onProgress)` called before `controller.close()` on both SSE routes.
6. Test suite is green, 30/30.
7. Sort logic is correct — `[...videos]` copy avoids mutating the index.

## Issues

### Critical (Fixed before merge)

**C1 — `POST /api/settings` persists an unvalidated `outputFolder`.**
- `app/api/settings/route.ts` called `writeSettings({ outputFolder })` without `assertOutputFolder`. Any path including `/etc` would be written and later used by every other route.
- Fix applied: added `assertOutputFolder(outputFolder)` call with 400 on failure.

**C2 — No type-guard on `outputFolder` in `POST /api/settings`.**
- `body?.outputFolder` typed as `unknown` at runtime — `{ "outputFolder": 42 }` would pass the truthy check and write a number to settings.json.
- Fix applied: added `typeof outputFolder !== 'string'` check → 400.

### Important (Should Fix)

**I1 — SSE streams have no `cancel` callback — EventEmitter listeners leak on client disconnect.**
- Both stream routes attach `emitter.on('progress', onProgress)` but provide no `cancel` callback. On browser disconnect, subsequent `emitter.emit` calls throw `TypeError: Cannot enqueue into a cancelled readable stream`.
- Fix applied: added `cancel() { emitter.removeListener('progress', onProgress); }` to both SSE ReadableStream constructors.

**I2 — Double `deleteJob` race after terminal event + `.catch()` both fire.**
- Guard flag `let finished = false` added to progress callback; terminal event sets it and only the first terminal path emits/closes.

**I3 — `settings-store.ts` uses `process.cwd()` (serverless environments may be read-only).**
- Deferred — local dev only per design. `.gitignore` verified to not include `settings.json` (file not committed).

**I4 — Missing test: `POST /api/settings` with invalid `outputFolder` returns 400.**
- Test added after C1 fix.

### Minor (Deferred)

- M1: Error responses on bare `new Response(...)` calls missing `Content-Type: application/json`
- M2: Rating sub-column sort not tested
- M3: EventEmitter default max-listener limit (10) can produce Node.js warning under load
- M4: `ingest/stream` does not validate `jobId` format
- M5: Missing test — SSE stream closes after `done` event fires

## Assessment

**Ready to merge: With fixes** (C1, C2, I1, I2 addressed before commit; I4 test added)
