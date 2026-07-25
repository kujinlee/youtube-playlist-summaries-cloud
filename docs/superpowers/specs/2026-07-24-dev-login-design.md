# Dev-Login (env-gated email/password) — Design Spec

**Date:** 2026-07-24
**Backlog item:** #13 (`docs/backlog.md`)
**Status:** design — awaiting user review

---

## 1. Scope / Goal

Give a developer a way to sign into the app UI with **email + password** when running
against a **local Supabase**, so browser-based manual testing (esp. the Sync feature)
no longer needs the `login.sh` + DevTools-console cookie-paste workaround.

The app's real login is **Google-OAuth only** (`app/login/page.tsx` →
`signInWithOAuth({ provider: 'google' })`). Local Google OAuth needs client-id/secret
env vars that are normally unset, so there is currently **no way to sign into the app UI
against local Supabase (#2)** without hand-injecting a session cookie.

The Supabase JS browser client already supports `signInWithPassword` and already manages
the session cookie automatically (see `lib/supabase/client.ts` → `createBrowserClient`).
The only missing piece is a **UI form that calls it** — gated so it is structurally
absent in production.

## 2. Non-goals (YAGNI)

- No rate-limiting, lockout, or CAPTCHA — local-only affordance against a throwaway DB.
- No user creation / management / password-reset UI. The test user is provisioned out of
  band (service-role admin API; see `docs/local-manual-test-env` memory).
- No change to the production login flow (Google OAuth stays exactly as-is).
- Not a replacement for real auth — purely a dev/testing convenience.

## 3. The gate — server-only, runtime, fail-closed *(revised after round-1 review)*

> **Round-1 review changed this section.** The original gate read the **literal**
> `process.env.NEXT_PUBLIC_SUPABASE_URL`. Two adversarial reviewers split on whether that
> literal is build-time-inlined (frozen) or request-time — see
> `docs/reviews/plan-dev-login-round1-adjudication.md`. Rather than depend on that subtle
> Next.js semantics, the gate now uses a **server-only flag** that is safe under either
> reading.

The gate is two required conditions, both evaluated **server-side at request time**,
**fail-closed**:

```
dev-login enabled  ⇔  process.env.DEV_LOGIN_ENABLED === 'true'          // primary, server-only
                       AND isLocalSupabaseUrl(getSupabaseEnv().url)      // defense-in-depth, runtime
```

**Primary signal — `DEV_LOGIN_ENABLED` (server-only, fail-closed).**
- **Not** a `NEXT_PUBLIC_*` var → never inlined into any bundle → read from runtime
  `process.env` on the server, unambiguously. (Resolves the reviewers' inlining split: the
  build-freeze question simply does not apply to a non-public var.)
- **Fail-closed:** absent / anything other than the exact string `'true'` → disabled. A
  runtime **flag that defaults closed** cannot fail *open* on a mis-set env — opening it in
  prod requires *deliberately* setting `DEV_LOGIN_ENABLED=true`, which no deploy does.
- **Set only in local `.env.local`.** Prod (fly secrets / build args) never sets it.

**Defense-in-depth — `isLocalSupabaseUrl` on the RUNTIME url:**

```ts
// lib/supabase/is-local-url.ts
export function isLocalSupabaseUrl(url: string | undefined | null): boolean {
  if (!url) return false;                    // fail-closed: absent → not local
  try {
    const host = new URL(url).hostname;
    return host === 'localhost' || host === '127.0.0.1';
  } catch {
    return false;                            // fail-closed: malformed → not local
  }
}
```

Read the URL via **computed-key access** `process.env['NEXT_PUBLIC_SUPABASE_URL']` — a
genuine **runtime** read (Next's DefinePlugin only substitutes the *literal*
`process.env.NEXT_PUBLIC_SUPABASE_URL`; bracket access is not inlined). Do **NOT** use
`getSupabaseEnv()` here — its `required()` **throws** on a missing var, which would break
fail-closed (throw instead of 404); computed-key access returns `undefined` →
`isLocalSupabaseUrl(undefined)` → `false`, the correct fail-closed result. Even if
`DEV_LOGIN_ENABLED=true` ever leaked to prod, the runtime URL there is the hosted
`…supabase.co` value (or unset) → this second condition closes the gate anyway.

**Request-time evaluation.** The route sets `export const dynamic = 'force-dynamic'` so the
gate is evaluated per request and never prerendered with a frozen decision. In prod the flag
is absent → 404 regardless.

- **Why not `NODE_ENV`:** a local `next build && next start` runs with
  `NODE_ENV=production` while still pointed at the local DB — a `NODE_ENV !== 'production'`
  gate would wrongly disable dev-login there. The flag + runtime-URL pair is correct in that
  case (flag set locally, URL local) and closed in hosted prod (flag absent).

## 4. Route: `/dev-login` (server-gated)

A dedicated route whose **server component** is the gate:

```
// app/dev-login/page.tsx
export const dynamic = 'force-dynamic';   // evaluate the gate per request, never prerender

GET /dev-login
  server component:
    if (!devLoginEnabled()) notFound();   // 404 unless flag set AND runtime URL local
    return <DevLoginForm />;              // local only
```

where the gate lives in a small server helper (single decision point, §3):

```ts
// lib/supabase/dev-login.ts  (server-only)
import { isLocalSupabaseUrl } from '@/lib/supabase/is-local-url';

export function devLoginEnabled(): boolean {
  if (process.env.DEV_LOGIN_ENABLED !== 'true') return false;            // fail-closed primary (runtime)
  return isLocalSupabaseUrl(process.env['NEXT_PUBLIC_SUPABASE_URL']);    // computed-key → genuine runtime read
}
```

> Note: `DEV_LOGIN_ENABLED` (server-only, not `NEXT_PUBLIC_*`) is a true runtime read and the
> primary gate — absent in prod → `false` short-circuits before the URL is consulted. The URL
> uses **bracket access** so it too is a runtime read (the *literal* form would be
> build-inlined). `getSupabaseEnv()` is deliberately NOT used — it throws on a missing var,
> which would fail-open-to-500 instead of fail-closed-to-404.

- The gate runs on the **server**, which the browser cannot influence. In production the
  page returns **404** and the form is never produced — "absent," not merely "hidden."
- `/login` (the real Google login) is untouched.
- Rationale for a dedicated route over a client-conditional form on `/login`: a
  client-gated form **ships to every prod browser** and relies on client JS to hide it
  ("present but hidden"); the server gate makes it genuinely absent. See §9.

**Middleware routing (required):** `lib/supabase/route-categories.ts` classifies any
route not in its public/anon lists as `authenticated`, and the middleware redirects an
unauthenticated page request to `/login` (`middleware.ts:54`) **before** the page
component runs. So `/dev-login` must be added to `PUBLIC_EXACT` — otherwise a logged-out
developer is bounced to `/login` and never reaches the form. This is safe in prod:
`classifyRoute` is pure (env-independent), so `/dev-login` is "public" everywhere, but the
**server gate still 404s it in prod** — public + 404 = 404. Public here only means "the
middleware won't force a login redirect," not "renders."

## 5. Form behavior (`DevLoginForm`, client component)

Mirrors the existing Google button's client pattern (`app/login/page.tsx`):

- Fields: `email`, `password`.
- On submit: `createClient().auth.signInWithPassword({ email, password })` on the browser
  client. The `@supabase/ssr` browser client writes the session cookie **client-side** via
  its cookie adapter. (Note — this differs from `signInWithOAuth`, which does *not* write a
  cookie directly: it redirects to Google and the cookie is written **server-side** by
  `app/auth/callback/route.ts` via `exchangeCodeForSession`. Do not describe the two as the
  same mechanism.)
- Success → **hard navigation** `window.location.assign('/')` (not `router.replace`). A full
  page load guarantees the middleware/server read the freshly-written cookie on the next
  request — matching the full round-trip the OAuth callback flow gets. (M1: a soft RSC nav
  might not surface the just-set cookie to middleware.)
- Error → render `error.message` inline (`role="alert"`), same as the Google button.
- A `pending`/disabled state on the submit button prevents double-submit while the request
  is in flight.
- Visual: minimal, consistent with the existing login page styling; clearly labelled
  "Local dev sign-in" so it is never mistaken for the real login.

## 6. Discoverability — conditional link on `/login`

Add a small "Local dev sign-in" link on `/login`, rendered only when
`isLocalSupabaseUrl(process.env.NEXT_PUBLIC_SUPABASE_URL)` is true (this value is a
`NEXT_PUBLIC_*` var, readable client-side).

- **Why safe:** a link is not a login box. If the client check ever misfired in prod, the
  worst case is a link to a **404** (the server gate still holds) — harmless. The real
  guarantee remains the server gate on `/dev-login`, not this link.

## 7. Testing (TDD — guard tests written first)

All suites that read `NEXT_PUBLIC_SUPABASE_URL` / `DEV_LOGIN_ENABLED` must **set/delete
those vars in `beforeEach`** (not merely restore in `afterEach`), so no test depends on
ambient env (M3 — `next/jest` leaves `NEXT_PUBLIC_SUPABASE_URL` unset under `NODE_ENV=test`).

| # | Test | Asserts | Layer |
|---|------|---------|-------|
| 1 | **Prod gate — flag absent (critical)** | `DEV_LOGIN_ENABLED` unset → `/dev-login` calls `notFound()` (404), *regardless of URL*. This is the production state (prod never sets the flag). **Mutation-checked:** delete the flag check → red. | route/server |
| 1b | **Prod gate — flag set but URL non-local (defense-in-depth)** | `DEV_LOGIN_ENABLED='true'` + `NEXT_PUBLIC_SUPABASE_URL='https://x.supabase.co'` → `notFound()` (404). **Mutation-checked:** delete the URL check → red. | route/server |
| 2 | Local gate | `DEV_LOGIN_ENABLED='true'` + `http://127.0.0.1:54321` → renders `DevLoginForm` (no 404). | route/server |
| 3 | `isLocalSupabaseUrl` table | `localhost`, `127.0.0.1` (any scheme/port) → `true`; `x.supabase.co`, `127.0.0.1.evil.com`, `''`, `undefined`, `null`, `'not a url'` → `false`. | unit |
| 3b | `devLoginEnabled()` table | flag unset → `false`; flag `'true'`+local URL → `true`; flag `'true'`+prod URL → `false`; flag `'1'`/`'yes'` (not exact `'true'`) → `false`. | unit |
| 4 | Form submit | entering email+password and submitting calls `signInWithPassword({ email, password })` with the entered values (mocked client). | component |
| 5 | Form error | `signInWithPassword` returns an error → message shown in `role="alert"`; no navigation. | component |
| 6 | `/login` link | link present when URL local; absent when URL prod-like. | component |
| 7 | Middleware classification | `classifyRoute('/dev-login')` → `'public'`; `classifyRoute('/dev-login-secrets')` → `'authenticated'`; unauth `/dev-login` NOT redirected. **Mutation-checked:** remove `/dev-login` from `PUBLIC_EXACT` → red. | unit + middleware |
| 8 | **Deploy assertion (H2)** | a repo-level check that the production build/deploy config does **not** set `DEV_LOGIN_ENABLED` (grep `fly.toml`/`Dockerfile`/CI for a truthy value → must be absent). Turns "trust the deploy" into a regression guard. | repo/CI |

Tests #1 and #1b are the invariant guards; both must survive mutation. Test #8 guards the
**in-repo config paths** for the flag (fly.toml / Dockerfile / CI) — it does **not** catch a
runtime `fly secrets set DEV_LOGIN_ENABLED=true` (a secret in no repo file). That runtime
path is caught by (a) the URL defense-in-depth in the gate and (b) a **required post-deploy
smoke check** (`curl <prod>/dev-login` → 404) in `docs/deploy.md` — the guard at the layer
that actually regresses.

## 8. Files touched

| File | Change |
|------|--------|
| `lib/supabase/is-local-url.ts` | **new** — `isLocalSupabaseUrl` pure helper |
| `lib/supabase/dev-login.ts` | **new** — `devLoginEnabled()` server gate (flag + runtime URL) |
| `app/dev-login/page.tsx` | **new** — server-gated route (`force-dynamic`; `notFound()` unless `devLoginEnabled()`) |
| `components/DevLoginForm.tsx` | **new** — client form calling `signInWithPassword`, hard-nav on success |
| `app/login/page.tsx` | **edit** — conditional "Local dev sign-in" link |
| `lib/supabase/route-categories.ts` | **edit** — add `/dev-login` to `PUBLIC_EXACT` |
| `.env.local` (gitignored) + `.env.example` | **edit** — add `DEV_LOGIN_ENABLED=true` locally; document it (never set in prod) |
| tests | **new/edit** — §7 tests #1–#8 |

- **New env var:** `DEV_LOGIN_ENABLED` (server-only; set only in local `.env.local`).
- **No migration. No change to production auth *code*.** Layer-1 (prod Supabase Auth
  provider config) is a **console/verification** action, not a code change — see §11.

## 9. Security rationale / threat model *(rewritten after round-1 review — B1)*

**Key correction from review:** the UI gate is **not** the control that makes
email/password auth "impossible to *use*" in production. `signInWithPassword` posts
**directly** to the Supabase Auth endpoint (`/auth/v1/token?grant_type=password`) using the
anon key + Supabase URL that **already ship in every production bundle**
(`lib/supabase/client.ts`, `fly.toml`). Whether `/dev-login` 404s has **zero** effect on
that endpoint's reachability. So there are two distinct layers, and they must not be
conflated:

- **Layer 1 — the authorization control (what actually enforces "impossible to use"):** the
  **production Supabase project's Auth configuration** — email/password sign-in **disabled**
  (or: the email provider off / no password-capable users). This is what stops a direct API
  call to the prod Auth endpoint from succeeding, *independent of this feature*. This feature
  does not create the direct-API exposure (it exists for any Supabase project with the email
  provider on), but shipping it without this being true would be false security. **§11 adds a
  verification task.**
- **Layer 2 — the UI gate (discoverability / defense-in-depth, what this feature adds):** the
  `/dev-login` route is **absent in prod** — `devLoginEnabled()` is `false` because
  `DEV_LOGIN_ENABLED` is never set there → `notFound()`. This keeps a login *form* from being
  discoverable/served in prod. It is a convenience-and-hygiene control, **not** the
  authorization boundary.

**Gate properties (Layer 2):**
- **Single server-side decision point** — `devLoginEnabled()`, fail-closed, unit- and
  mutation-tested (§7 tests #1, #3, #8).
- **Fail-closed under both build- and run-time semantics** — the primary signal is a
  server-only flag that defaults closed; it cannot be build-inlined (not `NEXT_PUBLIC_*`) nor
  fail open on a mis-set runtime env (only the exact string `'true'` opens it).
- **Layered** — independent of middleware and of `STORAGE_BACKEND`; even if prod ran with
  those in unexpected states, the flag-absent gate still 404s.
- **Residual:** the `DevLoginForm` client chunk may exist in the build output, but with
  `/dev-login` 404ing there is no page that loads it — and Layer 1, not chunk absence, is the
  real boundary.

## 10. Resolved decisions

1. **Server-gated dedicated route** (not client-gated form on `/login`) — absent > hidden.
2. **Gate = server-only `DEV_LOGIN_ENABLED` flag AND runtime local-URL check** (revised from
   "URL host only"; not `NODE_ENV`). Sidesteps the `NEXT_PUBLIC_*` build-inlining question —
   a non-public flag can't be inlined, and defaults closed so it can't fail open. `force-dynamic`
   evaluates it per request.
3. **Fail-closed** — flag absent / not exactly `'true'` / URL non-local/malformed → 404.
4. **`signInWithPassword` writes the cookie client-side; hard-nav (`window.location.assign('/')`)
   on success** — a full round-trip so middleware sees the fresh cookie (corrected from the
   earlier "same as OAuth" claim).
5. **Conditional link on `/login`** for discoverability — safe (worst case links to a 404).
6. **No rate-limit / user-management / reset**; `pending` state to prevent double-submit — YAGNI.
7. **`/dev-login` added to `PUBLIC_EXACT`** so the middleware doesn't redirect logged-out
   devs to `/login` before the gate runs — safe because the server gate still 404s in prod.
8. **The UI gate is defense-in-depth, not the authorization boundary** — the real control for
   "impossible to use in prod" is the prod Supabase Auth provider config (§9, §11).

## 11. Layer-1 verification — production Supabase Auth config (B1)

The authorization boundary is **not** in this codebase; it is the production Supabase
project's Auth settings. Before this feature is considered done:

- **Verify** the production project (`uykwcybxqgewmbltroxf`) has **email/password sign-in
  disabled** (Auth → Providers → Email: signups off / password grant not usable), or that no
  password-capable users exist. `signInWithPassword` against prod must fail regardless of any
  UI.
- This is a **read/verify** against prod (a human-gated check; changing the setting is an
  outward-facing prod action). Record the observed state in the task's review notes.
- Rationale: the direct Auth API is reachable with the public anon key that already ships in
  prod, independent of `/dev-login`. If email/password is already disabled in prod, the
  invariant's "impossible to *use*" clause holds; the UI gate then only prevents shipping a
  discoverable form.
