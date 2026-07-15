# Summary Section-Timestamp Guarantee — Design Spec

**Date:** 2026-07-15
**Status:** Approved (design) — awaiting spec review before planning
**Author:** Claude (brainstorming skill) + Kujin Lee

---

## 1. Problem & Root Cause

A cloud summary shipped with one section (`## 2. Funding Rounds and Shifting Valuations`, video `9nh8TQRcYD0`) missing its timestamp line. In the rendered dig-deeper doc that section shows **no `▶ (timestamp)`, no `dig deeper ▶`, and no `💬 ask AI`** control, because all three are gated on `startSec !== null` (`lib/html-doc/render-dig-deeper.ts:288,300,309`). A section with no timestamp has no `sectionId` to dig and no time range to ask AI about, so the render is *correct given the data* — the defect is upstream, in generation.

### How `▶` lines are actually produced (two-stage)

1. Gemini does **not** emit `▶` lines. Per the prompt (`lib/gemini.ts:335`) it emits an own-line placeholder token `[[TS:<index>]]` immediately after each `##` heading, where `<index>` is a transcript-segment index and indices "MUST strictly increase down the document."
2. A mechanical pass, `resolveTranscriptTokens` (`lib/transcript-timestamps.ts:101`), rewrites those tokens into `▶ [start–end](url?t=Ns)` lines — but it keeps only the **Longest strictly-Increasing-offset Subsequence (LIS)** of the tokens and **deletes the entire line** of any token not in that subsequence (`transcript-timestamps.ts:179`, `return k ? timestampLine(...) : null`).

### Why a section silently loses its `▶`

A section ends up with **no `▶` line at all** when, for that section, the model either:

- **(a) emitted a `[[TS:i]]` whose offset broke the strict-increase rule** (out of order vs neighbors, out of range, or offset ≥ video duration) → the LIS pass dropped and deleted its line; or
- **(b) omitted the token entirely.**

For `9nh8TQRcYD0`, case (a) is almost certain: section 1 is `3:28–6:09` (t=208) and section 3 is `6:09–9:17` (t=369), contiguous — leaving no strictly-increasing slot for section 2, so its token was dropped.

### Why nothing caught it

Every existing timestamp check is **document-wide, all-or-nothing** — "does the doc contain *at least one* `▶`?":

- `hasTimestamp` (`gemini.ts:275`) = `s.includes('▶')`; the generation-loop score criterion (`gemini.ts:304`) is `!hasSegments || hasTimestamp(s) ? 1 : 0`.
- `warnTimestampMiss` (`gemini.ts:387`) fires only on **zero** `▶` in the whole doc.
- `checkSummaryCompleteness` (`lib/summary-completeness.ts`) checks truncation, never per-section timestamps.
- `lib/timestamp-audit.ts` / `lib/timestamp-repair.ts` are offline ops tools (local `fs`), not in the live path, and also use document-level "any `▶`".

Because the other six sections supply that one `▶`, generation scored the doc as timestamped, returned success, and both the cloud worker (`lib/job-queue/summary-handler.ts`) and local pipeline (`lib/pipeline.ts`) persisted it unchanged. **No per-section guarantee exists anywhere.**

---

## 2. Goal & Invariant

**Goal:** guarantee that every generated summary section carries a valid `▶` timestamp, so every section is diggable and ask-AI-able.

**Invariant (the contract this slice enforces):**

> Every `##` heading the parser treats as a section in the persisted summary **body** — every numbered `## N.` section **and** `## Conclusion` — is immediately followed by exactly one `▶ [start–end](url?t=Ns)` line whose `startSec` is a **unique** integer and **monotonically increasing** with section order.

**Unique + monotonic is non-negotiable:** `startSec` *is* the dig `sectionId` — the dig blob key is `dig/{base}/{sectionId}.r9.md` (`DIG_GENERATOR_VERSION=9`). Two sections sharing a `startSec` would cross-wire their dig content. This is exactly why the strict-increase LIS rule exists; any relaxation must preserve uniqueness.

*Note on "section":* the guarantee covers headings in the **generated body** as split by `parseSummaryMarkdown` (`lib/html-doc/parse.ts` splits on `## `). The Quick Reference callout that `summaryCore` appends *after* generation (`lib/ingestion/summary-core.ts:96-134`) is not a generated section and is out of scope.

---

## 3. Scope

