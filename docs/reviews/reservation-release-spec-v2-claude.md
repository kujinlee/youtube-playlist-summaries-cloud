# Round-2 Adversarial Re-Review — Reservation Release Lifecycle Spec v2 (Claude)

**Reviewer:** Claude (independent adversarial pass, round 2)
**Spec:** `docs/superpowers/specs/2026-07-15-reservation-release-lifecycle-design.md` (v2)
**Method:** Every v2 claim cross-checked against the real SQL — `0008_jobs_queue.sql`, `0009_job_playlist_identity_and_worker_persistence.sql`, `0010_cancel_job_rowcount.sql`, `0011_cost_guardrails.sql`, `0012_serve_model_charge.sql`, `0014_serve_owner_budget.sql`, `0018_enqueue_dig.sql`, `0019_share_tokens_cascade.sql` — and the callers `lib/job-queue/worker-runner.ts`, `lib/html-doc/serve-doc.ts`. Round-1 findings (F1–F7, L1/L3) verified for genuine closure.

**Verdict up front: NOT CONVERGED.** One new Blocking (a real under-count / overspend hole in the error taxonomy) and five High.

---

## Mandate A — are the round-1 fixes genuinely closed?

| Fix | Round-1 defect | v2 mechanism | Genuinely closed? |
|---|---|---|---|
| **F1** | release refunds real spend (Gemini succeeded, save failed) | spend-aware `p_billable_succeeded` | **NO — reopened by an adjacent hole.** Persist-after-Gemini closed, but the taxonomy classifies *all* Gemini throws (incl. 5xx/timeout) as "no charge → RELEASE" → a timeout-after-metering under-counts. See **B1**. |
| **F2** | serve release exploitable / double-refundable / wrong-day | per-attempt token + stored day + clear-on-settle | **Partially.** Three named vectors genuinely closed. But a *new* bounded leak + a false invariant introduced. See **H5**. |
| **F3** | cancel-active mis/double-release | release only on genuine `queued→cancelled` | **Design right, SQL wrong.** `did_cancel` gate correct; OLD-`reserved_cents` capture is non-functional SQL that fails toward a leak. See **H1**. |
| **F4** | playlist-delete leaks reservations | release inside `request_cancel_playlist_jobs` | **Under-closed.** The set-based multi-row/multi-day release is exactly the complexity F5 claimed to eliminate, relocated here and left unwritten. See **H2**. |
| **F5** | reaper multi-row release underspecified | reaper never releases | **Closes the reaper CTE, opens a residual.** Correct not to release, but silently reintroduces the headline self-DoS on the 150¢ global crash path, undocumented. See **H3**. |
| **F6** | `greatest(0,…)` masks corruption | guarded decrement + `ledger_audit` | **Design right, table unspecified.** No RLS/grants/schema/exposure — a missing grant also breaks the "still commits" availability claim. See **H4**. |
| **F7 / L1 / L3** | behavior gaps, marker atomicity, status-guard primacy, owner_id | §7→23 rows, §6 marker placement, §4.3 wording, §6 owner_id | **Closed.** No new finding. |

---

## BLOCKING

### B1 — "Gemini transport/5xx/timeout ⇒ no charge ⇒ RELEASE" under-counts real spend (overspend direction)
**Where:** §5 line 111 ("…a Gemini call that threw (transport/5xx/timeout → no successful response → no charge)") → `p_billable_succeeded=false` → RELEASE. Reinforced by §3 row 2 (line 60).

**Why the premise is false:** A throw *from* `generateSummary`/`generateMagazineModel` does not prove the generation wasn't metered. Google bills on server-side completion; a client-side socket timeout, SDK deadline, or 504 at an intermediary can fire *after* the model metered a full response but *before* the body reached the worker — billing-identical to F1's "Gemini succeeded, save failed" case (which v2 correctly KEEPS), yet the taxonomy sends it to RELEASE.

