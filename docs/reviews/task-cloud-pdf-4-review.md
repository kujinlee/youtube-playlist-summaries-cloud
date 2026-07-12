# Task 4 — `pdf-concurrency` — dual review trail

**Files:** `lib/pdf/pdf-concurrency.ts` + test. Base 77e1493 → head ce9aad8.

## Claude code review (sonnet) — impl ca82e56 — "Needs fixes (small)"
Spec ✅ core mechanics correct + verified: no-poison (`finally` deletes on resolve+reject), sync-throw safety (async IIFE), check-then-set atomicity (no `await` between get/set and guard/increment → no interleave), no over-release (busy throws before `active++`, only acquired path enters `finally`), non-vacuous tests.
- **Important:** cap test sets `process.env.PDF_MAX_CONCURRENCY='1'` and never restores → leaks across test files in the same jest worker; a future fresh import (Task-5 route tests) inherits MAX=1. Fix: afterEach restore/delete.
- Minor: `|| 3` short-circuits `0`→3 (spec-inherited); no sync-throw test; Map `as Promise<T>` cast; composition note (all waiters share one PdfBusyError outcome).

## Codex adversarial review (gpt-5.5) — impl ca82e56 — 0 Blocking/High
Core mechanics confirmed correct (single-flight delete both paths; sync-throw converted; independent keys; busy before `active++`; release once; waiters don't hold slots).
- **Medium:** `PDF_MAX_CONCURRENCY='0'` → 3 (via `parseInt('0')||3`), violates the `Math.max(1,…)` floor → capacity inflation. Fix: default only on NaN, then clamp.
- Low: no sync-throw test; no MAX>1 boundary test.

## Fix (ce9aad8)
- **Medium (env clamp):** parse then clamp separately — `Number.isNaN(parsed) ? 3 : Math.max(1, parsed)`. Now `0`/negative→1, unparseable→3.
- **Important (env leak):** `afterEach` restores original `PDF_MAX_CONCURRENCY` + `jest.resetModules()`.
- **Low:** added sync-throw no-poison test, MAX=2 off-by-one boundary test, MAX=0 clamp test.

**Final:** 6/6 pdf-concurrency tests; full suite 2031/2031; tsc clean. Both passes' findings addressed; core logic was correct from the start.
