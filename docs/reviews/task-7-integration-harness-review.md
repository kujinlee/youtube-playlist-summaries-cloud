# Task 7 Review — Integration test harness (stack-gated)

**Reviewer:** Claude (sonnet), fresh subagent (task reviewer, SDD)
**Commit:** c22b3c0 | **Verdict:** SPEC ✅ / QUALITY approved
**Note:** Docker down on the authoring machine — reviewed as CODE; integration `db reset`/`test:integration` green deferred to the user's stack.

## Spec compliance — all 5 binding constraints PASS
1. **`exec_sql` security:** `security definer` + `set search_path = ''`; `revoke all from public, anon, authenticated`; `grant execute to service_role` ONLY (not broader). Deliberate service_role-gated escape hatch.
2. **`setup.ts` fail-fast:** module-top throw if stack env absent; referenced only in `jest.integration.config.ts` `setupFiles`, never in the default `jest.config.ts` — the throw can't fire during `npm test`.
3. **`helpers/clients.ts`:** `adminClient` uses service key; `newUser` → `auth.admin.createUser({email_confirm:true})`; `signInAs` returns an **anon-key + user-JWT** client (real RLS path, NOT service) — satisfies Codex M4; `anonSession` → `signInAnonymously`.
4. **`jest.integration.config.ts`:** testMatch is only `tests/integration/**`; default config unmodified.
5. **`exec-sql-guard.test.ts`:** asserts BOTH user-JWT and anon clients error on `exec_sql`.

Additive only; default suite 1505 green with `tests/integration/**` confirmed excluded; tsc clean.

## Findings (both Minor — FIXED by controller)
1. **`setup.ts` guard omitted `NEXT_PUBLIC_SUPABASE_ANON_KEY`** (needed by `signInAs`/`anonSession`) → a hand-edited `.env.test.local` with a blank anon key would fail deep in a test, not at setup. → **FIXED**: added to the fail-fast condition.
2. **`exec_sql` migration not idempotent** (`create function` → errors if re-run without full reset). → **FIXED**: `create or replace function`.

No Critical/Important findings.
