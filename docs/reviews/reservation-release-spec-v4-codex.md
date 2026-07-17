# Reservation Release Lifecycle Spec v4 — Codex Round-4 Adversarial Re-Review

**Reviewer:** Codex (gpt-5.5), independent
**Artifact:** `docs/superpowers/specs/2026-07-15-reservation-release-lifecycle-design.md` (v4)
**Round:** 4 (re-review of v4 after round-3 NOT CONVERGED)
**Verdict:** **NOT CONVERGED** (1 Blocking + 1 High — both classifier implementability against the real error-production paths)

---

## Blocking

### C4-B1 — Classifier can RELEASE after an earlier metered retry attempt
§3.1 lines 72-77; §5 lines 186-196; `lib/gemini.ts:245-270,258-260,389-394,543-554,665-689`.

**Failure:** `generateJson` attempt 1 reaches Gemini, receives a **billable** response, then fails locally on `JSON.parse` / Zod / `assertNotTruncated`. The retry loop catches and continues. Attempt 2 gets a Google **503**. `generateJson` throws only `lastErr` (503) → `generateSummary`/`generateMagazineModel` wraps in `{ cause }` → §3.1 classifies 503 as class A → `p_billable_succeeded=false` / `settle_serve_model(released=true)`. **Real money was spent on attempt 1, but the reservation is refunded → under-count.** Same shape in `transcribeViaGemini` (metered attempt, then a final 503; `gemini.ts:689` preserves only the final error).

**Direction:** classification must consider **retry history**, not just the final error. A releasable failure requires **all attempts** positively not-metered. If any prior attempt reached a response, timed out, aborted ambiguously, or parsed/truncated locally, the final error must classify KEEP. Implement via a typed aggregate error carrying `maybeMetered=true` (or `attemptClasses[]`).

---

## High

### C4-H1 — Dig jobs bypass the SDK error shape, so class-A outage RELEASE is not implementable for dig
§2.4 lines 40-44; §3.1 lines 72-75; §7 behavior 26; `lib/job-queue/dig-handler.ts:99-110`; `lib/dig/generate.ts:243-276`; `supabase/migrations/0018_enqueue_dig.sql:22-24`.

**Failure:** three dig jobs reserve 150¢ each. Gemini REST returns 503 during an outage. `generateDig` retries transient statuses, then throws a generic `Error("generateDig: Gemini REST returned HTTP 503")` — **no `.status`, no structured cause** (`lib/dig/generate.ts:268-271`). The §3.1 classifier only releases Google errors carrying `.status`, `NonRetryableError`, or connection codes → this defaults to **KEEP**. With `dig_max_attempts=1`, each job dead-letters and keeps 150¢ at ~$0 spend. The v4 claim "N generations all hit Google 503 → all release" (behavior 26) is **false for dig generation** — which uses a hand-rolled REST helper, not the `@google/generative-ai` SDK.

**Direction:** either bring dig into the classifier contract (make `generateDig` throw a typed/status-bearing error for REST HTTP failures, preserve connection causes), or explicitly exclude dig from the v4 outage-closure claim and document the residual.

---

## Medium / Low
None.

## Round-3 fix check
B-2/§3.1 classifier — sound in principle but incomplete against retry history (C4-B1) and the dig REST path (C4-H1). B-1 serve, H-1 transcript wrapper, H-2/H-3/H-4 cancel RPCs, M-1/M-2/M-3, L-1/L-2 — no new finding.

**Verdict: NOT CONVERGED.**