- **Forward-only.** Applies to newly generated / regenerated summaries. Existing already-shipped docs are **not** backfilled (decision D3). Video `9nh8TQRcYD0` is fixed only when next regenerated.
- **Shared core.** The change lands so both the **local pipeline** and the **cloud worker** inherit it — the generation path they share is `generateSummary` (`lib/gemini.ts`) → `resolveTranscriptTokens` (`lib/transcript-timestamps.ts`), orchestrated by `summaryCore` (`lib/ingestion/summary-core.ts`).
- **No new external spend beyond the existing bounded loop.** Mechanical layers are free; the re-roll layer reuses the pre-existing `MAX_SUMMARY_ATTEMPTS` budget (§10).

---

## 4. Decisions Settled (brainstorming forks)

| # | Decision | Choice |
|---|---|---|
| D1 | Repair strategy | **Both** — mechanical token-preservation + bounded re-roll fallback. |
| D2 | Terminal failure policy (still missing after re-roll budget) | **Mechanical last-resort interpolation** — always synthesize a valid `▶`; never block, never ship silently degraded. |
| D3 | Backfill existing summaries | **Forward-fix only** — no batch backfill in this slice. |

---

## 5. Architecture — Three Layers, Cheapest First

The guarantee is enforced as an ordered pipeline. A section that gains a `▶` at an earlier (cheaper) layer never reaches a later one.

```
Gemini → [[TS:i]] tokens
   │
   ▼
Layer 1  resolveTranscriptTokens (mechanical, free)
   │      out-of-order/dropped token → KEEP the section's ▶, startSec clamped
   │      strictly between kept neighbors (unique + monotonic). No line ever
   │      deleted for a section that had a token.
   ▼
per-section completeness check (## count vs ▶ count)
   │
   ├── every section has ▶ ─────────────────────────────► done
   │
   ▼ a section had NO token at all
Layer 2  bounded re-roll (reuses MAX_SUMMARY_ATTEMPTS)
   │      generation-loop timestamp criterion upgraded from
   │      "doc has ≥1 ▶" to "EVERY section has a ▶".
   ▼ budget spent, a section still tokenless
Layer 3  mechanical last-resort interpolation (free)
          synthesize startSec between neighbors (first→transcript start,
          Conclusion/last→video duration), kept unique. Guaranteed ▶.
```

### Layer 1 — Mechanical token-preservation (targets root-cause case (a))

Change `resolveTranscriptTokens` so that a **section heading token** that falls outside the LIS is **not deleted**. Instead its `▶` is emitted with a `startSec` **clamped strictly between its nearest kept (in-LIS) neighbors**, preserving monotonicity and uniqueness. This fixes the emitted-but-dropped case (likely `9nh8TQRcYD0`) at zero Gemini cost.

**Blast-radius guard (mandatory):** `resolveTranscriptTokens` is *also* called by dig generation for inline transcript citations (`lib/job-queue/dig-handler.ts:112`, `lib/dig/dig-section.ts:64`; dig passes a 4th `durationSeconds` arg summary does not). The Layer-1 change **must not alter dig's timestamp behavior.** Realize this by scoping the new "keep + clamp" behavior to **section-heading tokens on the summary path only** (e.g. a parameter/flag, or a separate resolution routine for heading tokens), leaving dig's inline-citation resolution byte-identical. **"Dig output byte-identical" is an explicit invariant and a mandatory adversarial-review target** (same discipline as the prior dig-frontend slice).

### Layer 2 — Bounded re-roll (targets root-cause case (b))

Add a **per-section completeness check** that counts `## ` section headings vs `▶` lines (and asserts adjacency). Wire its result into the **existing** generation loop (`gemini.ts:371-380`) by upgrading the scoring/stop criterion so a candidate is "timestamp-complete" only when **every** section has a `▶`, not merely one. The loop already re-rolls up to `MAX_SUMMARY_ATTEMPTS` and keeps the best-scored attempt; this makes a per-section gap a re-roll trigger instead of an ignored miss. The existing `TIMESTAMP_MISS_CAP=2` early-break (`gemini.ts:291,379`) is re-evaluated against the new criterion (see §8 edge E5).

### Layer 3 — Mechanical last-resort interpolation (D2 guarantee)

If the loop exits with a section still lacking a token, synthesize a `▶`:

- `startSec = ` integer **midpoint** of the nearest timestamped predecessor `P` and successor `N` (`P + floor((N - P) / 2)`), guaranteed strictly inside `(P, N)`.
- **First** section missing → lower bound is the transcript start (0 or first segment offset).
- **`## Conclusion` / last** section missing → upper bound is the video duration.
- Result is clamped to stay unique and monotonic against already-assigned neighbors.

