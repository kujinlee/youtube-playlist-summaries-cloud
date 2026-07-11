# Stage 1G plan — Round-2 Post-Plan-Gate re-review (CONVERGED)

**Date:** 2026-07-10 · Plan v2 → v3. Both passes: **0 new Blocking/High; all round-1 fixes verified genuine against real code. Convergence gate met.**

## Claude (opus) — CONVERGENCE
Part A: BLOCKING (cap<6) fixed — zero lingering `per_owner_serve_daily_cents:3`; over-budget forced via `setOwnerCap(6)+preseedBudget(owner,6)`; remaining `daily_cap_cents:3` is the global cap (CHECK ≥0, legal). P16 relabel + real P16 (live-lease→in_flight) correct against 0012 step-4. P9/P13 added. P8 preseeds only A → proves per-owner keying. Rollback P3/P4b snapshot all 3 tables, full equality (PJ005/PJ004 roll back the whole sub-block). readTitleStableModel unit matches the real jest.mock harness (readModelEnvelope mocked → strict() never runs on fixture). P17 regprocedure + tolerant matcher + staleMarker html guard.
Part B (new-defect hunt): preseed vs `insert on conflict do nothing` no double-count; P16 live lease → in_flight not attempts_exhausted; P9 UTC date math correct; P15 loser's step-4 claim rolls back (one marker); P13 recovery backed by the file's existing gemini mock (verified). 3 Low (helper duplication, UTC-midnight flake inherent to existing harness, P13 gemini-mock coupling) — no action.

## Codex (gpt-5.5) — no Blocking/High, convergence
All round-1 fixes verified genuine (same points). New-defect check clean. One **Low**: `snapshot()` selected only value columns → `toEqual` wasn't true full-row equality (missed day/doc_key/lease_expires_at/actual_cents). **Addressed in v3** — snapshot now `select('*')` + stable ordering.

## Disposition
Round-2 returned only Low (both passes) → **convergence**. v3 strengthens the rollback snapshot to full-row. Per the AFK boundary (plan+impl automated via dual review after spec approval), proceed to SDD.
