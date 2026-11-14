---
name: reservation-release-slice-state
description: "FIRES-WHEN: citing PR #22 or the reserve-to-release lifecycle — Reservation reserve→release lifecycle money-path slice — ✅ MERGED to master (PR #22, merge 54e0591, 2026-07-17); spend-aware spend_ledger release shipped; 2 money Highs (H1, H-R2-1) found+fixed via 3-round whole-branch dual review"
metadata:
  type: project
  originSessionId: 7746a733-7051-4952-85dd-526eb71dd21b
---

**✅ MERGED to master — PR #22, merge commit `54e0591` (2026-07-17).** Branch `feat/reservation-release-lifecycle`,
deleted. Migration **0020_reservation_release.sql**. This is a history record; nothing here is in flight.

**What it fixed:** `spend_ledger.reserved_cents` was add-only, never released, so ~3 cheap failures self-DoS'd all
users until UTC midnight. Failed/cancelled generation + serve attempts now return budget (release-only, spend-aware),
which unblocked the Fly.io deploy. See [[local-cloud-validation-run]].

**Open residuals at merge (not blocking):**
- live-Gemini verification of the class-A {429,503}-bills-nothing premise before flipping
  `CLOUD_GEMINI_RELEASE_VERIFIED` (§9 gate, `docs/reservation-release-live-gate.md`);
- the deferred settle slice closes spec §2.4b/§2.4c crash/requeue residuals (4a rare class-B timeout-after-metering,
  150¢; 4b worker-crash-before-terminal, 150¢, count-unbounded — mitigated by graceful drain);
- M1 doc-only Medium (a never-metered attempts>=1 requeue cancelled-while-queued is now KEPT) + 5 deferred Lows.
  T14/H-R2-1/M1 bite only at operator-raised `summary/dig_max_attempts>=2` (shipped = 1 CHECK → latent as shipped).

**Key design (money path, user-approved):** RELEASE iff `releaseGateOpen() && classifyGeminiFailure(err,ourSignal)==='release'
&& !billing.metered`. The classifier releases ONLY a pre-send NonRetryableError or Google/dig HTTP status ∈ **{429,503}**
(never 500/502/504), via a cause-chain walk. A **billing latch** (job-scoped) is set at the `model.generateContent`
primitive before parse. Guarded decrement + `ledger_audit` (never a silent clamp); day-correct via
`created_at::date at utc`; the reaper never releases; serve uses a per-attempt token + `settle_serve_model`; prod gate =
compile-time const false (test-only env override).

## History

- **Phase 1** spec converged in 7 rounds, user-approved 2026-07-16:
  `docs/superpowers/specs/2026-07-15-reservation-release-lifecycle-design.md` (v7, `b123b49`).
- **Phase 2** plan converged 2026-07-16 (`ce1c499`, v5); Highs per round v1(1/2)→v2(2/0)→v3(1/1)→v4(0/0); every finding
  was test scaffolding — the money SQL was verified-closed since v1.
- **Phase 3** 12 tasks via subagent-driven development (2026-07-16), `ce1c499`→`2fd29c6`; unit 2336/2336.
- **Whole-branch dual review, 3 rounds (2026-07-17):** R1 found **H1** (per-attempt latch vs per-job reservation
  under-count) → T13 durable `jobs.ever_metered`; R2 found **H-R2-1** (ever_metered persisted lazily, lost on lease
  loss → reaper requeue → un-gated cancel under-counts) → T14 cancel-release gated on `attempts=0`; R3 both halves
  0 Blocking/0 High, "no 3rd under-count path" (4 gated release sites). Integration 421 pass, reservation-release 32/32.
  Reviews: `.superpowers/sdd/whole-branch-{codex,claude}-round{1,2,3}.md`.
- At the time, Codex ran as a raw `codex exec` from the coordinator; that recipe is superseded by
  `scripts/codex-review.py` — see [[running-codex]], [[process-conventions]].
