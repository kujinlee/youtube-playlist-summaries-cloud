# Dig Cost-Bound Hardening — Design Note

**Origin:** whole-branch review of the cloud dig-generation slice (`docs/reviews/whole-branch-review.md`). Codex flagged a **Blocking** money finding: the dig per-job Gemini spend is not mechanically provable to be ≤ `dig_est_cents` (150¢). Human decision (2026-07-12): **harden before merge**.

## Problem

The summary path *proves* its spend bound: `perRunWorstCents()` (`lib/gemini-cost.ts`) computes a worst-case from enforced token caps × retry-pass multipliers, `PRICED_MODEL='gemini-2.5-flash'`, and the handler fail-fasts if the model drifts. The dig path has none of that:
1. `generateDig` runs on `gemini-2.5-pro` (unpriced) via `GEMINI_DEEPDIVE_MODEL ?? 'gemini-2.5-pro'`.
2. No `maxOutputTokens` — output is model-max-bounded only.
3. Its retry structure (`generate.ts:182→185→190`) can issue **up to 3 billable calls** in one job (`dig_max_attempts=1` caps job executions, not model calls).
4. **The dominant cost is the video input:** `buildRequestBody` sends the video segment (`file_data` + `video_metadata` start/end offset). Video ≈ 258 tokens/sec at default resolution (verified, Gemini API pricing, 2026-07). A section spanning a long stretch bills enormous video-input tokens × 3 passes → far exceeds 150¢.

## Verified pricing (2026-07)
- gemini-2.5-pro: input **$1.25/M**, output **$10/M** (per Gemini API pricing / OpenRouter). Video input **258 tok/s** at default (1 fps); LOW media resolution downsamples to ≈ **66 tok/s** (same lever the summary transcribe uses).

## Solution — bound every cost term, prove ≤ 150¢

New enforced caps (cloud dig only; additive):
| Cap | Value | Rationale |
|---|---|---|
| Media resolution | **LOW** | video 258→~66 tok/s; summary already uses LOW |
| Video segment | **`MAX_DIG_VIDEO_SECONDS = 900`** (15 min) | clamp `end_offset = min(endSec, startSec+900)`; generous — most sections ≪ 15 min |
| Output tokens | **`MAX_DIG_OUTPUT_TOKENS = 16384`** | dig elaborations are ~1–4K tokens; 16K is generous headroom |
| Billable passes | **`DIG_MAX_PASSES = 3`** | worst-case call count in generateDig's retry structure (sourced next to the retry constant so it can't drift) |

**Conservative (upper-bound-padded) price constants** — intentionally higher than observed so the bound stays sound if prices rise:
`PRICE_DIG_IN_PER_1M_CENTS = 150` (obs 125), `PRICE_DIG_OUT_PER_1M_CENTS = 1200` (obs 1000), `DIG_VIDEO_TOKENS_PER_SEC = 66` (LOW res), `PRICED_DIG_MODEL = 'gemini-2.5-pro'`.

### `digWorstCents()` (provable worst-case per job)
Per pass: video (`900 × 66 = 59,400` tok) + transcript (`MAX_TRANSCRIPT_INPUT_BYTES = 40,960` used as a token upper-bound — bytes ≥ tokens, so conservative) + prompt/schema overhead (~8,000 tok) ≈ **108,360 input tok** × 150¢/M = **16.3¢**; output `16,384 × 1200/M` = **19.7¢**. Per pass ≈ **36.0¢** × 3 passes ≈ **108¢ ≤ 150¢** (margin ≈ 42¢). Global daily `spend_ledger` cap remains the system-level backstop.

