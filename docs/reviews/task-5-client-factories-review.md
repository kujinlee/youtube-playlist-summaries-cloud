# Task 5 Review — Supabase client factories + service guard

**Reviewer:** Claude (sonnet), fresh subagent (task reviewer, SDD)
**Commit:** 167b1e1 | **Verdict:** SPEC ✅ / QUALITY approved

## Spec compliance
Three factories present: `client.ts` (browser/anon), `server.ts` (RLS-scoped, cookie-bound, never service_role), `service.ts` (`import 'server-only'` literal line 1 + runtime `window` guard + missing-key guard). Additive-only, no scope creep (no middleware/routes/migrations). Full suite 1493/1493; `tsc --noEmit` clean. Deferred Minor from Task 1 closed: `getServiceRoleKey` positive test added.

## Scrutinized deviations — both correct
1. **`getServiceRoleKey()` reordered before `getSupabaseEnv()` in `service.ts`** — correct: the missing-key guard test sets URL but not anon key, so the original order would throw about the wrong var. Both runtime guards (window defined; key absent) verified passing.
2. **`@supabase/ssr` 0.12.0 `SetAllCookies` requires a 2nd `headers` param** the plan omitted; accepted as unused `_headers`. Cookies (the `list`) forward correctly, so session persistence is NOT broken.

## Findings
- **Important (carry-forward to Task 10, not a Task 5 defect):** the `_headers` the factory drops carry anti-cache directives (`Cache-Control: private, no-store`). The factory abstraction intentionally can't set response headers. Middleware sets its own cookies+headers inline (fine). But **Task 10's callback route uses `createServerSupabase`** and would silently drop the cache headers → a CDN could cache a session `Set-Cookie` and serve it to another user. → **RESOLVED in plan:** Task 10 callback now wraps its redirects in a `noStore()` helper setting `Cache-Control: private, no-store, …` + a test asserting `no-store` on the success (cookie) response.
- **Minor:** `service-guard.test.ts` missing-key test is order-fragile (safe given current ordering). → note for final review.
- **Minor:** `server.ts` `CookieStore.set` options typed `Record<string, unknown>` rather than `@supabase/ssr` `CookieOptions`; cast hides narrowing. → optional tighten in Task 10.

No Critical findings. No regressions.
