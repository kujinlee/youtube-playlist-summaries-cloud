# Reservation Release Plan v1 — Codex Round-1 Adversarial Review

**Reviewer:** Codex (gpt-5.5), independent, run from coordinator (sandbox disabled).
**Artifact:** `docs/superpowers/plans/2026-07-16-reservation-release-lifecycle.md` (v1).
**Verdict:** **NOT CONVERGED** — 0 Blocking, 1 High, 3 Medium, 2 Low.

---

## Blocking
None.

## High

### H1 — retryability doesn't walk the cause chain, so a WRAPPED NonRetryableError classifies `release` but requeues (never releases)
`plan:1547` + `lib/job-queue/worker-runner.ts:62` + `lib/transcript-source.ts:60`.
The plan preserves `NonRetryableError` only in the `.cause` chain (Task 9 wrap), and the classifier walks that chain → `'release'`. But the runner leaves `retryable = !(e instanceof NonRetryableError)`, which is **`true`** for a wrapped `NonRetryableError` (the top-level is a generic `Error`). So `p_retryable=true` → `fail_job` requeues (`v_new='queued'`) → the release SQL explicitly refuses a `queued` transition (behavior 6) → the 150¢ is held while the job burns attempts, instead of releasing terminally. Concrete: a caption-less cloud video with the Gemini fallback disabled (`gemini.ts:657` fail-closed `NonRetryableError`) wrapped by `resolveTranscriptSegments`.
**Fix:** the runner's retryability must also walk the cause chain for `NonRetryableError` (a shared `isNonRetryable(err)` cause-walk), so a pre-send positive not-metered failure sets **both** `retryable=false` and `billableSucceeded=false`.

## Medium

### M1 — Task 10 runner tests point at the in-memory harness but assert `spend_ledger` deltas
`plan:1497`. `worker-runner-runtime.test.ts:22` never touches Postgres. A runner that omits `billableSucceeded` still passes a fake-queue test unless the test asserts the exact `queue.fail(..., { retryable, billableSucceeded })` call.
**Fix:** unit-assert the exact `fail` args for all three branches (release / metered-keep / gate-off-keep) with a spy queue; leave the real ledger delta to the DB-backed `fail_job` test (Task 2).

### M2 — Task 9 billing-only call drops the latch (guard is `signal || caps`)
`plan:1436` + `lib/transcript-source.ts:41`. `resolveTranscriptSegments` forwards opts only when `signal || caps`; a billing-only call silently drops it — violates the "every opts object" invariant (not immediately under-counting since cloud handlers pass `signal`/`caps`).
**Fix:** guard `opts?.signal || opts?.caps || opts?.billing`.

### M3 — planned integration tests call `enqueue_job` with the WRONG signature
`plan:707` + `0011/0018`. Real 8-arg signature is `enqueue_job(p_owner_id uuid, p_playlist_id uuid, p_video_id text, p_section_id int, p_job_kind text, p_job_version text, p_payload jsonb, p_enqueue_ip inet)`. The plan used `p_kind`/`p_version`/`p_idem_key` and omitted `p_job_kind`/`p_job_version`/`p_enqueue_ip` and `durationSeconds` in the payload (rejected by the duration guardrail `0018:42`).
**Fix:** use the real signature + a valid `durationSeconds` payload (mirror `cancel-job-rpc.test.ts:17` — `p_section_id: -1, p_job_kind:'summary', p_job_version:'3.3', p_payload:{ durationSeconds:100 }, p_enqueue_ip:null`).

## Low

### L1 — serve "metered-then-503" test stubs `generateMagazineModel`, not the real primitive latch
`plan:1609` + `gemini.ts:545`. Mocking the outer function won't verify the real `generateJson` primitive latch → possible false-green.
**Fix:** assert `generateMagazineModel` receives the same latch object and mutate it in the mock, or drive the test through `generateJson`.

### L2 — `ledger_audit` lockdown test masks permission-denied with `data ?? []`
`plan:72`. Since no grant exists for authenticated by design, PostgREST may return permission-denied and the test still passes without proving the surface.
**Fix:** assert the expected error, or explicitly accept "no data OR permission denied."

---

**VERDICT: NOT CONVERGED** (1 High, 3 Medium, 2 Low).