**Failure (inputs → wrong ledger):** worker claims summary job (+150¢) → `generateSummary` completes on Google's side and meters, response lost to a proxy 504/timeout → runner classifies `billable=false` → `fail_job(billable=false)` → RELEASE 150¢. Real money spent; ledger gave it back; cap now admits 150¢ more real spend than it should. Under a proxy-timeout burst this is systematic — the "never under-counts" invariant (§3) violated on demand.

**Direction:** only errors that provably occur **before any bytes are sent to Gemini** may be `false` (payload/validation, pre-call `PermanentTranscriptError`, duration-cap, at-capacity, idempotency skip, connection-refused/DNS pre-send). **Any throw originating from the Gemini call itself is ambiguous → KEEP (`true`).** Remove "5xx/timeout" from the RELEASE list in §5 line 111 and §3 line 60.

*(Corroborates Codex C-B1 from a distinct angle — Codex flagged the billable **transcription fallback** being missed; Claude flags the **timeout-after-metering** ambiguity of the summary/magazine call itself. Both are real; together the whole "Gemini threw = no charge" premise is unsound.)*

---

## HIGH

### H1 — Cancel CTE cannot read OLD `reserved_cents`; the sketch releases `amt = 0` → queued-cancel never releases (leak / self-DoS persists)
**Where:** §5 lines 115-128. The `flipped` CTE sets `reserved_cents = 0` in the same UPDATE, then `RETURNING` computes `amt` from `<OLD reserved_cents>`.

**Why it breaks:** In PostgreSQL < 18 (Supabase is PG15/17), `UPDATE … RETURNING` returns the **post-update** row → `RETURNING reserved_cents` after `set reserved_cents = 0` yields **0**. `<OLD reserved_cents>` is a placeholder with no legal expression there (`RETURNING OLD.col` is PG18-only). Copied literally → `amt = 0` → guarded decrement subtracts 0 → the queued job's 150¢ is never released — the self-DoS §1 exists to fix, reintroduced on the cancel path.

**Direction:** explicit two-CTE pre-read that also serializes against a concurrent `claim_next_job`:
```sql
with pre as (
  select id, reserved_cents as old_amt, (created_at at time zone 'utc')::date as d
    from jobs where id = p_job_id and owner_id = auth.uid() and status = 'queued' for update),
upd as (
  update jobs set cancel_requested = true, status = 'cancelled', reserved_cents = 0, updated_at = now()
   where id = p_job_id and owner_id = auth.uid() and status = 'queued' returning id)
update spend_ledger sl set reserved_cents = sl.reserved_cents - pre.old_amt, updated_at = now()
  from pre where sl.day = pre.d and sl.reserved_cents >= pre.old_amt;
```
*(Same defect as Codex C-H2.)*

### H2 — `request_cancel_playlist_jobs` set-based release is the multi-row/multi-day CTE F5 claimed to eliminate — unspecified
**Where:** §5 line 130 ("Same pattern, set-based … grouped by reserve-day"). No SQL. Real fn `0019:45-58` flips all non-terminal jobs of a playlist in one set UPDATE.

**Why it breaks:** A playlist can hold many queued jobs enqueued across a midnight boundary, each with its own `reserved_cents` and `(created_at at utc)::date`. Correct release needs the exact operation round-1 H1 flagged / F5 claimed to remove: snapshot pre-update `reserved_cents`, aggregate by day, decrement each `spend_ledger` day row by its group sum. A single `where day = X` decrement can't credit multiple days → other day leaks; and `RETURNING reserved_cents` after zeroing returns 0 → nothing released.

**Failure:** delete a playlist with 5 queued summary jobs, 2 on day X (23:58), 3 on day Y (00:03) → naive single-day port strands ≥450¢. F4 not closed.

**Direction:** write the explicit set-based pre-read + `group by (created_at at utc)::date` + per-day guarded decrement; acknowledge F5 relocated this complexity rather than removing it.

