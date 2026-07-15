# Plan Re-Review v3 (Round 3) — Summary Section-Timestamp Guarantee

**Artifact:** plan v3 (`a726bf6`) · **Reviewers:** Codex `gpt-5.5` + Claude (independent) · **Date:** 2026-07-15
**Outcome:** **NOT converged** — 0 Blocking, **1 High** (stale `endSec`). Severity dropped every round (4B → 2B → 0B). The hard invariant (unique, strictly-increasing `startSec`) is **genuinely fixed** — both reviewers verified by hand-trace.

## Genuinely fixed (both reviewers, traced)
- **R2-B1** (spreadStarts overshoot): `spreadStarts` deleted; `allocateSectionStarts` traced on all 8 inputs (`[100,null,101]`, `[100,100,400]`, `[100,50,200]`, `[null,null,null]@1000`, `@2`, all-good…) → **every result strictly increasing + unique**. The finalizer **rewrites** the colliding known line (not just the array).
- **R2-H1** (Math.floor float→int collision): `sectionStartsComplete` returns false on `startSec <= prev` → re-roll; finalizer runs even when all sections have a `▶` and rewrites the duplicate.
- **R2-M1**: the `replace` map genuinely overwrites existing `▶` lines in the rebuild.
- **`sectionLayout` ↔ `parseSections` parity (the flagged new risk): NO DRIFT** (Claude, structural proof): both walks check `isFenceLine` first and toggle `inFence` identically at every line index, so section boundaries and the `tsLine` slot can't desync; `layout[idx]` ↔ `sections[idx]` positionally always. Malformed-`▶`, `---`-before-`▶`, fence-before-`▶`, no-body, EOF all verified: a well-formed `▶` never yields `tsLine=null` (no duplicate insert), a malformed `▶` is `replace`d in place.
- **Money/loop**: stricter criterion only converts complete-but-colliding docs into ≤`TIMESTAMP_MISS_CAP=2` re-rolls; ceiling `MAX_SUMMARY_ATTEMPTS` intact; healthy videos still early-return.

## The remaining High (Codex) — stale/invalid `endSec`
The finalizer keeps a section's line "unchanged" when its `startSec` is unchanged, but `parse.ts:32-36` reads `endSec` from the **label**, which goes stale when a neighbor changes:
- **Insert overlap:** `[## A ▶208–369, ## B missing, ## C ▶369–…]` → allocator `[208,288,369]`; A kept byte-identical → still parses `208–369`, **overlapping** the inserted B at 288. A's end should become 288.
- **Duplicate-floor `end==start`:** `[## A ▶100–100, ## B ▶100–…]` → B's start rewritten, A kept → A left `endSec==startSec`.
- **Broken test:** the Task-2 helper `T(n)=▶ [0:00–0:00](…t=${n}s)` parses `endSec=0`, so the `endSec > startSec` test fails for kept lines — the stated PASS isn't reachable.
→ **v4 fix:** finalizer canonicalizes every section's line to `timestampLine(starts[idx], endFor(idx), videoId)` where `endFor = starts[idx+1]` (or `max(videoDuration, starts[idx]+1)` for last); keep only byte-identical lines (still a no-op for good docs). `sectionStartsComplete` also checks `endSec > startSec`. Test fixtures use real `timestampLine` labels.

## Mediums / Lows → v4
- **(Codex M1) tight-gap editorial drift:** `[100,null,101]→[100,101,550]`; a too-low known value should bump minimally to `prev+1` → `[100,101,102]`. Allocator: add `else if (k!==null && k<lower) s=lower`.
- **(Codex M2 / Claude L1) pathological last end:** `endSec = max(next-or-duration, start+1)`.
- **(Claude L2)** the defensive `[summary-section-ts-degenerate]` loop is unreachable (allocator proven strictly-increasing) — keep as belt-and-suspenders, don't test for the warn.
- **(Claude L3)** fixture migration verified: the only single-`mockResolvedValueOnce` fixture that now exhausts its queue is `gemini-response-schema.test.ts:55` — already named in the plan. No un-flagged exhaustion.
- **(Claude L4)** guard the synth warn on `bad > 0` (avoid "normalized 0 sections" on a zero-section body).
- **(Codex L1)** broaden the audit command to `rg "generateSummary\(" tests`.

## Convergence
Round 3: 0 Blocking, 1 High (endSec) + minor. The endSec fix is contained (finalizer end-canonicalization). → v4, then a focused round-4 re-review scoped to the endSec canonicalization + allocator minimal-bump.
