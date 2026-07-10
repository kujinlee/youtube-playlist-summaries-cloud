# Claude Adversarial Review — Stage 1G per-owner serve budget spec (v1)

**Reviewer:** Claude (opus) · **Date:** 2026-07-10
**Verdict:** Fundamentally sound; core atomicity/rollback/isolation verified against real 0012. 0 Blocking, 2 High, 2 Medium, 3 Low.

## High
- **H1 (= Codex High) — serve-stale positional mismatch.** Route renders current `parsed` against stale `resolved.model`; `render.ts` zips by array index. D5 drops the ENTIRE `isFresh` gate (incl. `sameTitles`), so serve-stale fires on titles/content drift → heading X paired with section A's stale lead/bullets; extra current sections vanish. D5's "reflects last-materialized state" claim is false — it's a current/stale hybrid. Own-doc only → High. Fix (a): gate serve-stale on version-only staleness (`sameTitles === true && version !== GENERATOR_VERSION`); titles drifted → fall through to over_budget 503.
- **H2 (= Codex Blocking) — `create or replace` risk is SECURITY DEFINER + search_path, not grants.** Grants/ownership survive a same-signature replace; the killer is omitting `security definer`/`set search_path` → SECURITY INVOKER → force-RLS blocks the service_role-only writes → every serve breaks. Fix: mandate the full header verbatim + a test asserting `pg_proc.prosecdef=true`, `proconfig` has `search_path=public`, anon/authenticated can execute.

## Medium
- **M1 — global `at_capacity` (5a first) suppresses serve-stale even when a stale model exists.** Over-budget owner in a globally-full window loses the (free, pressure-relieving) stale fallback exactly when it's most valuable. P4 omits the lost-stale interaction. [Resolved in v2 by adopting Codex's per-owner-first reorder → owner_over_budget wins → serve-stale applies.]
- **M2 — over-budget + concurrent live lease → in_flight/busy, not owner_over_budget → not serve-stale.** To reach 5b, step-4 must claim the lease; a live lease → `in_flight` → busy/503. Serve-stale not guaranteed for every over-budget view. Add a behavior row.

## Low
- **L1** — pin the gate-free reader import-guard-safe (no gemini/charging import); keep read-model.ts a pure blob leaf; 1F-b guard must still pass.
- **L2** — cross-column CHECK `per_owner_serve_daily_cents >= magazine_est_cents` re-validates on either column's UPDATE → admin raising `magazine_est_cents` above the per-owner cap fails. Operational foot-gun; note in D2.
- **L3** — no client-read grant on `serve_owner_budget` (unlike `usage_counters`) → forecloses a "daily budget remaining" UX in Sub-project 2 without a new RPC. Known consequence, not a defect.

## Verified sound (against real code)
No phantom-cents leak / cap-DoS: 5a increment + step-4 claim are inside the 0012 `begin…exception…end` savepoint; PJ005 rolls back ALL (attempt_count, global, per-owner). No phantom lease. Row-lock serializes same-owner races. render.ts won't crash on shorter stale model (`if(!m) return ''` — why H1 is silent-wrong not 500). Cap boundary exact (P10). CHECK ≥ est guarantees ≥1 attempt. Admin-lower-cap no underflow. Fresh doc never over-budgets (resolve returns ok before reserve). Share never-charge structurally preserved. MD path unaffected. `X-Magazine-Stale` threads both view + html-download via fileResponse (lost only on saved file — acknowledged).
