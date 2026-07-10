# Task 1 review — `serve_model_charge` migration + `reserve_serve_model` RPC (money-path)

**Commits:** `35c6ae9` (impl) → `a855e11` (fix: reclaim-rollback + RLS precondition tests) → `13ddcbd` (fix: fixed-literal expired-lease seed)
**Gate:** §8 iterative dual-adversarial re-review to convergence (money-path trigger). Execution: `superpowers:subagent-driven-development`.

## Round 1
**Claude task-review — Approved.** Spec ✅: owner from `auth.uid()` internal (never a param); promoted-gate before any money; per-attempt charge inside the generating branch only; exactly-K bound (`attempt_count < max_serve_attempts`); cap arbiter **byte-identical** to `enqueue_job` (0011); savepoint/PJ004 rolls back claim+charge together; force-RLS + service_role-only grants; RPC `security definer set search_path=public` granted `authenticated, anon`; seed helper mirrors the worker row. Strengths: RLS-lockdown test non-vacuous (`.select()`-chained 0-rows + service-read exact fields + `relforcerowsecurity=true`); K-boundary is a real two-racer `Promise.all` asserting committed post-state. **Important:** `at_capacity`-on-*reclaim* rollback path (B7c) untested (only fresh-insert covered).

**Codex adversarial — no Critical.** **Important [INTENT/DESIGN]:** registered-account invariant `20·5·6 = 600 > cap·0.2 = 100` → the spec-accepted registered residual **deferred to 1G**; enforcement/test belongs to **Task 8** (couldn't see it reviewing Task 1 in isolation). **Minor ×2:** reclaim-rollback test missing; RLS-mutation test could false-green if setup silently failed (`before===after===null`).

## Fixes
- `a855e11`: added the `at_capacity`-on-reclaim rollback test (seeds prior expired row, forces cap refusal, asserts marker unchanged — not bricked/incremented); hardened the RLS test (assert setup returned `reserved`, `before` non-null, `attempt_count===1`).
- `13ddcbd`: expired-lease seed uses fixed old literal `'2000-01-01T00:00:00Z'` (clock-skew-proof; matches sibling tests).

## Round 2 re-review (convergence gate)
**Both CONVERGE — no Critical/Important.** Claude traced that the reclaim-rollback test **fails without the savepoint** (genuinely guards the branch); Codex confirmed the migration SQL is byte-identical since round 1 (fixes test-only) and no false-green/state-leakage. Money-path SQL SOUND (both, both rounds).

## Carry-forward
- **→ Task 8 (#22):** ENFORCE/TEST the config invariant `MAX_OWNED·K·est ≤ cap·SAFETY_FRACTION` — anon bound (2 docs) asserted hard; registered residual recorded as explicitly deferred to 1G. Do **not** rely on comments (Codex Important).

## Result
Tests: RED 12→GREEN 14/14 focused; full integration 172/174 (2 pre-existing live-Gemini skips), no regressions. **Task 1 COMPLETE — converged.**
