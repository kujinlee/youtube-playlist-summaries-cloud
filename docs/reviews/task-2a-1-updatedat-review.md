# Claude Review — Stage 2a Task 1 (updatedAt trigger + cloud read surface)

**Reviewer:** Claude opus · **Date:** 2026-07-11 · **Diff:** `3231894..9403d20`
**Verdict:** Spec compliance **PASS** · Code quality **Approved** · 0 Critical, 0 Important.

## Verified
1. Migration `0015`: `BEFORE UPDATE FOR EACH ROW`, `new.updated_at = now()`, `plpgsql set search_path = public`, `create or replace` + `drop trigger if exists` (idempotent). Numbering correct off `0014`.
2. `readIndex` (`supabase-metadata-store.ts:23,33`): select widened to `data, updated_at`; maps `updatedAt: r.updated_at`. Spread order `{...r.data, updatedAt: r.updated_at}` makes the column authoritative even if a stale value ever sat in jsonb.
3. `VideoSchema.updatedAt` (`types/index.ts:207`) `z.string().datetime({ offset: true }).optional()` — the offset deviation is justified (PostgREST `+00:00`), accepts `Z`+offset, rejects invalid, test-covered (`types.test.ts:175-185`).
4. Trigger fires on the `upsertVideo` `.update({data})` gap; idempotent with the `0007` inline RPC sets; no recursion; INSERT covered by the column default.
5. Tests non-vacuous: integration sets `STORAGE_BACKEND='supabase'` + `signInAs()`; genuine RED is the direct-`.update` path (`toBeGreaterThan(t1)`), fails without the trigger; `sleep(1100)` distinguishes timestamps; BEFORE UPDATE fires even on no-op → no false-green.
6. No regressions: local FS path untouched (`updatedAt` stays undefined, absorbed by `.optional()`); no production consumer `parse()`s `readIndex` output (all use the plain cast).

## Findings (both Minor — optional)
- **M1 — latent `updatedAt` round-trip into `data` jsonb.** No present bug (both `upsertVideo` callers `pipeline.ts:152,278` build fresh Videos; read-path spread wins), but a future SP2 read-then-write caller could persist a stale `updatedAt` into `data`. Cheap hardening: strip it in `upsertVideo`. **→ Fixed now (aligns with Codex High) as defense-in-depth + brings spec N6 forward.**
- **M2 — doc note:** the offset fix only protects a future validating consumer; worth a one-line spec note for later cloud-timestamp fields. (No code change; noted.)

## Disposition
Core Approved. The one actionable item (M1 / Codex High) fixed in the follow-up commit; T1 then complete.