This makes coverage total: the summary always ships with every section timestamped.

---

## 6. Data Flow

`summaryCore` (`lib/ingestion/summary-core.ts:54`) is unchanged in shape; the guarantee is enforced **inside `generateSummary`** (Layers 1–2 already live there) plus the new Layer-3 finalizer applied to the chosen summary before `generateSummary` returns. `summaryCore` then continues (padDividers → completeness warn → frontmatter/body assembly) and both stores persist `mdContent` as today. No route, schema, or storage-key change.

---

## 7. Error Handling

- **No new throw paths.** Per D2 the terminal state is a synthesized timestamp, not a failure. Generation never fails *because* of a missing section timestamp.
- Existing failure modes (transcript resolution, JSON generation retries, truncation) are untouched.
- Layer 3 emits a `console.warn` (`[summary-section-ts-synth] videoId section=N`) for observability so synthesized (approximate) timestamps are auditable — visible, not silent.

---

## 8. Edge Cases (enumerated)

| # | Case | Expected |
|---|---|---|
| E1 | Section token emitted but out-of-order (case a) | Layer 1 keeps it; `startSec` clamped strictly between kept neighbors; unique + monotonic. No re-roll. |
| E2 | Section token omitted entirely (case b) | Layer 2 re-rolls (bounded). If a re-roll yields all tokens, done. |
| E3 | Still tokenless after re-roll budget | Layer 3 synthesizes midpoint `startSec`; `▶` present; warn logged. |
| E4 | First section missing a token | Layer 3 lower bound = transcript start (0 / first-segment offset). |
| E5 | `## Conclusion` / last section missing | Layer 3 upper bound = video duration. `TIMESTAMP_MISS_CAP` must not early-break before the per-section criterion is satisfied where a re-roll could still help. |
| E6 | Degenerate gap — neighbors < 2s apart (no integer strictly between) | Pathological (real sections are minutes apart). Fallback: `prev.startSec + 1`, preserving **dig-key uniqueness**; accept a possible 1s monotonicity relaxation vs the next real section. **Flagged for adversarial review.** |
| E7 | `hasSegments === false` (no transcript) | Out of scope — with no segments there are no `[[TS]]` tokens and the existing `!hasSegments` short-circuit (`gemini.ts:304`) stands; no `▶` expected, controls legitimately absent. |
| E8 | Dig inline-citation resolution | **Unchanged** — Layer 1 scoping must leave `dig-handler`/`dig-section` output byte-identical (blast-radius guard). |
| E9 | Multiple sections missing in one doc | Each handled independently, left→right, so all synthesized `startSec`s stay unique + monotonic in one pass. |

---

## 9. Enumerated Behaviors (test contract)

| # | Behavior | Trigger | Expected |
|---|---|---|---|
| 1 | Out-of-order heading token kept | `resolveTranscriptTokens` sees a section token breaking strict-increase | Section keeps a `▶`; `startSec` strictly between kept neighbors; unique |
| 2 | No section token deleted-to-empty | Any section with a heading token | That section's line is never `null`-dropped on the summary path |
| 3 | Dig resolution unchanged | `resolveTranscriptTokens` called from dig path | Byte-identical to pre-change output (golden) |
| 4 | Per-section checker detects gap | Doc with N `## ` headings but <N `▶` lines | Checker reports the specific missing section(s) |
| 5 | Re-roll on omitted token | A candidate has a section with no token | Loop re-rolls (within `MAX_SUMMARY_ATTEMPTS`), prefers a complete candidate |
| 6 | Criterion is per-section | Candidate with ≥1 but not all sections timestamped | Scored as NOT timestamp-complete (was: complete) |
| 7 | Interpolation midpoint | Section still missing after budget, both neighbors present | `startSec = P + floor((N−P)/2)`, in `(P,N)`, unique |
| 8 | Interpolation first-section | First section missing | Lower bound = transcript start |
| 9 | Interpolation last/Conclusion | Last/`Conclusion` missing | Upper bound = video duration |
| 10 | Total coverage | Any generated summary with segments | Every `## ` section (incl. Conclusion) has exactly one `▶`, unique monotonic `startSec` |
| 11 | Integration through `summaryCore` | Fixture transcript + mocked Gemini reproducing a dropped section | Persisted body: every section has a `▶`; no collision |
| 12 | No new failure | Deterministically bad video | Summary still persists; no throw; synth warn logged |

---

## 10. Money Invariant

