# Codex Adversarial Review — Stage 1B Implementation Plan

**Reviewer:** Codex (frontier), fresh session
**Date:** 2026-07-02
**Target:** `docs/superpowers/plans/2026-07-02-stage-1b-auth-rls-schema.md`
**Context:** `docs/superpowers/specs/2026-07-02-stage-1b-auth-rls-schema-design.md`
**Verdict:** 2 Blocking + 7 High + 4 Medium + 1 Low.

---

## Blocking

- **B1 — Google OAuth E2E deferred, but spec §8 makes it a 1B success criterion.** Spec §§4/8 require "Google and anonymous sign-in both yield a session and profiles row"; the plan defers Google E2E to deploy. → Fix by adding a concrete 1B verification for the Google/OAuth provisioning + callback path, or amend the approved spec to scope real-Google verification to deploy. **[Decision surfaced to user — see resolution.]**
- **B2 — Anonymous auth likely fails locally: `signInAnonymously()` requires `config.toml` opt-in.** Plan runs `supabase init` but never enables anonymous sign-ins. Tasks 1/7/9 depend on `anonSession()`. → Fix: set `[auth] enable_anonymous_sign_ins = true` (+ local email-confirm settings) in `supabase/config.toml`; smoke-test `anonSession()` after `db reset`.

## High

- **H1 — Anon-allowed auto-provision not implemented.** Spec §4: anon-allowed paths "auto-provision an anonymous session on first use." Task 10 only classifies `/try` and redirects authenticated routes. → Add middleware logic + test that mints an anonymous session on first visit to an anon-allowed route.
- **H2 — Confinement scan under-scoped.** Defaults to `app/**` only; `middleware.ts` is user-facing/edge-executed and outside that tree. → Scan all Next entrypoints: `app/**`, `middleware.ts`, route handlers, server components, any future `pages/**`.
- **H3 — Import-graph walker misses side-effect imports.** Regex matches only `... from '...'` and literal `import('...')`; it misses `import '@/lib/supabase/service'`. → Extend to side-effect imports (and re-exports/barrels/dynamic); add tests. Prefer the TS compiler API.
- **H4 — Runtime service guard insufficient for Edge/RSC.** Only checks `typeof window`; test only simulates browser. → Rely on the (now-broadened) entrypoint confinement scan as the build-time proof that `service.ts` is unreachable from middleware/RSC/route handlers; keep the runtime guard as defense-in-depth.
- **H5 — RLS isolation omits `profiles`.** Spec §7 requires isolation on `profiles`/`playlists`/`videos` each. → Add a B-scoped `profiles.select().eq('id', A.userId)` returning 0 rows.
- **H6 — Mutation semantics incomplete.** Spec §7 needs update AND delete on invisible rows + with-check violations on visible rows. Task 8 only updates videos + spoofed insert. → Add delete-on-invisible (0 rows) and an owner/id-changing update on an own visible row that must error.
- **H7 — `reorder_videos` callable by `PUBLIC`, no owner check.** Relies only on update-RLS no-op. → Revoke default execute; grant to `authenticated`; check `auth.uid()` owns `p_playlist_id` (or `auth.role() = 'service_role'`) before updating.

## Medium

- **M1 — Forced-RLS test checks `relforcerowsecurity` but not `relrowsecurity`.** → Assert both true for every owned table.
- **M2 — No negative test that `anon`/`authenticated` cannot execute `exec_sql`.** → Add integration assertions that anon-key and user-JWT clients get permission errors.
- **M3 — `principal.ts` JSDoc update has no task.** → Already committed in the spec-v3 work (`lib/storage/principal.ts` JSDoc already says "index selector; cloud = the playlist key"). Moot; noted for traceability.
- **M4 — OAuth callback ignores `exchangeCodeForSession` errors.** → Check the returned error; redirect to an auth-error route on failure; test the error branch.

## Low

- **L1 — Policy-presence test checks names only, not `cmd`/`qual`/`with_check`.** Behavior tests (Task 8) already prove the policies function; strengthen the presence assertion to include `cmd` + `with_check` for defense-in-depth.

---

## Resolution (applied to plan v2)

All High + Medium + Low fixed in the plan. **B2** fixed (config.toml auth opt-in task). **B1** surfaced to the user as a spec-criterion decision: real Google OAuth cannot be exercised on the local stack without Google credentials; the provisioning trigger test (Task 4) already proves an OAuth-style `auth.users` insert yields a `profiles` row, and a mocked callback unit test proves the code-exchange path — the live Google redirect remains a documented deploy-time manual check unless the user wants the spec criterion amended.
