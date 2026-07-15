# Plan Review v1 — Summary Section-Timestamp Guarantee

**Artifact:** `docs/superpowers/plans/2026-07-15-summary-section-timestamp-guarantee.md` (as of `ff3cbef`)
**Reviewers:** Codex `gpt-5.5` (independent) + Claude subagent (independent) · **Date:** 2026-07-15
**Outcome:** NOT ready — multiple Blocking. Both reviewers + the plan's own design note converge on **dropping Layer 1**. User confirmed: **drop Layer 1.**

Both reviewers ran independently against the plan, spec, and live code. Their Blocking findings overlap almost exactly (a strong convergence signal).

---

## Consolidated findings & dispositions

### Blocking

**B1 — `spreadStarts` overshoots the upper anchor → duplicate `startSec` (dig-key collision) + inverted `▶` range.** (Both reviewers.)
The degenerate fallback `if (v <= prev) v = prev + 1` marches upward with **no clamp against `hi`**: `spreadStarts(10,12,5)→[11,12,13,14,15]` (12=`hi`, 13-15>`hi`); `spreadStarts(100,101,1)→101` = the next section's start → **two sections share `startSec` → same dig blob key `dig/{base}/101.r9.md`**. Also inverts the label range (`end ≤ start`). Lives in **Layer 3 too**, so it must be fixed regardless of Layer 1.
→ **Fix (v2):** `spreadStarts` returns values **strictly inside `(lo, hi)`** (hard exclusive upper bound); when the interval lacks room (`hi - lo - 1 < count`), detect explicitly (warn) rather than silently colliding. Tests assert every synthesized start ∈ `(lo, hi)` **and** the full anchors+synthesized set is unique + strictly increasing, incl. a 1-second-gap and an N-in-a-tiny-gap fixture.

**B2 — (Codex) multiple dropped tokens between close anchors go backwards/collide.** Same root cause as B1 (Layer-1 instance). → **Dissolved by dropping Layer 1**; the Layer-3 instance is covered by the B1 fix.

**B3 — (Codex) `ensureSectionTimestamps` checks presence only, not uniqueness/monotonicity of existing `▶`.**
→ **Fix (v2):** the finalizer is the single authority for the invariant. Note: with **Layer 1 dropped**, the only source of `▶` lines is `resolveTranscriptTokens`' LIS, which is **strictly-increasing + unique by construction**, so colliding *existing* `▶` cannot arise from the real pipeline. v2 still adds a defensive full-set unique+increasing assertion/test (cheap insurance).

**B4 — (Codex) `findSections` accepts `▶` lines the render parser rejects.** `TS_LINE = /^▶\s+\[/` is looser than `parse.ts:16` `TS_LINE_RE` (requires `https?://…` + full-line). A malformed-URL `▶` → checker says "present", render parser returns `null` → guarantee violated.
→ **Fix (v2):** the checker **reuses `parse.ts`'s real `parseSections`** (export it) instead of reimplementing detection — checker⟺render-parser agreement becomes structural.

### High

**H1/L6 — (both) `findSections` disagrees with `parse.ts` on `---` dividers.** `parse.ts:80` drops pure-dash lines *before* timestamp extraction; the reimplemented walker treats `---` as first body line → false "missing". Also `parse.ts` uses `trimStart().startsWith('▶')` (tolerates leading ws).
→ **Fix (v2):** same as B4 — reuse `parseSections`; the injection pass reuses exported `isFenceLine`.

**H2 — (Claude) the Task-5 integration test cannot run as written.** `tests/integration/**` is **not** in the default `testMatch` (only `jest.integration.config.ts`, run via `npm run test:integration`), and `tests/integration/setup.ts:20-29` **throws without a live Supabase stack**. The test is a pure Gemini-SDK-mock logic test with no Supabase dependency → `npx jest tests/integration/...` finds "No tests"; `npm test` excludes it entirely.
→ **Fix (v2):** home the test under `tests/lib/` (matched by `npm test`, no Supabase), like `tests/lib/gemini.test.ts`. Rename to "generateSummary integration".

**H3 — (Codex) dig golden too narrow.** → **Dissolved by dropping Layer 1** — `resolveTranscriptTokens` is now untouched, so dig is byte-identical trivially; no golden needed. (v2 keeps the existing dig tests as the regression guard.)

**H4 — (Codex) Task 5 mislabeled "through summaryCore" but calls `generateSummary`.** → **Fix (v2):** rename; the lib-level `generateSummary` test is the right scope.

### Medium

**M1/M4 — (both) money framing.** New per-section criterion raises *expected* attempts from 1 → up to 2 for single-omitted-token videos (`TIMESTAMP_MISS_CAP=2`); spec §10 "same as today" is true only for the ceiling. → **Fix (v2):** state expected-spend honestly; add a `mockGenerateContent` call-count assertion.

**M2 — (Codex) Task-5 TDD sequencing.** After Tasks 1-3 the integration test already passes → it's a regression test, not failing-first. → **Fix (v2):** reframe as regression coverage.

**M3 — (both) existing gemini tests break — substantive rewrites, not string swaps.** Named: `tests/lib/gemini.test.ts:320-331` (out-of-range → now gets a `▶` via Layer 3; assertion inverts), `:354-362` (no-`▶` + `[timestamp-miss]` → now always injected + warn deleted), `:473-480` (cap test asserts `[timestamp-miss]`). → **Fix (v2):** enumerate all three by name with their exact new assertions in the wiring task.

**H2-codex (obs) — synth warn logs total sections, not synthesized.** → **Fix (v2):** compute missing sections before mutation; log count + section identifiers.

### Low

**L5 — (Claude) `interpolateStart` is dead code** — neither layer calls it (both use `spreadStarts`; `count=1` gives the midpoint). → **Fix (v2):** remove it.
**L1 — (Codex) `__test = { scoreSummary }` export is leaky.** → Accepted as an explicit test hook (documented); acceptable.
**L2 — (Codex) update the score comment** (`lib/gemini.ts:293-296` still says "has-timestamp"). → **Fix (v2):** update comment.

### Confirmed clean by both (not findings)
- No import cycle (`interval-math` leaf; acyclic).
- Dropping Layer 1 makes dig byte-identity trivial (`resolveTranscriptTokens` untouched).
- Invalid-index tokens handling / `!hasSegments` (E7) short-circuit / mutating `chosen.summary` after scoring — all safe.

---

## Layer-1 decision (user-confirmed)
**DROP Layer 1 (Task 3).** Unanimous across Codex, Claude, and the plan's own design note. Rationale: its sole benefit is saving ≤2 re-rolls for the out-of-order-token case on a once-per-video cached path; against that it touches shared dig-critical code and applies the fragile interpolation to 1–2s-apart segment offsets — the *higher-probability* collision surface. Layers 2+3 deliver the identical guarantee. User confirmed 2026-07-15.

## Convergence status
Round 1: 4 Blocking + 4 High (dropping Layer 1 dissolves B2, H3; folds several others). Non-trivial fixes → **mandatory re-review of the revised (v2) plan** before implementation.
