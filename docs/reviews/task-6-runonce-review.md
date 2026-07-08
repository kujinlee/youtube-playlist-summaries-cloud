# Stage 1E-b Task 6 — Claude Task Review (runOnce upgrade) + fix

**Reviewer:** Claude (Opus), read-only, adversarial, concurrency-focused. **Target:** diff `3b6f95b..b481827` (heartbeat + composed signal + wall-clock + teardown + retryability). **Date:** 2026-07-07.
**Verdict:** Approved → **1 latent-hazard Minor fixed** (uniform outcome contract) → clean.

## Spec compliance: ✅
Rows (a)–(g) + idle smoke present and mapped; back-compat `export type { JobHandler }`; `NonRetryableError` with `name`; `HandlerCtx = {isCancelled, signal, setPhase}`; `RunnerOpts` gains `shutdownSignal`/`wallClockMs`. tsc 0; runtime suite green, sub-second, clean exit (no leaked handle, no `--forceExit`).

## The 3 convergence-area pitfalls — all PASS
1. **Composed signal PASS:** `AbortSignal.any([wallClock.signal, leaseLost.signal, opts.shutdownSignal].filter((s): s is AbortSignal => Boolean(s)))` — `.signal` on both controllers, `shutdownSignal` passed bare (already a signal), type-guard filter (no `as`). A bare controller reaching `AbortSignal.any` is structurally impossible.
2. **Timer teardown PASS:** `wct` stored + `unref?()`'d; both `clearInterval(hb)` + `clearTimeout(wct)` in the single `finally`, fired on every exit path (success, throw, early returns — all inside the `try`). `hb` correctly NOT unref'd (must hold the loop while the handler runs) but always cleared.
3. **Heartbeat rejection safety PASS:** `.then(r => !r.ok && leaseLost.abort())` AND `.catch(() => leaseLost.abort())` — a throwing heartbeat can never become an unhandled rejection. Interval `floor(leaseSeconds*1000/3)`.

## Single-terminal-write — PASS (guard is load-bearing, not dead)
`settled` makes try-tail and catch mutually exclusive. Crucially, if `queue.complete()` itself rejects, control enters the catch with `settled===true` → returns `'lost'` and `fail` is NOT called (the guard prevents a complete-failure becoming a second write). Lease-lost-mid-handler (test f) traced clean: heartbeat ok:false → abort → handler rejects → catch → `fail` ok:false → `'lost'`; exactly one write.

## Fixed Minor (latent hazard for Task 8)
- **Asymmetric terminal-write error handling:** a throwing `queue.complete()` was already caught (→ `'lost'`), but a throwing `queue.fail()` in the catch had no guard → it rejected OUT of `runOnce`, violating the declared `Promise<'idle'|'done'|'failed'|'cancelled'|'lost'>` contract. Task 8's worker loop calls `runOnce` in a loop, so this was a latent unhandled-rejection crash path — the same class the heartbeat `.catch` guards against. **Fix:** wrapped the terminal `fail` await in try/catch → `return 'lost'` on throw, making the outcome contract uniform (runOnce never rejects). New test `(h)` asserts a throwing `fail` RPC resolves to `'lost'` and never rejects. Integration 95, unit 1588, tsc 0.

## Minor — CARRIED FORWARD (for Task 8 worker loop / whole-branch triage)
- **Cooperative, not preemptive abort:** `runOnce` awaits the handler regardless; `wallClockMs` only bites if the handler honors `ctx.signal`. Task 5's `summaryCore` threads the signal into `generateSummary`/`resolveTranscriptSegments` (cancellable), but `extractQuickView`/magazine/fix are not (Task 4 carried flag). **Task 7/8 note:** the handler path must honor `ctx.signal` for the wall-clock bound to be real.
- **Wall-clock doesn't cover `sweepExpired`/`claim`** (run before `wct` is armed). Low risk (fast DB ops).
- **Test (a) proves heartbeat CADENCE, not lease EXTENSION** (fake `heartbeat` returns ok:true regardless of elapsed); real extension proven at DB level in `job-queue-worker.test.ts:30`. Acceptable coverage division; report's "extended the lease" wording is overstated.
- **Nit:** `floor(leaseSeconds*1000/3)` has no lower clamp — theoretical (default 120; tests use 2 → 666ms).

## ⚠️ Unverifiable-from-diff
- Real `SupabaseJobQueue.fail` returning `status:'cancelled'` (the `'cancelled'` branch) — asserted by the live `job-queue-runner.test.ts` cancel test, not this fake-queue suite.
- Whether real pipeline handlers honor `ctx.signal` (cooperative-abort caveat) — Task 7/8 surface.

## Task quality verdict: Approved (post-fix).
