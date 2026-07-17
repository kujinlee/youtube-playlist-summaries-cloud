# Reservation Release Plan v3 — Codex Round-3 Adversarial Re-Review

**Reviewer:** Codex (gpt-5.5), independent, from coordinator.
**Artifact:** `docs/superpowers/plans/2026-07-16-reservation-release-lifecycle.md` (v3).
**Verdict:** **NOT CONVERGED** — 0 Blocking, 1 High, 1 Medium. All round-2 fixes verified genuine.

---

## Blocking
None.

## High

### R3-H1 — the integration-test snippets use the real helper API incorrectly (Tasks 1–5)
`tests/integration/helpers/clients.ts:12,22`. Real: `newUser()` → `{ user: { id }, email, password }`; `signInAs(email, password)` → `{ client, userId }`. The plan snippets used `const session = await signInAs(u)` and `u.id`, which would break every Task 1–5 test at compile/runtime before validating the money-path SQL.
**Fix (applied v3→v4):** `const u = await newUser(); const { client: session } = await signInAs(u.email, u.password);` and `u.id` → `u.user.id` throughout (matches `cancel-job-rpc.test.ts:22`). Executor-notes helper-API block added.

## Medium

### R3-M1 — behavior-16/26 "cap re-opens" is vacuous under the suite-wide 1M headroom
`clients.ts:45` pins `daily_cap_cents=1_000_000` in `ensureGuardrailHeadroom`. The behavior-26 stub asserts "a fresh enqueue admits again (cap re-opened)" but never sets a reachable cap, so the assertion can't fail.
**Fix (applied v3→v4):** behavior-26 sets `daily_cap_cents=450` locally in `try/finally`, reserves 3×150¢ to the cap, releases, asserts re-open, then restores headroom. Behavior 16 re-pointed to this test.

## Low (all round-2 fixes verified genuine)
- R2-H1 verified: `JobQueue` interface + adapter widened; `tsc --noEmit` gate. Only `SupabaseJobQueue implements JobQueue`; no other typed mock breaks.
- Claude-R2-M verified: the exact-match `fail()` assertions are precisely `worker-runner-runtime.test.ts:84/124/169`; plan updates them.
- R2-M1 verified: threading test uses `summaryCore(input, deps, {caps,billing})`; `SummaryCoreInput` fields match.
- L2/L3 verified.

**VERDICT: NOT CONVERGED** (1 High, 1 Medium — both test-scaffolding, now fixed in v4).
