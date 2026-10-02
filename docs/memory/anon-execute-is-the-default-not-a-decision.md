---
name: anon-execute-is-the-default-not-a-decision
description: "FIRES-WHEN: creating a public Postgres function, or reviewing a migration that does — MEASURED in prod 2026-08-19 — backlog #30 and #33 both CONFIRMED and both bounded; the real finding is that Supabase grants anon EXECUTE at CREATE time, so every future public function is anon-callable unless someone remembers"
metadata: 
  node_type: memory
  type: project
  originSessionId: a00a513a-4135-416e-bbf4-48c0416ca19d
  modified: 2026-08-19T17:05:44.225Z
---

**Backlog #30 and #33 verified against PRODUCTION 2026-08-19** (`claude_ro` on
`uykwcybxqgewmbltroxf`, read-only, `docker postgres:16`, SQL in a file). Both claims are TRUE and
both are BOUNDED. Recorded here because these are live-system facts, not derivable from the repo,
and re-deriving them costs a docker pull and four queries.

## #30 — `TRUNCATE` on the money tables

`has_table_privilege` is **true** for BOTH `anon` and `authenticated`, on all five:
`ledger_audit`, `spend_ledger`, `serve_owner_budget`, `serve_model_charge`, `guardrail_config`.

**Bounded, and the bound was already written down** — `0025_settle_is_observable.sql:36`: not
reachable through PostgREST, which exposes **no TRUNCATE verb**. Exploiting it needs a direct
Postgres session. RLS is irrelevant either way: it never gated TRUNCATE.

⚠ **One detail in the filed row is wrong.** It says *"SELECT/INSERT are correctly denied (false)"*.
`has_table_privilege(anon, …, 'select')` is **true** — the GRANT exists. The *effect* is nil because
all five have `rls_on = rls_forced = true` with **0 policies**, so a read returns 0 rows. Grant ≠
outcome; the row conflates them. Conclusion still holds.

## #33 — `anon` EXECUTE on 26 of 30 `public` functions

Confirmed exactly. **No exploitable path found**, and the split is what matters:

- **16 of 26 are SECURITY INVOKER** → RLS applies with `anon`'s rights → nothing, given 0 policies.
- **10 are SECURITY DEFINER** (bypass RLS). **8 of those check `auth.uid()`**, which is NULL for anon.
- The 2 without any `auth.uid()` reference were read in full and are benign: `handle_new_user`
  returns `trigger` (PostgREST cannot invoke it), and `reserve_serve_model_meta` returns
  `TABLE(secdef boolean, cfg text[])` — its whole body reads `pg_proc` to report whether
  `reserve_serve_model` is DEFINER. Introspection, no writes, no money.

**Bound honestly:** *"references `auth.uid()`"* is a PROXY for *"enforces ownership"*, not a proof.
Eight bodies were not read line by line.

## ⭐ The finding worth acting on — the DEFAULT is wrong

The risk is not any function that exists today. **Supabase grants EXECUTE to `anon` at CREATE time**,
so **every future `public` function is anon-callable unless someone remembers to revoke.** Safety
currently rests on each author independently adding an `auth.uid()` check — 8 for 8 so far, which is
a convention, not a mechanism.

Same shape as [[a-convention-catches-what-you-read]]: a rule that works only when read. The durable
fix is a **default revoke plus a ratchet** that fails when a `public` function is anon-executable and
not on an allow-list. **NOT FILED** — proposed to the user, awaiting their call per
[[feedback-agree-before-filing]].

Related: [[rls-denial-is-indistinguishable-from-absence]], [[hardcode-only-what-fails-loudly]].
