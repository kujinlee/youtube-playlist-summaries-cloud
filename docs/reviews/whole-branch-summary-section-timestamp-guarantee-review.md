# Whole-Branch Review — feat/summary-section-timestamp-guarantee (final, pre-merge)

**Range:** `a4c251c..a62a853` (code: 7 files, +388/-28) · **Reviewers:** Codex `gpt-5.5` + Claude/Opus (independent) · **Date:** 2026-07-15
**Verdict:** ✅ **MERGEABLE — 0 Blocking / 0 High from both.** All 4 SDD tasks implemented + individually reviewed clean; this whole-branch pass verifies the assembled code delivers the guarantee in the real pipeline.

## Emergent correctness — verified by BOTH reviewers
- **Reaches both persisted paths.** `ensureSectionTimestamps` runs inside `generateSummary` (the single chokepoint, `gemini.ts:385`). Local `pipeline.ts → summaryCore → generateSummary`; cloud `summary-handler.ts → generateSummary`. Both persist `summaryCore.mdContent`.
- **No post-generation mutation reintroduces a bad `▶`.** Only `padDividers` (touches only `---`/blanks, fence-aware, never `▶` lines) + Quick Reference callout (metadata region) run after. An inserted `▶` (first non-blank body line) is still consumed correctly by `parse.ts:extractTimeRange`. Guarantee survives to disk.
- **`videoId` byte-identity holds in production.** Same `videoId` feeds `resolveTranscriptTokens` and `ensureSectionTimestamps`; both build lines via the one `timestampLine(start,end,videoId)` → no missed keep, no spurious rewrite.
- **Dig premise intact.** `sectionId = timeRange.startSec`; unique startSec is exactly what prevents `dig/{base}/{sectionId}.r9.md` cross-wiring. `resolveTranscriptTokens` + all dig files byte-unchanged; `parse.ts` change export-only.
- **Invariant end-to-end.** Output round-trips through `parseSections` and re-satisfies `sectionStartsComplete` (unique + strictly-increasing startSec, `endSec > startSec`) — including h:mm:ss labels.
- **Hygiene.** `hasTimestamp`/`warnTimestampMiss` fully removed from lib; no now-vacuous tests. Full suite 2319/2319, tsc 0.

## Findings — all known-accepted (no code change before merge)
- **Medium (Codex): off-prompt literal-`▶` with a wrong `videoId` bypasses canonicalization.** A doc already `sectionStartsComplete` but carrying a model-authored literal `▶` line (the prompt asks for `[[TS]]` tokens, never `▶`, so this is off-contract) with a wrong-video URL keeps that URL. Dig still works (startSec correct from `t=`); cosmetic link issue only. **Accepted** — same class scoped out in the round-4 plan review (narrow-the-claim). The suggested "always canonicalize on hasSegments" fix was weighed in round 4 and declined (churns converged code for a near-impossible input). Deferred; owner: this slice's future maintenance.
- **Low (Claude L1): +1 paid attempt for imperfect-timestamp videos.** The per-section criterion (vs old "any `▶`") means a complete-but-collided/dropped-token summary re-rolls up to `TIMESTAMP_MISS_CAP=2` before synthesis. Intentional and bounded (ceiling unchanged); the whole slice trades a capped re-roll for the guarantee. Accepted.
- **Low (Claude L2): `firstStart`/`videoDuration` assume sorted segments.** Real YouTube transcripts are ascending; and even unsorted input only causes editorial drift (invariant preserved by the belt-and-suspenders bump + last-section `max`). Accepted; optional hardening = `min/max` over offsets.
- **Low (Claude L3): the `bad`-count warn re-implements the invariant scan.** Observability-only nit; a future invariant change must be mirrored. Accepted.

## Bottom line
Merge-ready. The per-section unique/monotonic `startSec` + `endSec > startSec` guarantee holds end-to-end through both persisted pipelines and reaches the dig blob-key + render gates the slice exists to satisfy. **Push / PR / merge remains the human gate.**
