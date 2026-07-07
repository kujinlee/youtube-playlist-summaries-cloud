# Stage 1E-a Spec — Codex Adversarial Review

**Reviewer:** Codex (`gpt-5.5`, session `019f3ad4-4751-7d81-b47b-b44eb206cd85`), read-only adversarial pass.
**Target:** `docs/superpowers/specs/2026-07-06-stage-1e-a-durable-job-queue-design.md` (v1).
**Date:** 2026-07-07.

## Blocking

1. **Missing lease fencing → double execution + stale finalization.** Job `active`/`locked_by=w1`, lease expires, sweep requeues (`attempts+=1`), `w2` claims, slow-but-alive `w1` calls `complete()` → overwrites `w2`. Only `heartbeat` carries `workerId`; `complete`/`fail` do not. **Fix:** `claim` returns a lease token/version; `complete`/`fail`/`heartbeat` fence on `id + locked_by + lease_token + status='active'`, fail closed on 0 rows.
2. **RLS does not authorize its own enqueue/cancel writes.** `SELECT`-only policy + `SECURITY INVOKER` insert → denied (convention 0002 is `for all ... with check`). Also parent §7 requires **anonymous guest jobs**, but spec grants only `authenticated` (0006 convention is `anon, authenticated, service_role`). **Fix:** `FOR SELECT` + `FOR INSERT WITH CHECK (owner_id=auth.uid())` + owner-scoped update for cancel; grant `anon` where guest enqueue is required.
3. **Enqueue idempotency under-specified / unsafe vs partial unique index.** No atomic statement given; check-then-insert races; `ON CONFLICT (cols)` won't infer a partial index without the predicate; `DO NOTHING RETURNING` returns no row; follow-up `SELECT` can miss. **Fix:** specify exact RPC — `ON CONFLICT (...) WHERE status IN ('queued','active') DO ... RETURNING`, single transaction, deterministic joined-row return + vanished-row fallback.
4. **Freeing completed idempotency keys contradicts source-of-truth + quota.** Completed frees the key → same key re-enqueues → re-runs paid Gemini, regenerates a source-of-truth blob, 1D may recharge (parent §8: charged once per key; §4: summary MD is non-regenerable). **Fix:** split "live job uniqueness" from "artifact already produced"; completed returns/reuses; only failed/cancelled/dead_letter free spend/idempotency; require version bump to legitimately re-run.

## High

1. **`attempts` double-count.** Sweep reclaim (`attempts+=1`) and then `w1`'s `fail()` (`attempts+=1`) for the same execution. **Fix:** increment once per lease token; sweep and fail mutually exclusive (via fencing).
2. **State-transition guards unspecified.** Terminal `cancelled` job can be overwritten by a stale `complete()`. **Fix:** guarded `WHERE status=...` transition table; terminal states immutable except explicit admin/retry.
3. **Custom queue drops pg-boss obligations.** §9 required full lifecycle + §8 queue-depth cap; spec overrides pg-boss but doesn't replace monitoring/retention/queue-depth/graceful-shutdown. **Fix:** specify equivalents or explicitly defer each with an owner.
4. **Missing hot-path indexes.** Claim (`status='queued' AND run_after<=now() ORDER BY created_at`) and sweep (`active AND lease_expires_at<now()`) seq-scan. **Fix:** partial indexes `(run_after, created_at) WHERE status='queued'`, `(lease_expires_at) WHERE status='active'`, plus owner/status for polling.

## Medium

1. **Cancel semantics allow cancelled work to complete.** `complete` writes `completed` even with `cancel_requested=true`. **Fix:** check cancel before/after expensive steps; `complete` conditional on `cancel_requested=false`.
2. **Cloud concurrency diverges from local `activeByFolder`.** Local serializes ingestion per output folder; cloud idempotency is only per `(owner,document,artifact,version)`, so two jobs for different artifacts in the same playlist mutate shared state concurrently. **Fix:** state whether cloud serializes per-playlist, or relies on 1C transactional methods; make the boundary explicit.
3. **Dead-letter lifecycle incomplete.** No retention/visibility/retry-admin/redaction. **Fix:** define them (or defer explicitly).

## Low

1. **`attempts < max` increment-timing ambiguity.** Define `attempts` precisely; single `attempts = attempts + 1`, compare new value to `max_attempts`.
