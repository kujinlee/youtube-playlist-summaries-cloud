# Round-3 Adversarial Re-Review — Reservation Release Lifecycle Spec v3 (Claude, independent)

**Artifact:** `docs/superpowers/specs/2026-07-15-reservation-release-lifecycle-design.md` (v3)
**Grounded in:** migrations `0006/0008/0009/0010/0011/0012/0014/0018/0019`; `lib/job-queue/{worker-runner,summary-handler,dig-handler}.ts`; `lib/html-doc/serve-doc.ts`; `lib/storage/supabase/supabase-job-queue.ts`; `lib/gemini.ts`; `lib/transcript-source.ts`; `tests/integration/cancel-job-rpc.test.ts`.
**Scope:** Mandate A (are round-2 fixes genuinely closed?) + Mandate B (defects the v3 fixes introduced).
**Note:** `ledger_audit`, `settle_serve_model`, `p_billable_succeeded`, `release_token` don't yet exist in the tree — expected; this is a design review, all SQL evaluated as written.

---

## Blocking

### B-1 — Serve path still under-counts on a metered-then-threw magazine call (B1 unfixed on the serve leg)
**§3 serve rows + §6 "Caller change".** The generation taxonomy was corrected so any throw from a billable Gemini call KEEPs; the serve leg was not. §3 asserts the opposite ("`generateMagazineModel` threw before returning → RELEASE") and §6 makes the caller unconditional ("On throw → `settle_serve_model(token, released:=true)`"). `generateMagazineModel` (`gemini.ts:495` → `generateJson` → `model.generateContent` with `REQUEST_TIMEOUT_MS`) is billable and can throw transport/timeout/504 **after** Google metered — byte-identical to the summary case B1 KEEPs.

**Failure:** Google meters the transform (6¢ real), socket times out → `generateMagazineModel` throws → `settle_serve_model(token, released=true)` → `spend_ledger -= 6`, `serve_owner_budget -= 6`. Real 6¢ spent, refunded → **under-count**, violating §2.1's "never under-counts". *(Corroborates Codex C3-B1.)*
**Direction:** apply the same pre-send-vs-maybe-metered rule to serve — RELEASE only on `generateMagazineModel`'s *pre-send* `NonRetryableError` (missing caps `gemini.ts:505`, input-cap breach `gemini.ts:85`); KEEP on any other throw.

### B-2 — §1 headline self-DoS (Gemini outage) is NOT closed, but §2.4 claims it is (internal contradiction, GOAL-AFFECTING)
**§1 vs §2.4 vs §5/B1.** §1's motivating problem: "A Gemini **outage** or retry burst self-DoSes all users at **~$0 real spend**." §2.4's rationale for accepting the crash residual claims the release-only fix "closes the **dominant** self-DoS surface — handler-level failures (**Gemini outage**, retry burst, bad input, at-capacity)." But B1 makes **every throw from a billable Gemini call KEEP** — a Gemini outage *is* a storm of Gemini-originated throws.

**Failure:** Gemini returns 503/timeouts for 20 min. Each generation: reserve 150¢ → `generateSummary` → 503 → `summary-handler` `throw e` (no `false` marker) → runner defaults `p_billable_succeeded=true` → **KEEP**. Three failures lock the global ledger at ~$0 real spend — **precisely the §1 scenario, still open.** §1 says outage = $0 (should release); B1 says outage-throw = maybe-metered (KEEP). The spec resolves toward money-safety (correct) but never admits it thereby fails the §1 goal, and §2.4 lists "Gemini outage" as *closed*. The §2.4 residual is therefore **much larger** than "crashed before first billable call" — it includes every outage/timeout/retry-burst failure (the common case). The user's ACCEPT decision rested on the false premise that outage failures release.
**Direction (goal-affecting → surface to human):** either (a) honestly restate that with conservative KEEP the outage self-DoS is **not** closed by this slice (only pre-send bad-input/capacity/duration releases), closing it needs settle; or (b) release on Gemini failures where "not metered" is provable (explicit HTTP 4xx/5xx, connection-refused) and KEEP only the ambiguous client-timeout case. §1/§2.4/§5/§10 must tell one consistent story.

---

## High

### H-1 — Pre-send transcript/Gemini failures are not implementable as RELEASE (taxonomy unreachable through the real error flow)
**§3 row 2, §5 pre-send list, §7 behavior 2 vs `transcript-source.ts` + `summary-handler.ts`.** `resolveTranscriptSegments` collapses all second-stage outcomes into one generic `Error('transcript unavailable …')` (`transcript-source.ts:61-66`): fallback-disabled `NonRetryableError` (`gemini.ts:658`, pre-send, $0), pre-send connection-refused, AND post-metering timeout are indistinguishable. `summary-handler` only special-cases `PermanentTranscriptError` (see L-2, ~unreachable) and otherwise `throw e` (`:141`). **No code path can attach `billableSucceeded=false` to a genuine pre-send transcript failure** → defaults to KEEP.