- **Layers 1 and 3 are mechanical — zero Gemini cost.**
- **Layer 2 adds no new uncapped spend:** it reuses the pre-existing bounded loop (`MAX_SUMMARY_ATTEMPTS`, `gemini-cost.ts`). It only *changes when* a re-roll is considered warranted (per-section vs whole-doc), within the same cap. Worst case is the same number of attempts already permitted today.
- No change to reservation/ledger logic.

---

## 11. Files (anticipated)

**Modify:**
- `lib/transcript-timestamps.ts` — Layer 1: scoped "keep + clamp" for section-heading tokens on the summary path (dig path unchanged).
- `lib/gemini.ts` — Layer 2 (per-section criterion in the gen loop) + Layer 3 finalizer on the chosen summary; upgrade `hasTimestamp`/score usage; re-evaluate `TIMESTAMP_MISS_CAP`.
- Possibly a small new module `lib/summary-section-timestamps.ts` (per-section check + interpolation) to keep `gemini.ts` focused and unit-testable in isolation.

**Not modified:** routes, storage keys, `parse.ts`, `render-dig-deeper.ts`, schemas, `summary-core.ts` shape.

*(Exact decomposition is the plan's job; this list bounds the blast radius.)*

## 12. Testing Strategy (TDD)

- **Unit — Layer 1:** out-of-order/dropped section token kept + clamped (unique, monotonic); a section token is never deleted on the summary path.
- **Unit — dig byte-identity:** golden test that dig-path `resolveTranscriptTokens` output is unchanged (blast-radius guard).
- **Unit — per-section checker:** detects the specific missing section(s); passes a fully-timestamped doc.
- **Unit — interpolation:** midpoint, first-section, last/Conclusion, multi-missing (E9), degenerate-gap (E6).
- **Unit — loop criterion:** a partially-timestamped candidate scores as not-complete.
- **Integration — through `summaryCore`:** fixture transcript + **mocked Gemini** (per project mocking boundary: `lib/gemini.ts` mocked) returning a body that reproduces a dropped section; assert the persisted body has a `▶` for every section, all `startSec` unique + monotonic, no throw.
- Mocks at the lib boundary; **no real Gemini calls** in unit/integration.

## 13. Out of Scope

- Backfilling existing shipped summaries (D3) — deferred; the existing `lib/timestamp-repair.ts` ops tool remains the manual escape hatch.
- Changing the Gemini prompt's token contract (still `[[TS:<index>]]`).
- Any change to dig inline-citation behavior (must stay byte-identical).
- Summaries generated with no transcript segments (E7).
- Per-section *accuracy* of model-provided timestamps beyond presence + ordering + uniqueness (we guarantee a valid, well-ordered `▶`, not that an approximate synthesized anchor is editorially perfect).

---

## Addendum — 2026-07-15: Layer 1 dropped (post-plan dual review)

The Post-Plan dual adversarial review (Codex + Claude) unanimously recommended, and the user confirmed, **dropping Layer 1** (the opt-in "keep out-of-order tokens" change to `resolveTranscriptTokens`). Its only benefit was saving ≤2 re-rolls for the out-of-order-token case on a once-per-video cached path; against that it touched shared dig-critical code and applied fragile interpolation to 1–2s-apart segment offsets (the higher-probability collision surface). **Layers 2 + 3 alone deliver the identical guarantee**, so the change is now:

- **§5 Layer 1 is REMOVED.** `resolveTranscriptTokens` is not modified; dig is byte-identical trivially.
- **§9 Enumerated Behaviors #1–3 are SUPERSEDED** (they described keeping out-of-order heading tokens and a dig golden). The out-of-order case is now handled by Layer 3 synthesizing a replacement `▶` after the unchanged LIS drops the token. The invariant OUTCOME (every section has a unique, monotonic `▶`) is unchanged.
- **Correction to §2 / §5:** existing `▶` starts are NOT "unique by construction." `resolveTranscriptTokens` keeps the LIS of float offsets but emits `Math.floor(offset)`, so two near-adjacent kept tokens can floor to the same integer → duplicate `startSec`. Therefore Layer 3 (`ensureSectionTimestamps`) is a **full-document normalizer**: it validates the entire start sequence for uniqueness + strict monotonicity and **rewrites** any offending existing `▶` line (not just inserts missing ones), running even when every section already has a `▶`. The Layer-2 score criterion likewise checks uniqueness + monotonicity, not mere presence.

See `docs/reviews/plan-summary-section-timestamp-guarantee-v1-review.md` and `-v2-rereview.md` for the convergence trail.
