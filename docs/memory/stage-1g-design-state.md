---
name: stage-1g-design-state
description: "FIRES-WHEN: citing Stage 1G / G1 (per-owner serve budget, owner_over_budget, serve-stale), PR #10, or migration 0014 — MERGED 4d5b597, 2026-07-11; G2–G8 were the remaining backlog"
metadata:
  node_type: memory
  type: project
  originSessionId: cf75153b-dcc5-4c52-94eb-ed2c1ce13895
---

**Stage 1G / G1 is MERGED** — PR #10, merge commit `4d5b597`, 2026-07-11 (user approved the merge); migration 0014 on
master. Stage 1G = the residual/hardening backlog from 1F-a/b/c + 1D; G1 (the standout money risk) was done first.

**Problem it fixed:** `reserve_serve_model` (0012) charges 6¢/attempt, K=5 per (owner,doc,day), against the GLOBAL
`spend_ledger` (500¢/day). Anon is bounded (≤2 docs → ≤60¢); a REGISTERED owner could consume the whole shared cap.

**Design as shipped (spec `docs/superpowers/specs/2026-07-10-stage-1g-per-owner-serve-budget-design.md` §3):**
- Migration 0014: `serve_owner_budget(owner,day,spent_cents)` counter (force-RLS, service_role-only) +
  `guardrail_config.per_owner_serve_daily_cents int default 60 check (>= magazine_est_cents)` + `create or replace
  reserve_serve_model` restating the FULL header (`security definer set search_path=public`, no drop, re-grant).
- Two atomic arbiters in one savepoint: **per-owner checked FIRST (5a), then global (5b)**, so an over-budget owner
  doesn't lock the global money row and `owner_over_budget` wins (serve-stale still applies when global is full).
- User forks: S1 serve-only (enqueue is already monthly-quota-bounded); S2 per-owner cents/day; S3 distinct status
  `owner_over_budget`; S4 serve-stale on over_budget only (owner path, HTML). MD download is always free.
- Serve-stale gated on **titles-match** (positional coherence — render.ts pairs by index). Route 503 +
  `X-Magazine-Stale:1`; fileResponse `staleMarker?` (html-only). Share path untouched (never reserves). Fail-closed on a
  missing budget row. A drift-proof assertion pins that the per-owner cap (60) bounds the registered residual within
  the safety fraction (100).

**Deferred (test-only, no masked gap):** make unit fakeModel a valid MagazineModel; rpc-spy on P14; midnight-UTC
preseedBudget flake (shared with `serve-owner-budget.test.ts`). **1G backlog G2–G8 at merge time:** config-drift guard,
storage/row GC, anon rate-limit/cache, version-bump heal-at-mint, cosmetic, test-strength, 1D live-Gemini gate (status
of each after 2026-07-11 not re-checked here — see `docs/backlog.md` / `docs/roadmap-to-launch.md`).

## History
- Spec: round-1 Codex Blocking (create-or-replace definer) + High (serve-stale positional mis-pair) + Medium (reorder);
  v2 → round-2 0 new Blk/High → v3 (`892ea00`). Plan v3 (`3fed09d`): round-1 Codex Blocking (tests set cap=3, violating
  CHECK≥est). Trail `docs/reviews/{spec,plan}-1g-*`.
- T1 migration (`8694eae` + RLS-lockdown fix `52761e0`); T2 caller (`264bf38`, §8 dual review); T3 owner route
  (`8adf882`). Whole-branch opus review 0 Blk/High/Med (`docs/reviews/whole-branch-1g-review.md`); L1 fix `bba1107`.
- Gates at merge: tsc 0; unit 1808/1808; integration from a fresh `supabase db reset` (0001→0014) 259 passed / 2 skips.
- See [[process-conventions]], [[stage-1f-a-design-state]].
