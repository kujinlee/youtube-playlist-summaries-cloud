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

## 3. The gate — `isLocalSupabaseUrl` (the security core)

The entire security of this feature collapses to one **pure function**, evaluated
**server-side**, **fail-closed**:

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

**Signal choice — the Supabase URL host, and only that.** Enable dev-login **iff** the
host of `NEXT_PUBLIC_SUPABASE_URL` is `localhost` or `127.0.0.1`.

- **Why not `NODE_ENV`:** a local `next build && next start` runs with
  `NODE_ENV=production` while still pointed at the local DB — a `NODE_ENV !== 'production'`
  gate would wrongly disable dev-login for local prod-builds. Hosted prod always uses the
  `…supabase.co` URL, so the URL host is the signal that actually correlates with "pointed
  at local data." One correct signal beats two that conflict.
- **Fail-closed:** every non-local / absent / malformed input returns `false` → 404. A bug
  fails toward "no dev-login," never toward "exposed in prod."

## 4. Route: `/dev-login` (server-gated)

A dedicated route whose **server component** is the gate:

```
GET /dev-login
  server component (app/dev-login/page.tsx):
    if (!isLocalSupabaseUrl(process.env.NEXT_PUBLIC_SUPABASE_URL)) notFound();  // 404 in prod
    return <DevLoginForm />;                                                    // local only
```

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
  client — which **auto-writes the session cookie** (same mechanism `signInWithOAuth`
  relies on). No bespoke cookie handling.
- Success → redirect to `/`.
- Error → render `error.message` inline (`role="alert"`), same as the Google button.
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

| # | Test | Asserts | Layer |
|---|------|---------|-------|
| 1 | **Prod gate (critical)** | prod-like `NEXT_PUBLIC_SUPABASE_URL` (e.g. `https://x.supabase.co`) → `/dev-login` server component calls `notFound()` (404). **Mutation-checked:** delete the gate line → this test MUST go red. | route/server |
| 2 | Local gate | `http://127.0.0.1:54321` → server component renders `DevLoginForm` (no 404). | route/server |
| 3 | `isLocalSupabaseUrl` table | `localhost`, `127.0.0.1` (any scheme/port) → `true`; `x.supabase.co`, `''`, `undefined`, `null`, `'not a url'` → `false`. | unit |
| 4 | Form submit | entering email+password and submitting calls `signInWithPassword({ email, password })` with the entered values (mocked client). | component |
| 5 | Form error | `signInWithPassword` returns an error → message shown in `role="alert"`. | component |
| 6 | `/login` link | link present when URL local; absent when URL prod-like. | component |
| 7 | Middleware classification | `classifyRoute('/dev-login')` → `'public'`; an unauthenticated request to `/dev-login` is NOT redirected to `/login`. **Mutation-checked:** remove `/dev-login` from `PUBLIC_EXACT` → this test MUST go red. | unit + middleware |

Test #1 is the invariant guard — it is the one that must survive mutation (remove gate →
red) per `docs/dev-process.md`.

## 8. Files touched

| File | Change |
|------|--------|
| `lib/supabase/is-local-url.ts` | **new** — `isLocalSupabaseUrl` pure helper |
| `app/dev-login/page.tsx` | **new** — server-gated route (`notFound()` unless local) |
| `components/DevLoginForm.tsx` (or co-located) | **new** — client form calling `signInWithPassword` |
| `app/login/page.tsx` | **edit** — conditional "Local dev sign-in" link |
| `lib/supabase/route-categories.ts` | **edit** — add `/dev-login` to `PUBLIC_EXACT` (else middleware redirects unauth users to `/login` before the gate runs) |
| `lib/supabase/__tests__/is-local-url.test.ts` | **new** — unit table (test #3) |
| route + component tests | **new** — tests #1, #2, #4, #5, #6 |

No migration. No change to production auth. No new env vars (reuses
`NEXT_PUBLIC_SUPABASE_URL`).

## 9. Security rationale / threat model

- **Threat:** an email/password login surface appearing in production would be an
  additional, un-OAuth'd way in.
- **Mitigation:** the surface is **server-gated** on a local-only signal, fail-closed, so
  in production the route 404s and the form is never produced. "Absent" beats "hidden."
- **Single decision point:** the gate is one pure, side-effect-free function evaluated on
  the server — exhaustively unit-tested and mutation-tested (test #1, #3).
- **Blast radius if the gate failed open:** an attacker would still need valid credentials
  for a user that exists in the **production** Supabase; the test user
  (`sync-test@example.com`) exists only in the local DB. But we do not rely on that — the
  gate is the control.
- **Residual:** the `DevLoginForm` client component's JS chunk may exist in the build
  output, but with `/dev-login` returning 404 in prod there is no page that loads it. The
  server gate — not chunk absence — is the guarantee.

## 10. Resolved decisions

1. **Server-gated dedicated route** (not client-gated form on `/login`) — absent > hidden.
2. **Gate on Supabase URL host only** (not `NODE_ENV`) — correct for local prod-builds.
3. **Fail-closed** — absent/malformed/non-local → 404.
4. **Reuse the browser client's `signInWithPassword` + auto-cookie** — no new auth plumbing.
5. **Conditional link on `/login`** for discoverability — safe (worst case links to a 404).
6. **No rate-limit / user-management / reset** — YAGNI for a local-only affordance.
7. **`/dev-login` added to `PUBLIC_EXACT`** so the middleware doesn't redirect logged-out
   devs to `/login` before the gate runs — safe because the server gate still 404s it in
   prod (public + 404 = 404).
