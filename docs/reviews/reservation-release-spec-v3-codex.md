# Reservation Release Lifecycle Spec v3 — Codex Round-3 Adversarial Re-Review

**Reviewer:** Codex (gpt-5.5), independent
**Artifact:** `docs/superpowers/specs/2026-07-15-reservation-release-lifecycle-design.md` (v3)
**Round:** 3 (re-review of v3 after round-2 NOT CONVERGED)
**Verdict:** **NOT CONVERGED** (narrowing — all findings are follow-ons of the v3 fixes, no new structural problems)

---

## Blocking

### C3-B1 — Serve Gemini throws are still incorrectly treated as non-billable refunds (the B1 fix was applied to generation, not serve)
§3 lines 66-69, §6 line 243; `lib/html-doc/serve-doc.ts:81`, `lib/gemini.ts:547`.

**Failure:** `reserve_serve_model` reserves 6¢, then `generateMagazineModel` sends a Gemini request. Gemini returns/may meter, but the SDK throws after response parsing (section-count mismatch `gemini.ts:547`, transport timeout after server-side completion, wrapper throw `gemini.ts:554`). §6 says `serve-doc.ts` calls `settle_serve_model(token, released=true)` on **any** throw → refunds `spend_ledger` + `serve_owner_budget`. That is the **same under-count class v3 fixed for generation (B1), still open on serve.**

**Direction:** serve needs the same conservative taxonomy — release only for errors proven **before** the billable Gemini request is sent. Any throw from `generateMagazineModel` after request send (timeout/5xx/parse/schema/section-count) must **KEEP** until real-cost settle exists.

---

## High

### C3-H1 — `RETURNS TABLE` likely breaks the `serve-doc.ts` caller contract (M1 follow-on)
§6 lines 236-240; `lib/html-doc/serve-doc.ts:52`, `supabase/migrations/0014_serve_owner_budget.sql:22`.

**Failure:** v3 specifies `reserve_serve_model(...) returns table(status text, release_token uuid)` and says destructure `{ status, release_token }`. PostgREST returns table-valued RPCs as a **row set (array)**: `data` becomes `[{ status:'reserved', release_token:... }]`; `const { status } = data` yields `undefined` → the switch hits the unexpected-status path → the reservation just made at `0014:74-85` is **stranded**.

**Direction:** specify a single-row **composite/scalar-object** return shape Supabase returns as an object (or explicitly read `data[0]`), and test against real PostgREST. Cannot leave it as `returns table` + object destructuring.

---

## Medium

### C3-M1 — Playlist guarded-decrement audit is underspecified for partial per-day underflow (H2 follow-on)
§4 lines 76-86, §5 lines 175-193, §8 lines 283-284.

**Failure:** playlist has queued jobs on day X and day Y; `per_day = {X:150, Y:150}`. `spend_ledger` has enough for X but the Y row is missing/corrupt. The final `update … from per_day … reserved_cents >= per_day.amt` updates X, skips Y. A naive `IF NOT FOUND` after the statement **won't fire** (one row *was* updated) → Y's jobs cancelled+zeroed but **no `ledger_audit` row** records the missing Y ledger row.

**Direction:** make the audit branch **set-based** — capture updated days in a CTE, insert `ledger_audit` for every `per_day` row with no matching successful update. Single-row `IF NOT FOUND` is insufficient for playlist release.

### C3-M2 — Cancel return semantics confused with release semantics
§5 lines 147-173; `supabase/migrations/0010_cancel_job_rowcount.sql:11`.

**Failure:** current `request_cancel_job` returns `1` for both queued cancellation and active flag-set (`status in ('queued','active')`). v3 says `did_cancel := (pre.old_status = 'queued')` drives the return. Implemented literally, cancelling an **active** job sets `cancel_requested=true` but returns `0`/false → callers think no cancellation was requested. Playlist cancel has the same row-count hazard if diagnostics are read after the ledger update rather than the job update.

**Direction:** keep **two** values — `requested_count` (from `pre`/`upd`, for the API return) and `release_count`/`release_rows` (for ledger/audit). Do not let the spend-release CTE's row count define cancel-request success.

---

## Round-2 fix check
- **B1** — closed for **generation only, not serve** (C3-B1). 
- **H1/H2** — old-value capture mostly closed; **H2's audit branch incomplete** (C3-M1). 
- **H3** — now honestly documented. ✓ 
- **H4** — RLS/grant posture materially closed. ✓ 
- **H5** — documented as an accepted bounded leak. ✓ 
- **M1** — incomplete due to the `RETURNS TABLE` caller shape (C3-H1). 
- **M2** — acceptable (unknown errors KEEP). ✓

**Verdict: NOT CONVERGED.**
