# Stage 1E-b Task 1 — Codex Adversarial Review

**Reviewer:** Codex (`gpt-5.5`), read-only. Session `019f3fe7-d2b4-7b52-ae67-cee2b9b4ec58`.
**Target:** diff `c421391..778e2ce` (migration `0009` identity re-key + queue adapter + fixtures).
**Date:** 2026-07-07.
**Verdict:** revise — 1 Blocking (adjudicated plan-mandated, see below), 3 Low.

## Blocking (as reported) — ADJUDICATED: known plan-mandated decision, deferred to Stage 1H
- **`0009:4` — incremental apply fails on a DB with pre-existing `jobs` rows.** `alter table jobs add column playlist_id uuid not null` has no default/backfill, so if `0008` is already deployed to a **populated** `jobs` table and `0009` is applied incrementally, Postgres rejects it before the FK/index/RPC changes deploy. *Codex fix direction:* reset-only, or nullable-add → backfill/purge → `set not null` → add FK/index.

  **Controller adjudication (NOT a new defect):** This is byte-identical to Codex's round-1 **plan** review Blocking B2, already adjudicated at the Phase-2 plan gate. The plan's Global Constraints explicitly state *"schema change is safe under `db reset` (fresh empty `jobs` table); no backfill path needed,"* which the human approved when approving plan v2.3. The entire job queue (1E-a → 1H) is **pre-deployment**: `0008` exists in no populated production DB; dev/test applies the whole chain via `npx supabase db reset`. So there is currently no environment where `0009` applies incrementally over populated `jobs`. Adding a backfill path would *contradict* the approved plan. **Recorded as deferred, owner = Stage 1H (deployment):** the first real-environment deploy must apply the migration chain fresh (or, if `0008` is ever live with rows before `0009`, use the nullable→backfill→set-not-null path then). Not blocking Task 1.

## Low (test-guardrail hardening) — FIXED this task
Two reviewers (Codex Low #1 + Claude Minor #3) independently flagged the composite-FK assertion. Since `schema.test.ts` is the guardrail whose purpose is catching exactly the cross-tenant-write-injection regression the composite FK prevents, these are fixed rather than deferred:
- **`schema.test.ts:50` — composite-FK assertion checks only `conname`.** A regression recreating `jobs_playlist_owner_fk` as single-column `FOREIGN KEY (playlist_id) REFERENCES playlists(id)` would still pass, silently reopening the cross-tenant hole. *Fix:* assert `pg_get_constraintdef` includes `(playlist_id, owner_id) REFERENCES playlists(id, owner_id)`.
- **`schema.test.ts:58` — idempotency-index assertion only greps `indexdef` for `playlist_id`.** Passes even if `playlist_id` is in an INCLUDE/predicate but not the unique key, or the predicate diverges from `enqueue_job`'s `ON CONFLICT` predicate. *Fix:* assert exact key columns + predicate.
- **`schema.test.ts:67` — progress_phase CHECK allows supersets.** Only asserts the three required strings are present; a CHECK permitting a 4th value passes. *Fix:* assert exact constraint definition (or add a negative insert for an invalid phase).

## Not flagged by Codex, sound (cross-checked vs Claude review)
Composite FK genuinely rejects cross-owner enqueue (proven by integration test); `set_progress_phase` lease fence has no gap; idempotency join tests still prove the join under the `playlist_id`-inclusive key; no unmigrated `enqueue_job`/raw-`jobs` callers remain.
