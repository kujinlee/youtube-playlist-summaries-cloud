# Stage 1E-b Task 8 — Claude Task Review (worker/main.ts) + fixes

**Reviewer:** Claude (Opus), read-only, adversarial — **ran the binary** (caught a Critical Jest masked). **Target:** diff `40b2972..6193eb1` (worker entrypoint + loop + SIGTERM). **Date:** 2026-07-07.
**Verdict:** Needs fixes → **1 Critical + 2 Important + 1 Minor fixed** → clean.

## Spec compliance: ✅ (post-fix)
No `server-only` import (verified via full import-graph trace); loop crash-safe (`runOnce` never rejects, `sleep` never rejects); SIGTERM/SIGINT → `abort()`, no forced `process.exit` mid-job; env fail-fast before client build; `require.main === module` auto-run guard; `workerId` unique per process; `package.json` change is only the `worker` script (+ the `tsconfig-paths` devDep the fix required).

## Critical (FIXED)
- **`npm run worker` crashed on line 1 — the entrypoint was dead-on-arrival.** The `worker` script omitted the `TS_NODE_COMPILER_OPTIONS='{"module":"commonjs"}'` prefix every other ts-node script uses (tsconfig is `module: esnext`, no `"type": "module"`), so `SyntaxError: Cannot use import statement outside a module`. The Jest path (ts-jest's own CJS transform) masked it. **Additionally** (found while fixing): even with the prefix, `@/` aliases don't resolve under ts-node (`tsconfig-paths` was not installed, and `worker/main.ts` + all its transitive `lib/` imports use `@/`) → `Cannot find module '@/lib/...'`. **Fix:** `"worker": "TS_NODE_COMPILER_OPTIONS='{\"module\":\"commonjs\"}' ts-node -r tsconfig-paths/register worker/main.ts"` + added `tsconfig-paths` devDep. **Verified empirically:** `npm run worker` (env-less) now boots and fail-fasts with `Missing required env var: NEXT_PUBLIC_SUPABASE_URL` — the module loads, `@/` resolves, `main()` reaches the env check.

## Important (FIXED)
- **I1 — `sleep` leaked an abort listener every idle cycle.** `{ once: true }` only removes the listener on the *abort* path; on the normal timeout path (every idle poll) it stayed attached to the process-lifetime signal → `MaxListenersExceededWarning` after 10, unbounded growth over uptime. **Fix:** capture the listener and `removeEventListener` it in the timeout branch.
- **I2 — the idle→sleep→abort paths had zero test coverage.** The existing test aborts from inside the handler, so `runOnce` returns `'done'` and `sleep` is never called — the one behavior the task guarantees (prompt shutdown during idle backoff, no leak) was unverified. **Fix:** exported `sleep`; added 3 focused tests — (1) abort mid-wait resolves in <1s (not the 10s delay), (2) already-aborted resolves <200ms, (3) the normal timeout path calls `removeEventListener('abort', …)` (no per-poll leak).

## Minor (FIXED)
- **M1 — no already-aborted short-circuit.** If `signal` was already aborted on `sleep` entry, `addEventListener('abort')` never fires → the loop waited the full `POLL_MS` before exiting. **Fix:** `if (signal.aborted) return resolve();` at the top (covered by test 2).

## Minor — not changed
- **M2 — SIGTERM/SIGINT listeners never removed.** Harmless at process exit (they live exactly as long as the process). Not worth the churn.

## Verified
Integration 107, unit 1588, tsc 0, `check:confinement` OK. `npm run worker` boots to env fail-fast.

## Task quality verdict: Approved (post-fix).
