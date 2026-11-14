---
name: summary-section-timestamp-guarantee-state
description: "FIRES-WHEN: a summary section is missing its ▶ timestamp, or citing PR #21 / ensureSectionTimestamps — every ## section gets a unique, strictly-increasing startSec; MERGED 329b3b5, 2026-07-15, live-verified"
metadata:
  type: project
  originSessionId: 7746a733-7051-4952-85dd-526eb71dd21b
---

**MERGED — PR #21, merge commit `329b3b5`, 2026-07-15; live-verified the same day.** Every generated summary section
(`## N.` + `## Conclusion`) gets a valid `▶ [start–end](url?t=Ns)` with a UNIQUE, strictly-increasing `startSec`.
Forward-only: an old doc is fixed only when it is regenerated.

**Why it matters:** render gates dig-deeper / ask-AI / timestamp controls on `startSec !== null`
(`render-dig-deeper.ts`), and `startSec` IS the dig `sectionId` (blob key `dig/{base}/{sectionId}.r9.md`), so
uniqueness is load-bearing.

**Root cause:** Gemini emits own-line `[[TS:<index>]]` tokens after each `## ` heading; `resolveTranscriptTokens`
(`lib/transcript-timestamps.ts`) keeps only the strictly-increasing-offset LIS and **deletes** out-of-order token lines.
The old checks were doc-wide "≥1 ▶", so a single dropped section slipped through.

**Shipped design (2 layers, shared local+cloud core; `resolveTranscriptTokens` untouched → dig byte-identical):**
- `gemini.ts` scoreSummary index 3 → `sectionStartsComplete` (per-section, was doc-wide) — re-rolls within the existing
  MAX_SUMMARY_ATTEMPTS / TIMESTAMP_MISS_CAP=2 budget.
- `ensureSectionTimestamps` (`lib/summary-section-timestamps.ts`) full-doc normalizer: synthesizes a `▶` for any
  missing section with `startSec` allocated strictly between neighbours, and canonicalizes every line's end to
  `next start` (last = `max(duration, start+1)`); a line is kept iff byte-identical to canonical.

**Known-accepted follow-ups (not blockers):** off-prompt literal-▶ wrong-videoId canonicalization (Codex Medium, scoped
out); +1 re-roll for imperfect-timestamp videos (bounded); unsorted-segments hardening; warn-count dedup.

**⚠ Unresolved observation (local cloud, 2026-07-15):** re-enqueuing a `summary` job for an already-ingested video —
with both the `enqueue_job` join-gate and the handler skip-gate cleared — completed in ~10s WITHOUT regenerating (blob
`updated_at` unchanged, yet `persist_summary` re-promoted and bumped `processedAt`). Not root-caused; worked around by
running `summaryCore` directly. Investigate if cloud regen-on-demand is ever needed. Also `spend_ledger.reserved_cents`
is add-only locally — reset today's row before re-enqueueing ([[local-cloud-validation-run]]).

## History
- Trigger: video `9nh8TQRcYD0` section 2 shipped with no `▶`. Live re-run of merged code (real Gemini, 22s): all 7
  sections got a `▶`, startSecs `[14,59,166,371,578,730,1012]`. Local-Supabase blob refreshed by `summaryCore`; old dig
  blobs keyed by old startSecs (e.g. 208) were orphaned and regenerate on demand.
- Plan review converged over 4 rounds: v1 4B+4H (dropped the original Layer 1, user-confirmed) → v2 2B+1H → v3 0B+1H
  (stale endSec) → v4 end-canonicalization `0da7ccd`, 0B/0H both. Reviews
  `docs/reviews/plan-summary-section-timestamp-guarantee-{v1-review,v2-rereview,v3-rereview,v4-rereview}.md`.
- SDD T1 `de9aacb`, T2 `a92e002`, T3 `3fb91b4`, T4 `a62a853`; whole-branch dual review 0B/0H (`d4f9856`); 2319/2319
  tests, tsc 0.
