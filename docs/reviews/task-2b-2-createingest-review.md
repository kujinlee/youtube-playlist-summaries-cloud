# Claude Task Review — Stage 2b Task 2 (createIngest + guardrail matrix)

**Reviewer:** Claude (independent subagent). **Diff:** `5136d31..b867dae`. **Date:** 2026-07-11.

## Verdict (round 1)
- **Spec compliance:** ✅ — all 8 status codes handled; 401→UnauthorizedError (before res.ok); 422 reads {limit,found} with numeric guards + generic fallback; 429 defaults Retry-After to 60 when absent; 200 returns IngestResult raw; `503 {playlistId?}` intentionally not captured (no later-task consumer); `getJobStatus` import-drop confirmed benign (Task 3 export). No scope creep.
- **Code quality:** Approved. Independently re-ran jest 18/18 + tsc 0. Exact-string assertions, non-vacuous. Flagged 2 Minors.

## Miss vs. Codex (controller note)
Claude asserted "error-body parsing is safe" — but **missed the High** Codex caught: a valid-JSON `null` (or non-object) error body passes `res.json().catch(() => ({}))` and then `null.limit` throws a raw `TypeError`, bypassing the entire IngestError/ingestErrorMessage matrix. Dual-review value: Codex's adversarial null-body probe surfaced a genuine crash the approval pass rated safe.

## Claude Minors (align with Codex Medium/Low)
1. 422 missing/non-numeric path only exercised via `ingestErrorMessage` directly, not end-to-end through `createIngest` (Codex Medium — also misses the null crash).
2. `Number(h)` doesn't guard non-numeric/HTTP-date `Retry-After` → `NaN` in copy (Codex Medium).

## Controller adjudication
Fix the High (null/non-object body guard) + the Retry-After `Number.isFinite` guard + close both test gaps (422 null-body & stringy fields through createIngest; malformed Retry-After). Re-review both per iterative re-review (the High fix changes guardrail-matrix behavior). See `-codex.md` + `-v2-rereview.md`.
