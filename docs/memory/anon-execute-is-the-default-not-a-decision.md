---
name: anon-execute-is-the-default-not-a-decision
description: "FIRES-WHEN: creating a public Postgres function, or reviewing a migration that does — Supabase grants anon EXECUTE at CREATE time (through PUBLIC), so every new public function is anon-callable unless its migration revokes; check-function-revokes.py enforces it"
metadata: 
  node_type: memory
  type: project
  originSessionId: a00a513a-4135-416e-bbf4-48c0416ca19d
  modified: 2026-08-19T17:05:44.225Z
---

**RULE: every new `public` function revokes PUBLIC in its own migration** — enforced by
`scripts/check-function-revokes.py` (backlog #54's prevention half). The platform grants EXECUTE at
CREATE time, so without the revoke a function is anon-callable and safety rests on each author
remembering an `auth.uid()` check — a convention, not a mechanism ([[a-convention-catches-what-you-read]]).
⚠ `ALTER DEFAULT PRIVILEGES` cannot fix this: measured 2026-08-28, PUBLIC's built-in EXECUTE survives it
and `anon` reaches the function THROUGH PUBLIC (the script's docstring has the table).

**Why:** a grant is not an outcome and a proxy is not a proof — see the measurements below.

## History — backlog #30 and #33 measured against PRODUCTION 2026-08-19
(`claude_ro`, read-only, `docker postgres:16`, SQL in a file.) Both claims TRUE, both BOUNDED.

**#30 — `TRUNCATE` on the money tables:** `has_table_privilege` is **true** for `anon` and
`authenticated` on all five (`ledger_audit`, `spend_ledger`, `serve_owner_budget`, `serve_model_charge`,
`guardrail_config`). Bounded per `0025_settle_is_observable.sql:36`: PostgREST exposes no TRUNCATE verb,
so exploiting it needs a direct Postgres session; RLS never gated TRUNCATE. ⚠ The row's *"SELECT/INSERT
are correctly denied (false)"* was wrong — the SELECT grant exists; the effect is nil because all five
have `rls_on = rls_forced = true` with **0 policies**.

**#33 — `anon` EXECUTE on 26 of 30 `public` functions:** no exploitable path found. 16 of 26 are
SECURITY INVOKER (RLS applies, 0 policies). 10 are SECURITY DEFINER; 8 check `auth.uid()` (NULL for
anon); the 2 without were read in full and are benign (`handle_new_user` returns `trigger`;
`reserve_serve_model_meta` only reads `pg_proc`). ⚠ *"references `auth.uid()`"* is a PROXY for
*"enforces ownership"* — eight bodies were not read line by line.

At the time the default-revoke ratchet was only proposed; it has since been filed (#54) and built.

Related: [[rls-denial-is-indistinguishable-from-absence]], [[hardcode-only-what-fails-loudly]],
[[feedback-agree-before-filing]].
