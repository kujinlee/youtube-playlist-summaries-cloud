# Plan Re-Review v4 (Round 4, focused delta) — Summary Section-Timestamp Guarantee

**Artifact:** plan v4 (`0da7ccd`) · **Reviewers:** Codex `gpt-5.5` + Claude (independent) · **Date:** 2026-07-15
**Outcome:** ✅ **CONVERGED — 0 Blocking / 0 High from both.** This round is the Post-Plan gate.

Severity trail across the loop: **v1 4B+4H → v2 2B+1H → v3 0B+1H → v4 0B+0H.**

## Both reviewers verified the v4 delta is GENUINE (traced against code)
- **End-canonicalization repairs overlap:** `[## A ▶208–369, ## B missing, ## C ▶369–1000]` → allocator `[208,288,369]`; A **rewritten** to `208–288` (end = B's start, overlap gone), B inserted `288–369`, C `369–1000` byte-identical → kept. `parseSections(out)`: unique, strictly increasing, all `endSec > startSec`.
- **Byte-identity — no false negatives (Claude, proven):** both `resolveTranscriptTokens` (`parse.ts:179`) and the finalizer build lines via the *same* `timestampLine(start,end,videoId)`, and the *same* `videoId` flows to both in `generateSummary` (`gemini.ts:356` and `:491`). `timestampLine` pins `(start,end)` injectively (URL `t=${start}s` + `formatTimestamp` label), so `lines[slot] === canonical` ⟺ start & end both unchanged. A stale/overlapping end is always a byte-difference → always rewritten; a good line is always kept.
- **Allocator minimal-bump (both, traced):** `[100,null,101]→[100,101,102]`, `[100,100,400]→[100,101,400]`, `[100,50,200]→[100,101,200]`, `[null,null,null]@1000→[498,748,874]`, `@2→[0,1,2]` — all strictly increasing + unique.
- **Last-section end** `max(videoDuration, start+1)`: `@D=2 → [0,1,2]`, last end `max(2,3)=3 > 2`. No `end<=start` survives.
- **No new re-rolls / money (Claude, proven):** the new `endSec>startSec` clause can only fail a doc that *already* fails uniqueness (real docs: interior end = next kept start > start; last end = videoDuration > start via candidate filter `parse.ts:137`). `TIMESTAMP_MISS_CAP=2` ceiling intact.
- **No dig-key churn:** a section rewritten only because a neighbor moved keeps its own `startSec` (only the end label changes).

## Remaining (non-gating) — applied as v4 refinements
- **Medium (Codex): plan over-claimed "canonicalize doc-wide."** The fast-path returns early on `sectionStartsComplete` (checks `end>start`, not `end==next-start`), so an already-complete doc with overlapping ends from an off-prompt **literal** `▶` isn't canonicalized. Cosmetic (startSec uniqueness holds), and the pipeline never emits literal `▶` (model emits `[[TS]]` tokens; `resolveTranscriptTokens` produces canonical ends). → **Applied:** narrowed the plan's stated guarantee + added a round-4 scope note (this case is out of scope).
- **Low (both): test `videoId` mismatch** (`L` used `'v'`, finalizer called with `'vid'`) left the `===canonical → keep` branch uncovered in the incomplete path (production is fine). → **Applied:** `L` now uses `'vid'`.
- **Low (Claude): the `endSec>startSec` clause is redundant-but-defensive** for the current wiring — kept as cheap insurance against a future non-canonical producer.

## Convergence (diminishing returns)
Round 4 returned no new Blocking or High from either reviewer — only a doc-clarity Medium and two test/robustness Lows, all applied or accepted. Per `docs/dev-process.md` (Iterative Re-Review → Stop), **this is the gate.** Proceed: notify human (Conditional AFK) → SDD implementation → whole-branch review → merge gate (human).
