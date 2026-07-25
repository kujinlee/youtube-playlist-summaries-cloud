# Dev-Login (#13) — Round 1 Review Adjudication

Two independent adversarial reviews of the spec+plan: `plan-dev-login-codex.md` (Codex,
gpt-5.5) and `plan-dev-login-claude.md` (Claude). They **disagreed on the central point**,
which per `docs/dev-process.md` ("Reviewer disagreement is the signal") is adjudicated here
by reading the mechanism — not by vote or by trusting either verdict.

## The disagreement

The original gate read the **literal** `process.env.NEXT_PUBLIC_SUPABASE_URL` in a server
component.

- **Codex (Blocking):** `NEXT_PUBLIC_*` literals are **inlined at build** and frozen; a
  build made with a local URL would carry an open `/dev-login` into prod → gate unreliable.
  Proposed: read runtime server env + `force-dynamic`.
- **Claude (High, opposite framing):** that same inlining makes the prod page a **build-time
  constant 404**, *immune to runtime tampering* — a **feature**. Warned that switching to a
  runtime computed-key read makes the gate **runtime-tamperable** (a mis-set prod env could
  fail it **open**). The real gaps are test fidelity (tests exercise a runtime path prod
  never uses) and the threat model.

Both are correct within their frame. Codex is right that a build made with a local URL leaks
(the `fly.toml` build-arg is the single point of truth). Claude is right that, given the
real deploy config, the literal is a frozen 404 and that a naive runtime switch fails open.

## Adjudication → decision

**Sidestep the NEXT_PUBLIC inlining question entirely by gating on a server-only,
fail-closed flag.** New gate:

```
dev-login enabled  ⇔  process.env.DEV_LOGIN_ENABLED === 'true'
                       AND isLocalSupabaseUrl(<runtime Supabase URL>)   // defense-in-depth
```

Why this resolves *both* reviewers:
- `DEV_LOGIN_ENABLED` is **not** a `NEXT_PUBLIC_*` var → never inlined → Codex's
  "build-frozen/unreliable" concern does not apply.
- It is **fail-closed**: absent / anything-but-`'true'` → disabled. So Claude's "runtime read
  fails **open**" concern does not apply either — opening it in prod requires *deliberately*
  setting `DEV_LOGIN_ENABLED=true`, which no deploy does. A runtime **flag that defaults
  closed** is safe to evaluate at runtime, unlike a runtime **URL** that could be mis-set.
- The route adds `export const dynamic = 'force-dynamic'` so the gate is evaluated
  per-request (never prerendered with a frozen decision).
- The runtime local-URL check (via the computed-key path, like `lib/supabase/env.ts`) is a
  second required condition: even if `DEV_LOGIN_ENABLED=true` leaked to prod, the hosted URL
  still closes the gate.

This design is safe under **both** reviewers' readings of Next.js semantics — chosen
precisely so the outcome does not depend on adjudicating the inlining subtlety.

## Findings accepted (both reviewers) and their dispositions

| # | Finding | Disposition |
|---|---------|-------------|
| **B1** (both) | UI gate ≠ the real control; `signInWithPassword` hits the prod Auth API directly with the shipped anon key. Spec §9 claims false security. | **Accept.** Rewrite §9: UI gate = discoverability/defense-in-depth; the authorization control is the **prod Supabase Auth provider config** (email/password disabled + no password users). Add a task to **verify** prod email/password sign-in is disabled (human-gated prod check). |
| **H1** (Codex/Claude split) | Gate mechanism mis-described / inlining hazard. | **Resolved by the flag design above** — gate is now unambiguously server-only + runtime + fail-closed. Spec §3/§4 rewritten to match. |
| **H2** (both) | No guard at the layer that regresses (a build/deploy that would open the gate). | **Accept.** Add: (a) unit test that `DEV_LOGIN_ENABLED` absent → 404 (matches prod, since prod never sets it); (b) a CI/deploy assertion that the prod image does not set `DEV_LOGIN_ENABLED`. Turn the finding into an assertion per dev-process. |
| **M1** (Claude) | §5 cookie analogy wrong; soft-nav propagation unverified. | **Accept.** Correct §5; use hard nav `window.location.assign('/')` on success (matches OAuth's full round-trip). |
| **M2** (Claude) | §3 "local prod-build" benefit oversold. | **Accept.** Reword §3 (moot now that gate is a flag, not the URL alone). |
| **M3** (Claude) | Test-env order fragility. | **Accept.** Set/delete env in `beforeEach` in the affected suites. |
| **M-Codex** | Explicit prod kill switch / deploy assertion. | **Accept** — the `DEV_LOGIN_ENABLED` fail-closed flag *is* the kill switch; H2 assertion covers deploy. |
| **L1/L2** (Claude, positive) | prefix-safety + layered gate hold. | Note as verified; state layering in spec. |
| **L4** (Claude) | no double-submit guard. | Accept as YAGNI; add a `pending` state to avoid re-flag. |

## Re-review required

The fixes are a **design change** (gate mechanism) + threat-model rewrite → non-trivial →
a full re-review round (Codex + Claude) on the revised spec+plan is required before the plan
gate is satisfied (per dev-process "Iterative Re-Review").
