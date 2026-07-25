# Claude Adversarial Review — Dev-Login Gate (#13) — Round 1

Reviewer: Claude (independent subagent). Artifact: spec `2026-07-24-dev-login-design.md`
+ plan `2026-07-24-dev-login-13.md`. Grounded against real code.

## Blocking

**B1. Gating the UI is not the control the invariant needs; the real control (prod
Supabase Auth config) is never verified.** `signInWithPassword` posts directly to the
prod Supabase Auth endpoint (`/auth/v1/token?grant_type=password`) with the anon key + URL
that already ship in every production bundle (`fly.toml:25`, `lib/supabase/client.ts`).
`/dev-login` is only UI; whether it 404s has zero effect on that endpoint's reachability.
Spec §9 is backwards — the "no prod password user + email provider disabled" state *is* the
control; the UI gate is discoverability only. **Fix:** verify (assert in CI if possible)
prod Supabase has email/password sign-in disabled / no password users; rewrite §9.

## High

**H1. The gate is build-time-inlined, not request-time-evaluated.** Next inlines literal
`process.env.NEXT_PUBLIC_SUPABASE_URL` at build (`Dockerfile:27-53` + `fly.toml:23-25`),
so the prod page is a compile-time constant 404 — stronger than the spec claims, but every
test mutates `process.env` at runtime (jest has no DefinePlugin), exercising a mechanism
prod never uses. Latent footgun: switching to the computed-key form (`process.env['…']`)
would silently make the gate runtime-tamperable. **Fix:** correct spec §3/§4 to say the
gate is resolved at build time from the inlined value (or move to an unambiguous server-only
flag); document that the literal form is load-bearing if kept.

**H2. No automated guard for the only real prod-leak path (a build that inlines a local
URL).** Invariant holds only because the deploy build arg is non-local (`fly.toml:24`). A
build with a local arg → `/dev-login` renders in prod, unit tests stay green. **Fix:** add a
build/CI assertion that the deploy build arg host is non-local and/or a smoke test that curls
the built server's `/dev-login` and asserts 404. DoD's "or trust test #1" is the gap.

## Medium

**M1. Spec §5 cookie analogy is wrong; soft-nav session propagation unverified.**
`signInWithOAuth` does NOT write the cookie client-side — `app/auth/callback/route.ts`
writes it server-side via `exchangeCodeForSession`. Password sign-in writes cookies
client-side then soft-navigates (`router.replace`); whether middleware sees the fresh cookie
on that soft RSC nav is untested. **Fix:** correct the analogy; use a hard nav
(`window.location.assign('/')`) to force a fresh server round-trip, matching OAuth.

**M2. §3 "local prod-build" benefit oversold** — only true if that build inlined a local
URL; running the prod image locally inlines the prod URL → disabled. Net fail-closed (safe)
but reword.

**M3. Test-env coupling is order-fragile.** `next/jest` skips `.env.local` under
`NODE_ENV=test`; `NEXT_PUBLIC_SUPABASE_URL` is `undefined` in tests, so existing LoginPage
tests pass incidentally. **Fix:** set/delete `NEXT_PUBLIC_SUPABASE_URL` in `beforeEach`, not
just `afterEach`.

## Low / Positive

- **L1 (positive):** `classifyRoute` exact-match (`route-categories.ts:14`) — `/dev-login`
  cannot sweep in `/dev-login-secrets`. No prefix bypass.
- **L2 (positive):** page gate is independent of middleware + `STORAGE_BACKEND`; layered.
- **L3:** Task 4 test asserts `notFound()` is *called*, not a real 404 response — reinforces
  H2.
- **L4:** `DevLoginForm` has no double-submit guard — YAGNI, note so it isn't re-flagged.

## Bottom line

The page is robustly absent in prod, but the plan earns that by accident relative to its own
(inaccurate) description and never verifies it at the layer that could regress. Highest-value
fixes: (1) assert the deploy build arg is non-local + smoke-test the built server 404s
(H2); (2) confirm prod Supabase disables email/password sign-in (B1) — that, not the UI
gate, makes "impossible to use" true.
