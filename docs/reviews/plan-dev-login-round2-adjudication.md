# Dev-Login (#13) — Round 2 Re-Review Adjudication + Convergence

Round-2 re-review of the revised spec+plan: `plan-dev-login-codex-v2.md` (Codex, gpt-5.5)
and the Claude re-review (below-summarised). The two **split on convergence** — adjudicated
here by reading the mechanism (dev-process "reviewer disagreement is the signal"; never
resolve a split by trusting a CONVERGED verdict).

## The split

| | Codex v2 | Claude v2 |
|---|---|---|
| URL read is a build-inlined literal, not the "runtime read" the spec claims | **High** | **Medium** (doc accuracy) |
| Deploy grep misses the runtime `fly secrets` leak path | **High** | **Medium** (test completeness) |
| Task 7 bogus-cred probe can't prove "no users" | Medium | Medium |
| Verdict | **NOT converged** | **CONVERGED** (no new Blocking/High) |

Both round-1 findings verified genuinely fixed by both reviewers (B1, H1, H2, M1, M2, M3) —
the disagreement is only about the severity of two residuals.

## Adjudication (by mechanism, not vote)

**URL-literal finding → Medium, not High.** The concern is real (Next's DefinePlugin inlines
the *literal* `process.env.NEXT_PUBLIC_SUPABASE_URL` at build; being behind a conditional
does not make it runtime — `force-dynamic` governs prerender, not substitution). **But it is
a documentation-accuracy issue, not a security regression:** the `DEV_LOGIN_ENABLED` flag is
the primary gate and short-circuits `false` in prod *before* the URL is read; and in every
traced scenario the URL resolves non-local in prod (frozen hosted value, or unset at the
runtime stage → `undefined`) → gate closed. **Decisive tell that Codex over-ranked it:
Codex's proposed fix (`getSupabaseEnv()`) is wrong** — that helper `throw`s on a missing var
(`lib/supabase/env.ts` `required()`), converting fail-closed-404 into fail-to-500. Claude
caught this. A finding whose proposed remedy introduces a bug is not a clean High.
- **Resolution (satisfies both):** read `process.env['NEXT_PUBLIC_SUPABASE_URL']` — bracket
  access is a genuine runtime read (Codex's ask) AND undefined-safe / no throw (Claude's
  requirement). Spec §3/§4 + this doc corrected; `getSupabaseEnv()` explicitly warned against.
  (Supersedes round-1 adjudication's imprecise "via `getSupabaseEnv()`" phrasing.)

**Deploy-grep finding → Medium, not High.** Correct that grepping repo files can't catch
`fly secrets set DEV_LOGIN_ENABLED=true`. But it is not a hole: the URL defense-in-depth
already closes the gate even if the flag leaked, and the grep still has value as a
repo-drift guard. The genuine runtime guard is a **post-deploy smoke check** (`curl
<prod>/dev-login` → 404), which is the layer that actually regresses.
- **Resolution:** keep the grep, extend it to `.github/workflows/*`, add the post-deploy
  smoke check to `docs/deploy.md` + DoD, and soften the spec's overstatement (§7).

**Task 7 probe → Medium (agreed).** The bogus-credential probe proves only the *disabled*
disjunct (distinguishable error `"Email logins are disabled"` vs `"Invalid login
credentials"`); the "no password-capable users" disjunct needs the dashboard/admin API.
- **Resolution:** Task 7 reworded accordingly.

**Lows:** `pending`-state test added (L1); `beforeEach` env reset added to Task 4 suites
(Codex Low / L2).

## Convergence verdict

**CONVERGED.** Adjudicated: no genuine new Blocking/High — the two Codex "High"s are a
documentation-accuracy and a test-completeness issue, both mitigated by the fail-closed flag
and neither opening any prod path (independently confirmed by Claude's path trace: flag unset
→ `false`; flag leaked → frozen/unset hosted URL → `false`). Per dev-process "diminishing
returns," a full re-review round returning no new Blocking/High **is** the gate. The
Medium/Low fixes above are applied; they are line-level doc/test changes, not a design change,
so they do not require a further full round.

**Standing human gate (independent of convergence):** Task 7 — verify prod Supabase
email/password is disabled — is the real authorization boundary and must be confirmed against
the live prod project before the feature is *done*.