## Enforcement
- **Model fail-fast:** `makeDigHandler` throws at init if `DEEPDIVE_MODEL !== PRICED_DIG_MODEL` — an env override to an unpriced model cannot silently break the bound (mirrors summary-handler's `SUMMARY_MODEL !== PRICED_MODEL` guard).
- **Guard test:** assert `digWorstCents() <= 150` (the `dig_est_cents` default) — the mechanical proof, analogous to the summary cost-guard test.
- **Signal:** thread `ctx.signal` into `generateDig` so an abort (lease loss / shutdown / wall-clock) cancels the in-flight Gemini call instead of burning it.

## Spec-untouchable constraint
`lib/dig/generate.ts` is shared with the LOCAL dig pipeline (`lib/dig/dig-section.ts:61`), which the slice spec designated UNTOUCHED. All new `generateDig` parameters are **optional** (`opts?: { maxOutputTokens?; maxVideoSeconds?; mediaResolution?; signal? }`); the local caller passes none → **behaviorally identical** (no cap, default res, no external signal). Only the cloud handler passes the cost-governing opts.

## Tasks (SDD, money-critical → dual review)
- **HA** `gemini-cost.ts`: add the dig constants + `digWorstCents()` + guard test (`digWorstCents() <= 150`).
- **HB** `generate.ts`: additive optional `opts` on `generateDig`; `buildRequestBody` sets `generationConfig.maxOutputTokens` + `mediaResolution: 'MEDIA_RESOLUTION_LOW'` and clamps `end_offset` to `startSec+maxVideoSeconds` when provided; `callGeminiRest` composes `opts.signal` with its timeout signal. Local behavior unchanged when opts absent.
- **HC** `dig-handler.ts`: pass `{ maxOutputTokens, maxVideoSeconds, mediaResolution:'LOW', signal: ctx.signal }`; add the `DEEPDIVE_MODEL !== PRICED_DIG_MODEL` fail-fast.
- **HD** tests: guard test (HA); generate.ts cap/res/clamp/signal plumbing; handler model-guard throws + passes opts; re-run integration.

## Assumptions surfaced for the merge gate
- LOW media resolution + a 15-min video cap slightly change what dig "sees" for very long / visually-dense sections. Reasonable defaults; documented; reversible.
- Price constants are conservative and dated; revisit if Gemini pricing changes materially.

---

## RESOLUTION (2026-07-12): cloud dig → gemini-2.5-flash (human-decided)

**Why the pro approach failed:** three adversarial rounds established (verified against Google docs + developer reports) that **gemini-2.5-pro cannot be cost-bounded per job**: thinking cannot be disabled (min budget 128) and `thinkingBudget` is a **soft** limit the model can overflow (and reports of it being ignored). Worst-case Pro dig ≥228¢ > 150¢ — unprovable by any config.

**Human decision:** run **cloud** dig generation on **gemini-2.5-flash**, which CAN hard-disable thinking (`thinkingBudget: 0` — valid on Flash-family, proven by the summary transcribe path in `lib/gemini.ts`). The **local** dig path stays on `gemini-2.5-pro` (unchanged).

**New provable bound (flash rates, thinking disabled):**
- Prices: reuse the existing dated flash constants `PRICE_IN_PER_1M_CENTS=30`, `PRICE_OUT_PER_1M_CENTS=250` (same source-of-truth the summary bound uses). Drop the pro-padded `PRICE_DIG_*`.
- `MAX_DIG_THINKING_TOKENS = 0` (flash genuinely disables thinking via `thinkingConfig.thinkingBudget: 0`).
- `PRICED_DIG_MODEL = 'gemini-2.5-flash'`; the cloud handler passes this model + `thinkingBudget: 0` explicitly.
- Per pass: input `(video 59,400 + transcript 40,960 + summaryProse 8,192 + overhead 4,000) × 30/1M ≈ 3.4¢` + output `16,384 × 250/1M ≈ 4.1¢` ≈ **7.5¢**; × 3 passes ≈ **23¢ ≤ 150¢** (margin ≈ 127¢).
- Video LOW resolution (66 tok/s) + 15-min video clamp + 16K output cap all retained (still valid on flash).

**Changes:** `generate.ts` gains an additive `opts.model` (cloud passes flash; local no-opts → `DEEPDIVE_MODEL`=pro, unchanged) and sets `thinkingConfig.thinkingBudget: 0` when the caller supplies `thinkingBudget: 0`; `gemini-cost.ts` reprices dig at flash rates + `MAX_DIG_THINKING_TOKENS=0` + `PRICED_DIG_MODEL='gemini-2.5-flash'`; `dig-handler.ts` passes `model: PRICED_DIG_MODEL` + `thinkingBudget: 0`; the `cap-soundness` live drift-guard reflects the new (~23¢) bound. Flash + video + LOW-res + thinkingBudget:0 is the exact proven pattern the summary transcribe path uses.
