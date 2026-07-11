# Codex Post-Plan-Gate Review — Stage 1G plan (v1)

**Reviewer:** Codex (gpt-5.5) · **Date:** 2026-07-10. Migration fidelity verified faithful (only 5a arbiter + PJ005 added).

## Blocking
1. **Tests set `per_owner_serve_daily_cents: 3`, violating the new `CHECK (>= magazine_est_cents=6)`.** Every `update({per_owner_serve_daily_cents:3})` fails the CHECK → tests error or silently keep cap=60 → wrong expectations. **Fix:** never cap < est; set cap=6 (or 12) and pre-seed today's `serve_owner_budget` at the cap (`insert … values($owner, utc_day, 6)`) so `spent+6 > cap` → `owner_over_budget`. Ripples through P3/P4/P8/P10.
2. **Task 1 Step 6 mislabels P15 as P16 and MISSES real P16.** The two-doc-concurrency test is spec P15. Spec P16 (over budget + live lease → `in_flight`, no stale) is absent. **Fix:** relabel; add real P16 (live `serve_model_charge` row + over budget via pre-seed → expect `in_flight`, spend unchanged).

## High
3. **P9 (daily reset) missing.** Fix: seed `serve_owner_budget` at `day = utc_day - 1, spent = cap`, reserve today → `reserved`, today's row = 6.
4. **P13 (stale-then-recovered) missing.** Fix: stale envelope (old generatorVersion) + yesterday's budget row at cap → call route today → 200, no `X-Magazine-Stale`, envelope rewritten to current version.
5. **P8 isolation test doesn't prove isolation** (sets cap<est → both blocked by misconfig, then raises). Fix: valid cap=6, pre-seed ONLY owner A's today row at 6; B has no row → A `owner_over_budget`, B `reserved`.

## Medium
6. **P3/P4 rollback tests don't snapshot prior state** (start from no rows → only prove "no new rows"). Fix: snapshot serve_owner_budget + spend_ledger + serve_model_charge before/after, assert exact equality on both `owner_over_budget` and `at_capacity`.
7. **P17 helper `where p.proname='reserve_serve_model'` matches overloads/non-public.** Fix: `where p.oid = 'public.reserve_serve_model(uuid,text)'::regprocedure`.
8. **P17 `proconfig` matcher brittle.** Fix: tolerant `(data.cfg ?? []).some(v => v.replace(/\s/g,'')==='search_path=public')`.

## Low
9. Task 2 Step 5 integration tests written after implementation — move P5/P6/P6b/P14 before the serve-doc case.
10. "Mirror existing harness" placeholders risky for literal subagents — inline exact stub shapes / confirm helper names.
