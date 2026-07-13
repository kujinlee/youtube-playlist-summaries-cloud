---
status: accepted
---

# Cost caps and pricing constants are tunable soft targets, currently enforced as a hard per-job ceiling

The dig/summary **cost caps** (`*_est_cents`, `*_max_attempts`, `max_duration_seconds`, `quota_allowance`), the **request caps** that bound a single Gemini call (model, output/thinking-token limits, video-segment clamp, media resolution), and the **provider price constants** used to prove the bound are **trial-and-error soft targets**, not permanent truths. They are set deliberately conservative today and are **meant to be adjusted** as we observe real document quality against real cost — including swapping a cheaper model back to a more capable one, or accepting the occasional per-job budget overflow, if quality warrants it.

The current default posture enforces a **mechanically provable per-job spend ceiling** (a CI guard test fails if the live config drifts below the computed worst case). **That strictness is itself a choice, not a law.** This ADR records the intent so a future maintainer does not read the guard test as immovable — and knows exactly which knob to turn, where it lives, and what turning it forces.

## Why this needs recording

A future reader will see `tests/lib/gemini-cost.test.ts` assert `digWorstCents() <= DIG_EST_CENTS` and `tests/integration/cap-soundness.test.ts` assert `live dig_est_cents >= ceil(digWorstCents()) * dig_max_attempts`, both failing CI on violation, and reasonably conclude *"the per-job cost bound is a hard invariant — I must not exceed it."* The intent is the opposite: the numbers are dials. The **hard-ceiling enforcement is a starting default** we chose because it is the safest place to begin on a money path; it can be relaxed to "soft target + global daily backstop" once we have quality/cost data. The switch of cloud dig to gemini-2.5-flash (ADR context: `docs/reviews/task-cloud-dig-flash-review.md`) is exactly such a dial-turn — chosen for a provable bound, at a known cost to elaboration quality — and it is expected to be revisited.

## Configuration surface — which knob lives where

**Runtime-tunable now (DB, no code change / no redeploy).** `guardrail_config` singleton (migration 0011) + `quota_allowance`, service-role only:

| Knob | Effect |
|---|---|
| `dig_est_cents` / `summary_est_cents` | The amount **charged/reserved** per job at enqueue (quota debit + `spend_ledger` reserve). This is the real charge. |
| `dig_max_attempts` / `summary_max_attempts` | Billable executions per job row (`enqueue_job` sets `jobs.max_attempts`). |
| `max_duration_seconds` | Rejects over-long videos before enqueue (PJ003). |
| `quota_allowance` (per `is_anonymous` × `kind`) | Per-principal job allowance. |

**Code constants (require an edit + redeploy + passing the guard test)** — `lib/gemini-cost.ts`:

| Constant | Role | Quality lever? |
|---|---|---|
| `PRICED_DIG_MODEL` | The model cloud dig **actually runs** (pinned into `generateDig` opts by `dig-handler.ts`, env-independent). | **Biggest** — flash vs pro. |
| `MAX_DIG_OUTPUT_TOKENS`, `MAX_DIG_THINKING_TOKENS`, `MAX_DIG_VIDEO_SECONDS`, `DIG_VIDEO_TOKENS_PER_SEC` (LOW-res rate), `DIG_GENERATE_MAX_PASSES` | Bound the per-call spend terms. | Yes — output/thinking/video budget. |
| `PRICE_IN_PER_1M_CENTS`, `PRICE_OUT_PER_1M_CENTS` | Provider prices used by `digWorstCents()`/`perRunWorstCents()`. Dated snapshots (see below). | No — accounting only. |

Note the model split: `GEMINI_DEEPDIVE_MODEL` (env) controls the **local** dig model only. **Cloud** dig is pinned to `PRICED_DIG_MODEL` (a code constant) *by construction* so its cost can't drift via env — changing the cloud model is a deliberate code edit, not an env toggle.

## The coupling a tuner must understand