**Failure (shipped config `CLOUD_TRANSCRIBE_FALLBACK_VERIFIED=false`, `gemini.ts:25`):** every caption-less video → `transcribeViaGemini` throws `NonRetryableError` before billing → wrapped to generic `Error` → `throw e` → KEEP 150¢ at $0. ~3 caption-less videos lock the budget. §7 behavior 2 ("pre-call no-transcript releases") is unsatisfiable. Only handler-direct pre-send throws (payload validation `:61`, duration-cap `:68`) can reach the runner with a `false` marker.
**Direction:** if pre-send transcript failures must release, `resolveTranscriptSegments` must preserve a typed pre-send discriminator (stop wrapping into generic `Error`) and the handler must translate it. Otherwise drop those rows from RELEASE and fold into the KEEP residual.

### H-2 — Playlist-cancel CTE stops flagging `cancel_requested` on active jobs → reintroduces write-after-delete hazard
**§5 `request_cancel_playlist_jobs` CTE vs `0019:49-55`.** The existing function sets `cancel_requested=true` on **all** non-terminal jobs (`status in ('queued','active')`) so an in-flight worker stops writing to rows the cascade delete is about to remove (the entire reason 0019 exists). The rewritten CTE's `upd` updates only `pre` rows, and `pre` filters `status='queued'` → **active jobs never flagged.**

**Failure:** playlist has one active summary job. Delete → new CTE flips only queued; the active job's `cancel_requested` stays false → worker keeps running, calls `persist_summary` on a `videos` row the `ON DELETE CASCADE` is concurrently removing → write races the delete. §5 prose claims "active-handling unchanged," but the SQL changes it.
**Direction:** `upd` must still set `cancel_requested=true` on active jobs (`status in ('queued','active')`), flipping `status`/zeroing `reserved_cents` only for the queued subset; `pre`/`per_day` stay queued-only for the release.

### H-3 — Guarded-decrement audit (§4.2/behavior 15) not expressible in the cancel CTEs → corruption silently swallowed on 2 of 4 release paths
**§4.2 + §7 behavior 15 vs the §5 CTEs.** §4.2's mechanism is procedural (`update … ; if not found then insert into ledger_audit`). The cancel paths are a **single** multi-CTE statement whose final `update … where reserved_cents >= amt` matches zero rows on underflow with **no `if not found`** → no audit row. F6/H4's "make corruption visible" is closed only on `fail_job`/`settle_serve_model`, not the cancel RPCs.

**Failure:** ops corruption leaves `reserved_cents` below a queued job's `old_amt`. Cancelling silently no-ops the decrement with **no audit row** — the exact silent clamp §4.2 promised to remove. Behavior 15 fails for cancel paths.
**Direction:** express audit as a data-modifying CTE (`ins_audit as (insert into ledger_audit select … where day not in (select day from dec_returning))`), or split cancel release into procedural plpgsql like `fail_job`.

### H-4 — Cancel RPCs' integer return contract broken by the CTE rewrite
**§5 CTEs vs `0010:18-19`/`0019:56-57`, `supabase-job-queue.ts:44-53`, `cancel-job-rpc.test.ts:37`.** Both functions `returns int` via `get diagnostics n = row_count`, consumed as counts and asserted by tests. After the rewrite, `row_count` captures the **final** statement (`update spend_ledger`), not the jobs update.

**Failures (against existing tests):** `request_cancel_job` on an active job → final ledger update matches 0 rows (guard false) → returns **0**; test *"flags an active job without changing status"* asserts `res.data === 1` (`cancel-job-rpc.test.ts:37`) → **breaks**. `request_cancel_playlist_jobs` with 5 queued jobs on one day → final update touches 1 day-row → returns **1**, not 5.
**Direction:** derive the return from the jobs mutation (`upd … returning 1` aggregated), or restructure so `get diagnostics` reflects rows flagged; if semantics change, DROP+recreate + re-grant like `fail_job` (spec is silent on this for cancel functions).

---

## Medium

### M-1 — Idempotency-skip KEEPs (completes), contradicting its RELEASE classification
**§3 row 2 / §7 behavior 2 vs `summary-handler.ts:86-92`.** On an already-promoted artifact the handler `return;`s → `complete_job` → `completed` → KEEP. But §3/behavior 2 list "idempotency skip" as RELEASE. Safe direction (over-count), but behavior-2's test can't pass. **Direction:** drop idempotency-skip from RELEASE (accept over-count) or have the handler signal a pre-send release; align §3/§7.

