# Dev-Login (#13) — Whole-Branch Review Convergence

Dual whole-branch adversarial review of the implemented branch `feat/dev-login-13`:
`branch-dev-login-codex.md` (Codex, gpt-5.5) and `branch-dev-login-claude.md` (Claude).

## Verdict: CONVERGED — mergeable (no Blocking/High)

Both reviewers independently reached **Mergeable, no Blocking or High** code findings, and
both traced the fail-closed gate across every prod state (flag unset / flag=true + prod|unset|
malformed URL → 404). No prod path opens `/dev-login` or lets the form authenticate through
this code. Single gated entry point; no PUBLIC_EXACT regression; strong mutation-catching tests.

## Findings applied (post-review hardening — commit follows)

| Finding | Reviewer | Disposition |
|---|---|---|
| `force-dynamic` load-bearing but not mutation-guarded | Codex (Med) | **Applied** — added a test asserting `dynamic === 'force-dynamic'`; mutation-verified (remove export → red). |
| `dev-login.ts` server-only not mechanically enforced | Codex (Low) | **Applied** — added `import 'server-only'` (matches `service.ts`; build-time error on client import). |
| Middleware `/dev-login` test not in default `npm test` | both (Med/Low) | **Accepted as known gap** — mitigated by `classifyRoute('/dev-login')==='public'` in the default suite; middleware behavior for a public route is a pure function of classification. Pattern-consistent with `/login`. No in-repo CI workflow exists to run integration automatically (broader infra item, not dev-login-specific). |
| L1–L5 (navigate seam untested by design; dead `??` fallback; deploy-grep strictness; no `.env.example`; login-link runtime-only test) | Claude | Informational; no change (harmless / by-design). |

## Standing human gate (NOT satisfied by code)

**Task 7 — verify prod Supabase email/password sign-in is disabled.** Both reviewers stress:
the UI gate is defense-in-depth; the real "impossible to *use* in prod" boundary is the prod
Supabase Auth provider config, because `signInWithPassword` hits the prod Auth endpoint directly
with the shipped anon key regardless of the UI. This is a human-verified check (Supabase
dashboard / probe) and blocks declaring #13 *done* — though not the merge of this code.

## Verification recorded
- Default Jest suite: **2480 passed**. `tsc --noEmit`: clean.
- Integration `middleware-2a` (incl. the new `/dev-login` passthrough): passes under
  `test:integration`. (Unrelated integration suites' failures in a full serial run were proven
  environmental — DB-state pollution from in-session manual testing — `job-queue-runner` passes
  3/3 in isolation; those files are unmodified by this branch.)