The real Gemini **spend ceiling** is set by the **code request-caps** (model × output × thinking × video × resolution × passes). The **charge** is the **DB `dig_est_cents`**. The guard test enforces `charge >= spend-ceiling` (so we never under-charge relative to worst-case spend). Therefore:

- **To raise quality within the provable-bound stance:** raise the code caps (e.g. back to pro, or a bigger `MAX_DIG_OUTPUT_TOKENS`) **and** raise `dig_est_cents` in the DB so the guard stays green. This necessarily **charges users more** — that is the honest cost of more quality.
- **To allow occasional overflow / stop paying for the strict ceiling:** relax the *stance* — downgrade the `digWorstCents() <= DIG_EST_CENTS` guard to a soft warning and rely on the standing **global daily `spend_ledger` cap** + per-owner serve budget as the real blast-radius backstops. A single job may then exceed its `est_cents`, but total daily spend stays bounded. **Keep the daily cap regardless** — it is what makes soft-target tuning safe.

`digWorstCents()` today reads **code** constants, not the live DB. If any code cap is promoted to DB config (see follow-ups), the guard must recompute the worst case from the **live** config too, or it silently proves the wrong number.

## Provider pricing drifts — the price constants are dated

`PRICE_IN_PER_1M_CENTS` / `PRICE_OUT_PER_1M_CENTS` / `DIG_VIDEO_TOKENS_PER_SEC` are **snapshots of Gemini pricing as of 2026-07**, intentionally padded above observed values. **AI-provider charge policies change over time**, so these are not evergreen:

- Re-validate the price + token-rate constants whenever the provider announces a pricing change, or on any model swap (flash↔pro have different rates), or on a periodic cadence.
- On a change, re-run the guard/cap-soundness tests — they will flag if the padded constants no longer cover the new prices, forcing a conscious `est_cents` (or padding) update rather than a silent under-charge.
- The bound only holds while the *padding* absorbs price rises; a large provider increase requires a real config revision, not just a note.

## Considered options

- **Hard provable per-job ceiling (chosen as the current default).** Safest on a money path from day one; makes under-charging a CI failure; costs quality flexibility (forced us off pro). Explicitly reversible per this ADR.
- **Soft target + daily-cap backstop only (available, not yet chosen).** Maximizes quality flexibility and tolerates rare overflow; gives up the per-job guarantee, leaning on the daily `spend_ledger` cap. Adopt when quality/cost data justifies it.
- **Bake all knobs as immutable constants (rejected).** Contradicts the trial-and-error intent; every tuning cycle would need a code change + full review loop.

## Consequences / follow-ups (for later design or config adjustment)

- **Promote the quality-vs-cost code constants to configuration.** At minimum `PRICED_DIG_MODEL`, `MAX_DIG_OUTPUT_TOKENS`, `MAX_DIG_VIDEO_SECONDS`, `MAX_DIG_THINKING_TOKENS` → env or new `guardrail_config` columns, so tuning does not require an edit + redeploy + the SDD/review loop. **If moved to the DB, update `digWorstCents()` to compute from the live config** and keep the cap-soundness guard sound.
- **Record the stance explicitly when it changes.** If occasional overflow becomes acceptable, change the `digWorstCents() <= DIG_EST_CENTS` guard from a hard failure to a warning and document that the daily cap is now the primary bound. Until then, the hard ceiling stands.
- **Add the opt-in live smoke-check** (deferred from the flash review) that asserts `usageMetadata.thoughtsTokenCount === 0` and LOW/clipped token scale on the raw REST dig body — run it before trusting any new model/caps combination empirically, not just against documented pricing.
- **A "which dial for which goal" quick map:** more quality → raise model/output caps (+ raise `est_cents`); cheaper → lower them; more headroom for long/dense videos → raise `MAX_DIG_VIDEO_SECONDS` (+ re-derive the bound); tighter blast radius → lower the daily `spend_ledger` cap.
