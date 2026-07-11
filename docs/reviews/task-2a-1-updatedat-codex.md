# Codex Review — Stage 2a Task 1 (updatedAt trigger + cloud read surface)

**Reviewer:** Codex (gpt-5.5) · **Date:** 2026-07-11 · **Diff:** `3231894..9403d20`
**Verdict:** Spec FAIL / Code Changes-needed (driven by the one High) · 0 Blocking.

## Passed checks
- Trigger `0015`: `BEFORE UPDATE FOR EACH ROW`, `new.updated_at = now()`, `set search_path = public`, no recursion, idempotent with the `0007`/`0009` RPCs that set `updated_at = now()` (transaction-scoped `now()`).
- `z.string().datetime({ offset: true })` deviation from the brief is **correct + necessary** (PostgREST timestamptz → `+00:00`, not `Z`); accepts both forms, rejects invalid; test-covered.
- Migration numbering `0015` off `0014` correct. Unit suites pass. (Could not run integration in sandbox — `EPERM` to 127.0.0.1:54321.)

## Findings
- **High — `updatedAt` round-trip into `data` jsonb.** `readIndex` now returns `{...data, updatedAt: r.updated_at}` (`supabase-metadata-store.ts:33`); `upsertVideo` writes `.update({ data: video })` (`:83`) and `updateVideoFields`/bulk merge caller `fields` — a read-then-write caller could persist a stale `updatedAt` into `data`, violating §7.1 "DB column/trigger is source of truth." **Fix:** strip `updatedAt` from every cloud write payload (shared helper in `upsertVideo`/`updateVideoFields`/`bulkUpdateVideoFields`).
- **Low — test misses the round-trip.** Regression test hits the direct `upsertVideo` path but passes raw `row.data`, not a `readIndex`-surfaced Video. Add a strip assertion.

## Disposition
Fixed (commit follows): shared `stripComputed` drops `updatedAt` in the three cloud writers + unit test. Codex High = Claude M1. See `task-2a-1-updatedat-review.md`.
