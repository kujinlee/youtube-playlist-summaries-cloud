# Claude Adversarial Re-Review — Dev-Login Gate (#13) — Round 2

Reviewer: Claude (independent subagent). Revised spec + plan, vs round-1 findings.

## Round-1 verification
All six genuinely resolved (not cosmetic): **B1** (§9 Layer-1/Layer-2 split + §11/Task 7),
**H1** (server-only flag is a real design change + `force-dynamic`), **H2** (test #8 added;
old build-arg guard legitimately moot), **M1** (§5 cookie corrected + hard-nav), **M2** (§3
reworded), **M3** (Task 5 `beforeEach`). Two carry residue (M1/M2 below).

## New findings
- **Blocking:** none.
- **High:** none. Path trace: in the prod artifact the gate closes on every path — flag
  unset → `false`; even if the flag leaked via `fly secrets`, the URL literal is frozen at
  build to the hosted value (or unset at the runtime stage → `undefined`) → `isLocalSupabaseUrl`
  → `false`. No path opens `/dev-login` in prod.
- **Medium M1:** spec §3/§4 self-contradict the plan on the URL read; the "runtime read" claim
  for the literal is technically false (DefinePlugin substitutes the literal at compile time
  regardless of control flow). Not a security break (frozen → hosted → false; or computed-key →
  undefined → false). **Sharp edge:** fixing by calling `getSupabaseEnv()` would `throw` on a
  missing var → fail-open-to-500. Fix the DOCS to match the code, or use bracket access; warn
  against `getSupabaseEnv()`.
- **Medium M2:** deploy test #8 (grep fly.toml/Dockerfile) gives partial assurance; `fly
  secrets`/CI/machine env leaks are unseen. Mitigated by URL defense-in-depth. Soften §7 claim;
  extend grep to CI files.
- **Medium M3:** Task 7 bogus-credential probe proves only the *disabled* provider case
  (`"Email logins are disabled"` vs `"Invalid login credentials"`); the "no password users"
  disjunct needs dashboard/admin API.
- **Low L1:** `pending`/double-submit state has no test. **Low L2:** deploy test #8 is
  green-from-first-run (documentation until mutated; plan's manual mutation step satisfies it).

## Consistency / completeness
Names/types line up across tasks; every spec requirement maps to a task; middleware/route/form
tests are non-vacuous and mutation-catching. Only internal inconsistency is M1.

## Convergence verdict
**CONVERGED** — no new Blocking/High; the three Mediums are documentation/test-completeness,
cheap to fix, none a security hole. Another full round not required. **Task 7 (verify prod
Supabase email/password disabled) stays a human gate regardless.**