### H3 — Reaper-keep leaves an unbounded-by-count 150¢ **global** crash residual — the headline self-DoS, undocumented for the generation path  ⚠️ POSSIBLY GOAL-AFFECTING
**Where:** §2 decision 3 / §2.3 document only the **serve** residual (6¢, per-owner ≤ 60¢). §5 line 132 / §3 line 64 make the reaper/crash path KEEP 150¢ with no residual accounting.

**Why it breaks:** A worker dying mid-run *after* `enqueue_job` reserved 150¢ but *before* any billable call (SIGKILL during deploy, OOM during transcript fetch, container recycle) leaves an `active` job; the reaper terminalizes it and never releases. Its 150¢ stays reserved on the **global** `spend_ledger` until midnight. With `daily_cap_cents=500`/`summary_est_cents=150`, **~3 such crashes lock the entire system's budget** — verbatim the failure mode §1 promises to eliminate. Unlike the serve residual this is **global, count-unbounded**, and reachable via an ordinary operational event (a crash-loop during rollout).

**Direction:** arguably goal-affecting → surface to the human. At minimum document the generation crash residual (its global, count-unbounded nature, deploy/crash-loop risk) and either (a) scope-in a generation lease-expiry settle (persist a "billable-phase-entered" marker so the reaper can release active jobs that never billed), or (b) record it as an accepted residual with operational mitigation (graceful worker drain before deploy). Don't let §2.3's per-owner-bounded framing stand in for the 150¢ global case.

*(Same defect as Codex C-H3.)*

### H4 — `ledger_audit` has no RLS / grants / schema / PostgREST-exposure spec; a missing grant also breaks the "still commits" availability claim
**Where:** §4.2 lines 80-86 — new table inserted from `fail_job` (security **invoker**, service_role) and the definer cancel/settle RPCs. No `create table`, no `enable/force row level security`, no grants. Every other money table is `force row level security` + service_role-only.

**Two failures:** (1) **Exposure** — PostgREST auto-exposes any `public` table; without RLS `ledger_audit` is world-readable/writable at `/rest/v1/ledger_audit`, leaking mis-accounting events and allowing forged audit rows. (2) **Availability regression** — the audit `insert` shares the RPC transaction; if `fail_job` (service_role caller) lacks `INSERT`, the insert raises → whole txn (terminal flip + lease clear) rolls back → job stays `active` → `worker-runner.ts:67-71` returns `'lost'` → dangles until reaper. So "still commits" is contingent on an unstated grant.

**Direction:** `enable + force row level security`, `grant insert (+ select) to service_role` only, no anon/authenticated policy (mirror `spend_ledger`); confirm definer functions (owner postgres, BYPASSRLS) can insert; state the audit insert must never fail the terminal write.

*(Codex rated this Medium (C-M1); Claude rates it High for the availability regression + PostgREST exposure. Treat as High.)*

### H5 — Serve "at most one un-settled attempt per (owner,doc,day)" is false once generation exceeds the lease TTL → double-reserve + token overwrite (bounded leak; false invariant)
**Where:** §6 line 156. Real lease TTL `lease_ttl_seconds` default **180s** (`0012:22`), set once at reserve, **never heartbeated** on the serve path (`serve-doc.ts` has no lease renewal).

**Why the invariant is false:** single-flight holds only while the lease is live. The reserve→settle window spans an unbounded `generateMagazineModel` + write (`serve-doc.ts:81-92`). If that exceeds 180s the lease is expired and a concurrent second view **reclaims** (`reserve_serve_model` on-conflict `where lease_expires_at < now()`, `0014:54-58`) → runs 5a/5b again (`+6`/`+6`) and SETs `reserved_cents=6, release_token=TB`, overwriting A's `TA`. A later `settle_serve_model(TA,…)` → no match → no-op → A's 6¢ stranded. Two reserves, ≤ one release.

**Direction (leak is bounded/safe, but the design rests on a false invariant):** correct the §6 claim to "at most one un-settled attempt *while the lease is live*"; either heartbeat/extend the serve lease across generation, or fold the slow-generation overlap into the documented residual with its per-owner ≤ 60¢ bound.

*(Same defect as Codex C-H1.)*

