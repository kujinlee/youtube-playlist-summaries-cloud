# Reservation Release Lifecycle Spec v2 — Codex Round-2 Adversarial Re-Review

**Reviewer:** Codex (gpt-5.5), independent
**Artifact:** `docs/superpowers/specs/2026-07-15-reservation-release-lifecycle-design.md` (v2)
**Round:** 2 (re-review of the revised spec after round-1 NOT CONVERGED)
**Mandate:** (A) verify round-1 fixes F1–F6 genuinely closed; (B) hunt new defects the fixes introduced.
**Verdict:** **NOT CONVERGED**

---

## Blocking

### C-B1 — Paid transcription can be misclassified as "pre-billing" and released
Spec §3/§5 lines 60, 68, 110-112; code `lib/transcript-source.ts:40`, `lib/gemini.ts:669`, `lib/job-queue/summary-handler.ts:100`, `lib/job-queue/dig-handler.ts:69`.

**Failure scenario:** YouTube captions unavailable → `transcribeViaGemini` succeeds and returns segments (a **billable** Gemini call) → then `generateSummary`/`generateDig` throws, or persist/write fails. v2's taxonomy says "after `generateSummary`/`generateMagazineModel` returned" = billable, and "Gemini call threw" = releasable. That taxonomy **ignores the earlier billable Gemini transcription fallback**. The runner passes `p_billable_succeeded=false`, releases 150¢, and the global fuse under-counts real spend.

**Direction:** track "any paid Gemini response succeeded" across **transcription, summary, dig, and magazine** — do not key the boolean only to `generateSummary`/`generateMagazineModel`. Specify the typed marker end-to-end in the handler/core dependencies, not "e.g. a flag".

---

## High

### C-H1 — Serve token model is not single-flight after lease expiry; SET marker strands overlapping reservations
Spec §6 lines 145-156, 158-160, §8 line 206; code `supabase/migrations/0014_serve_owner_budget.sql:52`.

**Failure scenario:** Attempt A reserves doc D: ledger +6, owner +6, row `token=A`, `reserved_cents=6`. A runs longer than `lease_ttl_seconds`. Attempt B reclaims the same `(owner,doc,day)` row (because `lease_expires_at < now()`), increments ledger/owner another +6, then v2 **SETs** `token=B`, `reserved_cents=6`. A later fails and settles token A → **no match → A's reservation is stranded**. B settling only clears B's marker. The spec's claim "at most one un-settled attempt" is **false** — the lease guarantees one live *lease*, not one still-running *attempt*.

**Direction:** either do not reclaim while an unsettled reservation marker exists, or model attempts as separate rows keyed by attempt token. If keeping one row, `reserved_cents = SET` is unsafe under reclaim — it cannot represent two charged attempts.

### C-H2 — Cancel release SQL still hand-waves the old value; the shown CTE reads post-update state
Spec §5 lines 114-128, 130; code `supabase/migrations/0010_cancel_job_rowcount.sql:11`, `supabase/migrations/0019_share_tokens_cascade.sql:49`.

**Failure scenario:** Queued job has `reserved_cents=150`. The sketched `UPDATE` sets `status='cancelled'` and `reserved_cents=0`; `RETURNING status`/`reserved_cents` observe the **new** values, not old. The `<OLD reserved_cents>` placeholder is not real SQL, and `case when status='queued'` is false *after* the update. Implemented literally, cancel releases **0** and leaks 150. Playlist delete is worse: the cascade then deletes the job rows, destroying the only record of the reservation amount.

**Direction:** specify actual SQL — `old as (select id, created_at, reserved_cents from jobs where … for update)`, then update from `old`, then aggregate old amounts by reserve day. Explicitly for both single-job and playlist cancel.

### C-H3 — Generation crash/reaper-KEEP leaves the original global self-DoS mostly intact for active pre-billing crashes
Spec §2.3 line 39, §5 lines 104, 108, 132; code `supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:68`.

**Failure scenario:** Three summary jobs reserve 150¢ each, are claimed, then workers die **before any billable call**. Reaper keeps all reservations ("active may have spent"). Ledger stays 450¢ until UTC midnight → no more summary/dig job can reserve under the 500¢ cap. This is the **same "~3 cheap failures self-DoS" shape** the spec set out to fix, just via crash/lease-expiry instead of handler failure. The spec discusses a bounded 6¢ *serve* residual but the *generation* residual is 150¢ and global.

**Direction:** either explicitly accept this as a remaining High-risk limitation, or add a persisted job phase/billable marker so the reaper can release active jobs that never entered a billable phase.

---

## Medium

### C-M1 — `ledger_audit` is not specified enough to be reliable or safely hidden
Spec §4.2 lines 75-86, §8 lines 204-205.

**Failure scenario:** Migration creates `ledger_audit` without forced RLS/grants. SECURITY DEFINER RPCs insert under a role lacking rights or blocked by RLS → the audit insert **aborts the terminal transition**, contradicting "availability is preserved". Or broad select/insert grants **expose global money-path anomalies through PostgREST**. Also audit rows are transactional — any later exception rolls them back, so they are **not** durable out-of-band audit.

**Direction:** define table DDL, RLS posture, grants, and whether audit failure should ever abort. Recommended: service-role-readable only, no anon/authenticated grants, insertable by definer owner, and drop the claim that it survives transaction rollback.

---

## Round-1 Fix Check (Mandate A)

| Fix | Verdict |
|---|---|
| **F1** (release refunds real spend) | **Incomplete** — fixes post-summary persist failures, misses paid Gemini transcription before summary/dig (C-B1). |
| **F2** (serve exploit/double-refund/wrong-day) | **Incomplete** — token blocks direct uncharge/double-refund for a settled same attempt, but fails under lease reclaim/token overwrite (C-H1). |
| **F3** (cancel-active mis/double-release) | Conceptually fixed, but **SQL is not genuine** until old `reserved_cents` capture is written (C-H2). |
| **F4** (playlist-delete leak) | Conceptually fixed, **same old-value/set-based gap** as F3 (C-H2). |
| **F5** (reaper multi-row release) | Multi-row issue avoided, but **replaced by a 150¢ active-crash leak** (C-H3). |
| **F6** (`greatest(0,…)` masking) | Better than `greatest(0,…)`, but **audit DDL/RLS/grants unspecified** (C-M1). |
| **F7/L1/L3** | Mostly addressed; tests need an overlapping serve lease-reclaim case and transcription-billable classification. |

---

**Verdict: NOT CONVERGED.**
