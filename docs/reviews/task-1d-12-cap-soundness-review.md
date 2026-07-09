# Task 1D-12 Review — Drift-proof cap-soundness guard test

**Commit:** 233fae6 · **Base:** 66cb82a · Claude SDD task review (recompute-faithfulness + isolation focus).

## Spec Compliance: ✅ Approved

- Inline recompute from raw `@/lib/gemini-cost` constants; primary assert does NOT call `perRunWorstCents` (helper only cross-checked secondarily) — per brief.
- Asserts `summary_est_cents >= ceil(worst) * summary_max_attempts` against the LIVE `guardrail_config`, and `SUMMARY_MODEL === TRANSCRIBE_MODEL === PRICED_MODEL`.
- Numbers: audio=57600, video=242400 → transcribe 64.032 + summary/quickview 50.952 = 114.984 → ceil 115; 150 ≥ 115×1 ✅. tsc clean (only T13's producer-roundtrip remains).

## Focus 1 — Recompute FAITHFUL (traced to enforcement)
Reviewer verified pass-counts against actual loops: `TRANSCRIBE_MAX_PASSES=3` = `transcribeViaGemini` retry loop; `SUMMARY_MAX_PASSES=12` = `generateSummary`(4) × `generateJson`(3); `QUICKVIEW_MAX_PASSES=3` = `extractQuickView`. `MAX_TRANSCRIPT_INPUT_BYTES` is a REAL enforced cap (`summary-core.ts` `truncateSegmentsToByteCap` before every summary/quickview pass), not aspirational. Formula matches migration 0011's stated est≥worst×attempts contract. No divergence between test derivation, helper, and enforced caps. (Noted safe-direction overestimate: transcribe model adds prompt-overhead on top of the 300k input cap → 304k modeled > 300k enforced; conservative, pre-existing in gemini-cost.ts, correctly mirrored.)

## Focus 2 — Test isolation: Accept-as-is
Only 4 integration files touch `guardrail_config`: schema (read-only), cost-guardrails (beforeEach resets the 3 relied-on cols to defaults; no body-level mutation of them), summary-handler (mutates max_duration_seconds in try/finally with restore), cap-soundness (read-only). Under `--runInBand` with no custom sequencer, the live row is always canonical when cap-soundness runs. A `beforeAll` pin would defeat the test's purpose (validate the LIVE config) and duplicate the migration's source-of-truth → NOT recommended.

## Findings
- Critical/Important: none.
- **Minor (→ whole-branch fix wave):** add an in-file comment documenting the cross-file `guardrail_config` state dependency (turns a silent coupling into a grep-able one). Non-blocking; reviewer explicitly said not a reason to withhold approval.

## Verdict: Approved.
Codex adversarial pass deemed disproportionate (read-only guard test, no new production code); whole-branch review covers it again.