---

## MEDIUM

### M1 — Returning the serve token requires a return-type change (DROP + re-grant + caller contract), contradicting "preserving signatures"
**Where:** §6 lines 149-155 vs §5 line 94. Real `reserve_serve_model` returns scalar `text` (`0014:22-24`), granted `authenticated, anon`, destructured as scalar in `serve-doc.ts:52-56`. Carrying a token → composite/record return → `DROP FUNCTION` + recreate + re-grant + update the `serve-doc.ts` call site to read `{status, token}`. Security is fine (token server-held, unforgeable); this is a mechanics gap. **Direction:** specify the DROP+recreate, new return shape (`returns table(status text, release_token uuid)`), grant re-issue, and the destructure change.

### M2 — Handler→runner `billableSucceeded` marker is assumed, not specified; unclassified pre-billing errors default to KEEP (leak)
**Where:** §5 line 112. Real `worker-runner.ts:58-66` catches a bare `e`, computes only `retryable`; no marker plumbing today; the handler change isn't shown. With SQL default `true` (KEEP — correct for safety), any pre-billing error the runner can't affirmatively classify `false` defaults to KEEP → 150¢ leak. So release coverage is only as complete as the taxonomy + the handler actually attaching the marker. **Direction:** specify the handler change (attach `billableSucceeded=false` on every pre-Gemini throw path) and the runner's marker read; keep SQL default `true`; document that unclassified errors KEEP (leak, safe).

---

## LOW

- **L1** — §7 behavior 3 ("Gemini-threw releases") bakes in the wrong classification. Add a row: "Gemini call throws but may have metered (5xx/timeout) → KEEP" once B1 is fixed, + a test that a post-send Gemini throw does not release.
- **L2** — §4.2 "the terminal transition still commits" should be conditioned on the audit grant (see H4); reword once H4's grants are specified.

---

## Verified-correct (convergence trail — no finding)
- **Serve un-charge (round-1 Claude-B1) genuinely closed** — release requires the unforgeable server-held token; browser client never receives it; `owner_id = auth.uid()` + token match blocks cross-tenant / kept-serve un-charge.
- **Serve double-refund / wrong-day (round-1 Codex-2/3) closed** — single-use token cleared on settle; decrements target the row's stored `day`, never `now()`.
- **Cancel-active double-release (round-1 Claude-B2) closed at the design level** — `did_cancel` gates release to the genuine flip. (Implementation blocked by H1's SQL, not the design.)
- **Generation exactly-once under concurrent claim vs cancel** — `for update skip locked` serializes claim vs cancel; no double-release, no claim-of-cancelled.
- **Reaper vs zombie-worker** — reaper flips off `active`; lease-loser's `fail_job` finds no `active` row and returns null before any release. Exactly-once holds; the issue is the H3 leak, not a double.
- **Generation day-correctness (§4.4)** — `now()` txn-stable, `created_at::date at utc == reserve-day`, re-queue never rewrites `created_at`.
- **Retry never re-reserves** — retry re-claims the same row; one `enqueue_job` = one reservation.

---

## VERDICT — NOT CONVERGED. Must-fix before merge:
1. **B1 (Blocking)** — reclassify Gemini 5xx/timeout (and the billable transcription fallback, per Codex C-B1) as ambiguous → KEEP; only provably-pre-send errors RELEASE.
2. **H1** — replace the non-functional `<OLD reserved_cents>` cancel sketch with an explicit pre-read CTE.
3. **H2** — write the `request_cancel_playlist_jobs` set-based, multi-day, pre-read release SQL.
4. **H3** — document (and surface to the human) the 150¢ global, count-unbounded reaper/crash residual.
5. **H4** — fully specify `ledger_audit` (force-RLS, service_role-only grants, no PostgREST exposure) + make the audit insert incapable of failing the terminal write.
6. **H5** — correct the false serve single-flight invariant; cover the un-heartbeated-180s-lease overlap.

M1, M2, L1, L2 are dispositions to record.
