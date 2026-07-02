# Task 10 Review — Auth wiring (middleware + OAuth callback + classifier)

**Reviewer:** Claude (sonnet), fresh subagent (task reviewer, SDD) + re-review
**Commits:** 10edbc8 (impl) + 667b35f (fix) | **Verdict:** SPEC ✅ / QUALITY approved *(after fix + re-review)*

## Spec compliance (after fix)
Classifier (public / anon-allowed / authenticated) + `needsAnonProvision`; session-refresh middleware with anon auto-provision on anon-allowed (Codex H1) and authenticated→`/` redirect; OAuth callback with code-exchange, error→`/auth/auth-error` (Codex M4), and `noStore()` Cache-Control (Task 5 carry-forward). Installed Next.js v15 matched the plan (`cookies()` async, `NextResponse` APIs). Additive only. Full suite 1505/1505; tsc clean; `check:confinement` OK.

## CRITICAL found + fixed (667b35f)
- **`/auth/callback` + `/auth/auth-error` were classified `authenticated`** → middleware redirected the unauthenticated OAuth callback to `/` before the handler ran, **blocking every new-user Google sign-in**. No unit test in the task surfaced it (the bug lives in the middleware↔handler interaction). Fixed: a `PUBLIC_PREFIX = ['/auth']` classified via `pathname === p || pathname.startsWith(p + '/')`. Re-review confirmed the boundary guard: `/authors` is NOT falsely matched (`'/authors'.startsWith('/auth/')` is false). Tests assert `/auth`, `/auth/callback`, `/auth/auth-error` → public.

## Also fixed
- **Important:** error-path callback tests (exchange-failure + no-code) now assert `Cache-Control: no-store`.
- **Minor:** `as never` → `as unknown as CookieStore` (type exported from `server.ts`); production cast narrowed. (A residual test-only `as never` on a throwaway request stub is acceptable.)

Re-review verdict: SPEC ✅ / QUALITY approved. No regressions to the other route categories or `needsAnonProvision`.
