# Plan Re-Review v2 (Round 2) — Summary Section-Timestamp Guarantee

**Artifact:** plan v2 (`32dafa3`) · **Reviewers:** Codex `gpt-5.5` + Claude (independent) · **Date:** 2026-07-15
**Outcome:** **NOT converged** — 2 Blocking + 1 High remain, all rooted in one design gap. Both reviewers converged on the same defects (strong signal). v3 required.

## Verified genuinely fixed (both reviewers)
- **B4/H1/L6** (checker vs render parser): ✅ real fix — checker/finalizer reuse `parseSections`. Claude traced `headingLineIndices` == `parseSections` enumeration (order/count/fence/preamble/EOF) — no drift.
- **H2** (test un-runnable): ✅ Task 4 under `tests/lib/`, `npm test`-discoverable, no Supabase.
- **B2/H3** (Layer-1 instances): ✅ dissolved — `resolveTranscriptTokens` untouched, dig byte-identical; `parse.ts` change is export-only.
- **M1/M4** (money): ✅ honest — per-section criterion raises expected 1→2 attempts for single-miss videos; `TIMESTAMP_MISS_CAP=2` only *breaks*, ceiling stays `MAX_SUMMARY_ATTEMPTS`.
- **L5/L1/L2**: ✅ addressed.

## Remaining — carried into v3

### R2-B1 (both) — `spreadStarts` still emits `>= hi` → collision with an unchanged known `▶`; and its test is unsatisfiable.
`spreadStarts(100,101,1)` traces to `[101]` (the final `if(v<=prev)v=prev+1` overrides the `v=hi-1` clamp). Failure: sections `[A@100, B missing, C@101]` → B synthesized 101, C's line **unchanged** at 101 → duplicate dig key `dig/{base}/101.r9.md`. The array-only defensive check is blind to it (it never sees C's rendered line). Also the Step-1 test asserts an integer strictly inside `(100,101)` — none exists → RED can't go GREEN.
→ **v3:** delete `spreadStarts`; the finalizer must be able to **rewrite** the colliding known line.

### R2-H1 (Claude) — `Math.floor` collisions among EXISTING starts ship silently; "unique by construction" is false.
`resolveTranscriptTokens` keeps the LIS of float offsets (strict `<`) then emits `Math.floor(offset)` (`transcript-timestamps.ts:156`). Segments `@100.2` and `@100.9` are both kept but both floor to `100` → two existing `▶` with `startSec=100`. All sections present → `everySectionHasTimestamp` true → finalizer no-ops → collision ships. The finalizer never runs when all sections have a `▶`, and never rewrites existing lines, so it cannot enforce global uniqueness.
→ **v3:** the score criterion must check **uniqueness + strict monotonicity** (not just presence); the finalizer must run and repair (rewrite) whenever the full start sequence isn't unique+increasing.

### R2-M1 (Claude) / root cause — the finalizer never rewrites an existing `▶` line.
The defensive bump mutates only the in-memory `starts` array; the rendered known line is byte-identical by design, so any needed correction is lost, and array-based checks report clean while the document ships a collision. This is the shared mechanism behind R2-B1 and R2-H1.
→ **v3:** finalizer rewrites existing lines as needed (safe — no dig content exists at generation time).

### High (Codex) — M3 test list incomplete.
`tests/lib/gemini-response-schema.test.ts` (single `mockResolvedValueOnce`, Conclusion lacks a timestamp) will trigger the extra re-roll and run out of queued responses.
→ **v3:** comprehensive fixture audit (per the `summary-truncation-resilience-stage2` precedent: migrate all `generateSummary` fixtures to timestamp-complete or no-segments), not just the 3 named rewrites.

### Mediums
- (Codex) spec §9 behaviors #1-3 stale after Layer-1 drop (require keeping out-of-order tokens / a dig golden). → **v3:** spec addendum.
- (Codex) the "end > start" test only checks `t=` starts, not `endSec`. → **v3:** assert `s.timeRange!.endSec > s.timeRange!.startSec` via `parseSections`.

### Lows
- (Claude R2-L3) `tests/lib/gemini.test.ts:366-375` asserts `not.toHaveBeenCalledWith('[timestamp-miss]')` → vacuous after the rename; clean it up.
- (Claude R2-L1) `startSec=0` edge / `-1` sentinel — add an assertion.
- (Codex Low) assert `headings.length === sections.length` before inserting (defensive vs future parser drift).

## v3 design (folds all of the above)
A pure `allocateSectionStarts(known[], firstStart, videoDuration)` produces a unique, strictly-increasing integer start for every section (keeps the model's real value when it fits after `prev` and leaves room for the tail; synthesizes otherwise). The finalizer applies it and **rewrites** any existing `▶` line whose start changed + inserts missing ones. `sectionStartsComplete` (presence + uniqueness + strict increase) is the Layer-2 score criterion and the finalizer's fast-path guard. Convergence check: round 3 re-review.
