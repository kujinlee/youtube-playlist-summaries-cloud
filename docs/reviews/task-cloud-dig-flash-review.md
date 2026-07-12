# Cost-Bound Resolution Review — Cloud Dig → gemini-2.5-flash (`96705ee..5942066` + `2561baa`)

Money-critical dual review of the human-decided fix that resolves the whole-branch **Blocking** money finding (dig per-job Gemini spend not mechanically provable ≤ `dig_est_cents`). Touches shared `lib/dig/generate.ts` → dual review to convergence required.

Reviewers: **Codex adversarial** (gpt-5.5, cost-soundness skeptic) + **Claude task-reviewer** (sonnet, spec compliance + code quality), independent.

## The change
Switch the **cloud** dig path from gemini-2.5-pro to **gemini-2.5-flash**, which can hard-disable thinking (`thinkingConfig.thinkingBudget: 0`), making the per-job spend cleanly provable. The **local** dig path stays on gemini-2.5-pro (`DEEPDIVE_MODEL`), byte-identical.
- `lib/gemini-cost.ts`: `PRICED_DIG_MODEL='gemini-2.5-flash'`; `MAX_DIG_THINKING_TOKENS=0`; removed the pro-padded `PRICE_DIG_IN/OUT_PER_1M_CENTS`; `digWorstCents()` reprices at the flash constants `PRICE_IN_PER_1M_CENTS=30` / `PRICE_OUT_PER_1M_CENTS=250`.
- `lib/dig/generate.ts`: additive `opts.model` (`const model = opts?.model ?? DEEPDIVE_MODEL`). Local no-opts → pro, no `generationConfig`, byte-identical.
- `lib/job-queue/dig-handler.ts`: removed the now-obsolete `DEEPDIVE_MODEL !== PRICED_DIG_MODEL` init guard (cloud now pins `model: PRICED_DIG_MODEL` explicitly → env-independent); passes `model: PRICED_DIG_MODEL` + `thinkingBudget: 0`.
- Tests: gemini-cost (flash + thinking 0 + 23), dig-handler (opts include model; obsolete guard test replaced with an env-independence test), generate.test (opts.model URL override + local-default + thinkingBudget:0 honored), cap-soundness (drift-guard intact; model assertion updated).

## The provable bound (both reviewers independently recomputed)
```
per pass input  = (video 900×66=59,400 + transcript 40,960 + summaryProse 8,192 + overhead 4,000) × 30¢/M = 3.37656¢
per pass output = (16,384 + 0 thinking) × 250¢/M = 4.096¢
per pass        = 7.47256¢ ; × DIG_GENERATE_MAX_PASSES(3) = 22.41768¢ → ceil = 23¢
```
**`digWorstCents() = 23¢ ≤ DIG_EST_CENTS (150¢)` — margin ≈ 127¢.** No constants were fudged to hit it.

## Convergent verdict
**Codex: 0 Blocking / 0 High.** Independently confirmed against current Google docs that gemini-2.5-flash supports disabling thinking with `thinkingBudget=0`, and flash pricing matches the constants — the exact model-family fact that the prior 3 pro-based rounds proved impossible. Verdict: "the code path pins Flash and emits `thinkingBudget:0` … no Blocking/High defects."

**Claude: SPEC COMPLIANCE Approved, CODE QUALITY Approved — no findings.** Verified all five spec items against source; recomputed 23¢; confirmed local `dig-section.ts:61` still calls `generateDig` with no 4th arg (byte-identical); traced the env-independence test and confirmed it is a **genuine** regression guard (a revert to `model: DEEPDIVE_MODEL` would fail it), not a tautology; confirmed no stale "pro cannot disable thinking" claims survive on the cloud path.

**This is convergence:** both independent reviewers returned 0 Blocking / 0 High on the money-critical crux.

## Findings (all below the merge bar)

### Medium (Codex) — live-shape validation gap → deferred, becomes the merge-gate caveat
The existing live gate (`tests/integration/gemini-live-gates.test.ts`) exercises the **SDK** summary/transcribe request shape, not the **raw REST** dig body (`file_data` + `video_metadata` + camelCase `generationConfig`). So the ~23¢ figure is proven at the code/config level and against Google's documented contract, but the *exact raw REST dig request* has not been validated by a live call asserting `usageMetadata.thoughtsTokenCount === 0` and LOW/clipped token scale.
- **Disposition: deferred, not a code defect.** This is the same class as the already-deferred T12 deploy-verification caveat — it requires a live API key + billable call. It is the **one caveat carried to the human merge gate** (recommend an opt-in live direct-REST dig smoke-check post-merge). The camelCase `generationConfig` field names + `MEDIA_RESOLUTION_LOW` + `thinkingBudget` are the *same* fields the production summary path (`lib/gemini.ts`) already sends successfully, which is strong (not absolute) evidence they are honored.

### Low (Codex) — stale 2048/Pro test wording → FIXED (`2561baa`)
`tests/lib/dig/generate.test.ts` carried Pro-era "cannot disable thinking / bounded budget" comment on the generic `thinkingBudget: 2048` plumbing test. Fixed: retitled + re-commented as a generic opts-plumbing test, pointing to the real cloud invariant (flash + `thinkingBudget:0`, asserted by the `thinkingBudget: 0 IS honored` test and `MAX_DIG_THINKING_TOKENS===0`). Comment/title only; `npx tsc --noEmit` 0, generate.test 43/43.

### Low (Codex + Claude) — cap-soundness model assertion is a constant-check → accepted as-is
`tests/integration/cap-soundness.test.ts:42-43` asserts `PRICED_DIG_MODEL === 'gemini-2.5-flash'` (a constant), not the runtime model the handler passes. Codex notes a future edit dropping `opts.model` would still pass this integration guard.
- **Disposition: accepted.** The drift Codex names **is** caught — by the unit env-independence test in `dig-handler.test.ts` (Claude verified it would fail if the handler reverted to `model: DEEPDIVE_MODEL`). The runtime-wiring guard therefore exists; the integration assertion is honest documentation of the flash pin, and lines 35-41 already explain why it is a constant-check (cloud cost is env-independent by construction, so there is no live drift for *this* layer to catch). Replacing it would duplicate the unit guard in an ill-fitting layer.

## Verification
`digWorstCents()=23`; targeted 58/58 + cap-soundness integration 4/4 + full unit **2141/2141**; `npx tsc --noEmit` exit 0; local `dig-section.ts:61` byte-identical. Post-Low-fix: generate.test 43/43, tsc 0.

## Bottom line
**Converged — mergeable as the final cost-bound resolution.** The whole-branch Blocking is resolved: cloud dig per-job spend is now mechanically provable at **≈23¢ ≤ 150¢** with thinking genuinely disabled (flash contract confirmed against Google docs by the adversarial reviewer). One deferred caveat for the human merge gate: an opt-in live direct-REST dig smoke-check would upgrade the raw-request-shape honoring from "documented-contract + production-parity evidence" to "empirically verified." Trade-off accepted by the human's flash decision: cloud dig elaboration quality is flash-tier, not pro-tier (local dig stays pro).
