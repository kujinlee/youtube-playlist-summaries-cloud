<!-- codex-review: model=gpt-5.5 -->

**Blocking**

1. `docs/superpowers/specs/2026-08-22-corrections-in-cloud-design.md:238-249` still permits the row to claim corrections that the published body never received.

Scenario: playlist-wide doc-version bump, existing final blob, stored corrections. The worker applies `fixSummary`, stages corrected bytes, persists corrected card/hash, then `promote()` discards the staged blob because Supabase promotion is create-if-absent (`lib/storage/supabase/supabase-blob-store.ts:116-123`). The spec acknowledges this but still leaves unattended correction in scope. That violates the stated goal at lines 7-8: “the row stops claiming corrections it never applied.”

Suggested fix: do not add unattended corrections until #22/M5 makes publication observable, or persist corrected card/hash only after `promote` returns a result proving the corrected body became live.

2. `docs/superpowers/specs/2026-08-22-corrections-in-cloud-design.md:120-124` still says `effective corrections`, which is the stamping input, not always the apply input.

Scenario: an implementer follows §4 literally and uses effective corrections in the attended route. A bare attended POST with stored corrections then re-runs `fixSummary`, contradicting §5.1 and the existing test at `tests/api/regenerate.test.ts:113-116`.

Suggested fix: change the rule to `fixSummary runs iff the apply input is non-empty after trimming`, then define apply input explicitly: attended=request corrections; unattended=freshly re-read stored corrections.

**High**

1. `docs/superpowers/specs/2026-08-22-corrections-in-cloud-design.md:94-103` moves the prose-rule problem into “structural validation.”

Scenario: “same invariants” is not precise enough to build consistently. One implementation may only check section count and timestamp completeness; another may require exact H2 text and exact `▶` start times. Dig anchoring depends on exact heading/timestamp stability, not just parseability.

Suggested fix: specify the validator as an exact comparison: after stripping Quick Reference, compare pre/post parsed H2 sequence, heading text, timestamp start/end tuple, section count/order, frontmatter/H1 presence, and required metadata. State repair vs throw; current text says failure is error, so make it throw-only.

2. `docs/superpowers/specs/2026-08-22-corrections-in-cloud-design.md:219-222` still does not make attended metering implementable.

Scenario: it says “route-side reserve / settle / release” but gives no RPC name, integer reserve amount, daily/per-owner policy, idempotency key, or settle semantics. §6.2’s `17.4¢` cannot be reserved as an integer ledger amount; the implementation would have to invent `18¢` or a new column/config.

Suggested fix: define `correction_est_cents = 18`, the exact reserve RPC and settle RPC, whether owner budget applies, and the release rule keyed to a `BillingLatch`.

**Medium**

1. `docs/superpowers/specs/2026-08-22-corrections-in-cloud-design.md:210-213` gives the right raw arithmetic bound but not the bound the current guard shape would enforce.

Recomputed:
- Summary raw at 1800s: `114.984¢`, ceiling `115¢`.
- `summary_est_cents`: `150¢`.
- Slack from ceiled summary: `35¢`.
- Correction worst: `17.43168¢`, i.e. `17.4¢` rounded.
- Raw fit max: `4416s`; at `4417s`, raw summary + correction is `150.00192¢`.

But if the ratchet extends the existing `cap-soundness.test.ts` style, which uses `Math.ceil(worst)`, the max fit is `4332s`, not `4416s`.

Suggested fix: specify whether the ratchet proves raw cents or whole-cent rounded reservations. If whole-cent, use `4332s` or raise the estimate.

2. `docs/superpowers/specs/2026-08-22-corrections-in-cloud-design.md:224-227` says “No lease” but the route-side duplicate story is still hand-wavy.

Scenario: two authenticated cloud clients submit the same corrections. Both can reserve and both can pay. “Converges on the same result” is true for content, not spend. The spec says bounded by caps/ledger, but without the route reserve design from the High finding, this is not yet a mechanism.

Suggested fix: either use a per-video correction lease/idempotency key, or explicitly accept duplicate spend and make the reserve protocol enforce the cap.

**Low**

1. `docs/superpowers/specs/2026-08-22-corrections-in-cloud-design.md:183` says `generateJson` reaches caps via `withCaps` at `:326`. More precisely, `generateSummary` constructs a capped model with `withCaps` at `lib/gemini.ts:326`, then passes that model to `generateJson`. `generateJson` itself has no cap parameters.

Suggested fix: reword for accuracy.

2. `docs/superpowers/specs/2026-08-22-corrections-in-cloud-design.md:166` says `route.ts:52-59` writes `annotationsEditedAt.corrections` on every request. Current code only calls `updateVideoFields` for non-empty corrections or explicit `''`; absent/whitespace does not write.

Suggested fix: say “on every non-empty or explicit-clear request today.”

**Verified**

- Deleted machinery: no live dangling `applicable.ts`, tokenizer, reducible/irreducible outcome, or `exists(finalKey)` pre-check remains except historical discussion.
- §6.1 verified: `withCaps` is at `lib/gemini.ts:36`, used by `generateSummary` at `:326` and `extractQuickView` at `:433`; `fixSummary` at `:470-497` does not use it.
- §9 local test claim verified: `npm test -- tests/api/regenerate.test.ts tests/lib/cloud-sync/regenerate-stamp.test.ts --runInBand` passed, 2 suites / 18 tests. The seven behavior-relevant tests are preserved.

**Round-2 Non-Optimization Disposition**

| Finding area | v3 status |
|---|---|
| Cloud route wiring | Fixed in spec |
| Local bare regenerate semantics | Fixed; tests pass |
| Cap derived from byte sample | Fixed |
| Cost arithmetic deferred | Fixed, with rounding caveat |
| `updated_at` side effect | Partly; named, but requires new RPC |
| Clear corrections on Supabase | Partly; correct surface named, not designed |
| Structural validation | Partly; required but underspecified |
| Attended ledger | Partly; still not implementable |
| Abort ordering | Fixed in spec |
| Stale unattended corrections read | Fixed in spec |
| `thinkingBudget: 0` quality | Partly; still NOT VERIFIED |
| Falsifiers | Partly; better, but blocked by publication and metering gaps |

This should not be another monolithic revision. The design needs a different shape: split attended cloud corrections, worker/unattended corrections, publication observability, and ledger/RPC changes into separate slices. The unattended slice depends on #22/M5; forcing it into this spec is why the same composition defect keeps resurfacing.

NOT CONVERGED
