# Reservation Release Lifecycle Spec v6 — Codex Round-6 Adversarial Re-Review

**Reviewer:** Codex (gpt-5.5), independent
**Artifact:** `docs/superpowers/specs/2026-07-15-reservation-release-lifecycle-design.md` (v6)
**Round:** 6 (re-review of v6 after round-5 NOT CONVERGED)
**Verdict:** **CONVERGED** — no Blocking / High / Medium / Low.

---

## Findings
**Blocking:** None. **High:** None. **Medium:** None. **Low:** None.

**No surviving concrete under-count in v6.**

## Why it converges
The job-scoped latch closes the round-5 root cause: §3.1/§5 make the runner release only when `classify(err) === 'release' && !billing.metered`, and the live spec says the latch flips at any Gemini response body. That covers the real code paths:

- `generateJson` body returned before parse/truncation failure, then later 429/503 → **KEEP**.
- `generateSummary` outer quality loop `i=0` returns a metered imperfect summary, `i=1` throws 503 → **KEEP** (the round-5 B5-1 case).
- `transcribeViaGemini` returns segments, then summary/dig fails with 503 → **KEEP** (R5-B1/M5-1).
- `generateDig` body returned / typed `GeminiHttpError` later → KEEP if metered; RELEASE only a clean 429/503 with no body.
- `generateMagazineModel` body returned then section-count/write failure → **KEEP**.
- retry requeue, reaper, and cancel paths remain consistent: requeue/reaper do not release; queued cancel releases; active/cancelled-after-run keeps.

## Consistency
Live §1/§2.4/§3.1/§5/§6/§7/§8/§9 agree on `{429,503}` only, connection/DNS → KEEP, and no live stale `maybeMetered` release rule. Historical change-log references (§12–16) are clearly historical.

**CONVERGED**
