# Task 4 Review — worker kind→handler dispatch (Approved, converged)

Task review of `477b8f8` (base `56f53b7`); Minor test-tightening `e7ea691`.
Diff: `lib/job-queue/dispatch.ts` (`makeJobHandler`), `worker/main.ts` (wire summary+dig), `tests/lib/job-queue/dispatch.test.ts`.

Pure routing, no money/auth/concurrency surface → single Claude task-reviewer (sonnet) is proportionate; Codex not dispatched.

## Claude task-reviewer — ✅ Spec compliant, Task quality Approved (0 Critical/Important)
- `makeJobHandler(handlers: Record<JobKind, JobHandler>)` is exactly the required pure kind→handler dispatch (`dispatch.ts:8-14`); `JobKind='summary'|'dig'` unchanged (`job-queue.ts:4`).
- Unknown-kind guard throws `NonRetryableError` (not plain/retryable) so the runner dead-letters instead of looping; `if (!h)` preserved as a deliberate runtime bad-data guard despite the `Record` type saying `h` is always defined.
- `worker/main.ts:65-68` wires `makeJobHandler({ summary: makeSummaryHandler(client), dig: makeDigHandler(client) })`; `runWorkerLoop({ queue, handler, ... })` byte-identical to before — summary path untouched.
- **Async deviation verified correct (not just safe):** the brief's sample was a *sync* arrow whose `if (!h) throw` would throw *synchronously* — which would fail the brief's own `.rejects.toThrow(...)` test (a sync throw isn't a rejected promise). Making the handler `async` converts the guard throw into a genuine rejection. Verified the only caller `worker-runner.ts:52-58` does `await handler(job, ctx)` inside try/catch, so async-reject and sync-throw are caught identically; line 64 `retryable: !(e instanceof NonRetryableError)` preserves dead-lettering. The implementer caught a latent brief bug and fixed it provably-safely.

## Findings

### Minor — FIXED (`e7ea691`)
Unknown-kind test asserted only the message (`/no handler for kind/`), not `instanceof NonRetryableError`. On a money-path slice this matters: the dead-letter-vs-retry distinction depends on the *class*; a future plain-`Error` regression with the same message would silently become a retry loop (wasted slots / potential re-charge). **Disposition:** fixed inline — test-only; now asserts `toBeInstanceOf(NonRetryableError)` AND the message. `npx jest dispatch` green. No re-review round (test-only, strengthens already-correct code).

## Disposition
Converged. Approved with the one Minor tightened inline. Tests: dispatch 2/2 (message+class), full suite 2100/2100, tsc clean.
