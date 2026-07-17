# Reservation Release Lifecycle Spec v5 — Codex Round-5 Adversarial Re-Review

**Reviewer:** Codex (gpt-5.5), independent
**Artifact:** `docs/superpowers/specs/2026-07-15-reservation-release-lifecycle-design.md` (v5)
**Round:** 5 (re-review of v5 after round-4 NOT CONVERGED)
**Verdict:** **NOT CONVERGED** (1 Blocking + 1 High — both under-count, both classifier-completeness)

---

## Blocking

### C5-B1 — Cross-call metering is not carried to the classifier (under-count)
§3.1 spec:68/78/81, §5 spec:195; code `lib/ingestion/summary-core.ts:69,83`, `lib/transcript-source.ts:40`, `lib/gemini.ts:669`.

**Failure:**
1. Captions absent → `resolveTranscriptSegments` falls back to Gemini.
2. `CLOUD_TRANSCRIBE_FALLBACK_VERIFIED=true`; `transcribeViaGemini` **succeeds** and returns segments — a **billable** Gemini call.
3. Later, `generateSummary` throws a **first-attempt** `GoogleGenerativeAIFetchError.status=503` (or dig throws typed `GeminiHttpError.status=503`).
4. The v5 classifier sees only the final 503. `maybeMetered` aggregates retry history **inside** `generateJson`/`transcribeViaGemini`/`generateDig` only — it does **not** remember that an earlier, *separate* transcription call succeeded.
5. Classifier → `release`; runner → `p_billable_succeeded=false`; ledger releases 150¢ though transcription already billed → **under-count.**

Directly contradicts §3.1's own class-C row ("billable transcription fallback succeeded before a later step threw → KEEP") — the rule is stated but not *implementable* from the final error alone.

**Direction:** a **cross-call billable marker**. The cleanest is a **job-scoped positive flag** (`billableCallSucceeded`) set the moment *any* Gemini call — transcription, summary, dig, magazine — returns a response; the release decision becomes `classify(finalErr)==='release' AND NOT billableCallSucceeded`. This subsumes the within-call `maybeMetered`. Alternatively `resolveTranscriptSegments` returns `source:'gemini'`/`billableSucceeded:true` and later errors are marked `maybeMetered=true`.

---

## High

### C5-H1 — Live behavior table still says serve connection failures RELEASE (stale contradiction, under-count)
§7 spec:354 (behavior 17).

**Failure:** §3.1 correctly classifies connection/DNS errors as ambiguous → KEEP, but **behavior 17 still lists `connection` under the class-A serve release trigger**. If the implementation/tests follow behavior 17, `settle_serve_model(token, released=true)` refunds 6¢ for a possibly-metered serve → under-count.

**Direction:** remove `connection` from behavior 17's class-A serve trigger (align with §3.1's dropped connection branch).

---

## Medium / Low
None.

**Verdict: NOT CONVERGED.**