### M-2 — `serve-doc.ts` destructure guidance wrong for a `returns table` function
**§6 "M1" step vs `supabase-job-queue.ts:60-61`.** A `returns table(...)` fn comes back through `.rpc()` as an **array** (cf. `claim_next_job` consumed as `data[0]`). §6 says destructure `{ status, release_token }` directly from `data` → `undefined` → `switch` hits `default: throw` on every serve. *(Corroborates Codex C3-H1.)* **Direction:** `const { status, release_token } = data[0]` (or a composite scalar + `.single()`); pick one concrete shape.

### M-3 — `fail_job` release body is prose-only; requeue-exclusion + day/amount reads unspecified at SQL level
**§5.** No SQL given for `fail_job`'s release. It must gate on `v_new in ('failed','dead_letter','cancelled')` (a retryable `v_new='queued'` must NOT release — behavior 6) **and** `p_billable_succeeded=false` **and** the `status='active'` fence, and `select created_at, reserved_cents` (current SELECT at `0008:148` reads neither). Correct in intent but the requeue-exclusion lives only in prose. **Direction:** show the `fail_job` release SQL, or pin the `v_new`-terminal + `billable=false` + `active` guard + `created_at`/`reserved_cents` reads as explicit acceptance criteria.

---

## Low

### L-1 — "at-capacity" listed as a generation RELEASE case, but no reservation exists to release
**§3 row 2 / §5.** An `enqueue_job` at-capacity rolls back the reserve (`0018:64`); serve at-capacity rolls back the claim (`0014:85`). No in-flight reservation to credit → classifying at-capacity as RELEASE is a harmless category error. Clarify it's a no-op.

### L-2 — The caption-less `PermanentTranscriptError` path the taxonomy leans on is effectively unreachable
**`transcript-source.ts:44-47` vs `gemini.ts:673`.** `PermanentTranscriptError` fires only when `transcribeViaGemini` *returns* zero segments, but it *throws* on zero (`gemini.ts:673`) instead. So the branch is ~dead, and when reached it's downstream of a billable transcription call. §3's "pre-call `PermanentTranscriptError`" is inaccurate about *when* it fires and its billability. Behavior 3b's shape is realistic; behavior 2's is not. Align with real control flow (ties into H-1).

---

## Mandate A scorecard (round-2 fixes)

| Finding | Verdict |
|---|---|
| B1 (Gemini-throw KEEP) | **Partially** — correct for generation; **unfixed on serve (B-1)**; surviving KEEP surface under-documented (**B-2**); pre-send cases can't reach RELEASE (**H-1**). |
| H1 (cancel OLD-value pre-read CTE) | **SQL valid & correct** for OLD-value capture + `claim_next_job` serialization — genuinely closed. But return (**H-4**) + audit (**H-3**) regressions rode in. |
| H2 (playlist multi-day aggregation) | Aggregation correct; **active-job flagging dropped (H-2)**; return count wrong (**H-4**). |
| H3 (150¢ crash residual documented) | Documented — but residual is materially **larger** than stated (**B-2**); accept-decision inconsistent across §1/§2.4/§5. |
| H4 (`ledger_audit` RLS/grants + "insert cannot raise") | **Genuinely closed** for paths that insert (`fail_job`=service_role BYPASSRLS+grant; `settle_serve_model`=definer/postgres). Identity insert needs no sequence grant; force-RLS-no-policy blocks anon/authenticated. Airtight *for paths that can insert* (cancel paths can't — H-3). |
| H5 (serve lease-overlap bounded residual) | **Genuinely closed** — reclaim overwrites token, stale settle no-ops, releases ≤ reserves, per-owner cap holds. No double-refund. |
| M1 (serve return-type DROP+recreate) | `regprocedure` probe survives (arg signature unchanged). Grants restated. **But caller destructure mis-specified (M-2).** |
| M2 (marker plumbing → KEEP default) | Default direction correct; **plumbing can't see pre-send transcript/Gemini failures (H-1)** → KEEPs cases spec lists as RELEASE. |
| self: `fail_job` DROP+recreate | Correct — drop 5-arg, create 6-arg default-`true`, re-grant, one overload. **Body SQL still unspecified (M-3).** |
| self: `ledger_audit` BYPASSRLS grounding | Correct; matches `0006:9-10` + precedent. |

---

**Verdict: NOT CONVERGED** (2 Blocking, 4 High introduced/surviving).
