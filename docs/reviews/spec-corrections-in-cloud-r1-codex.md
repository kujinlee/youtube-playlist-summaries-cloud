<!-- codex-review: model=gpt-5.5 -->

**Blocking**

1. `docs/superpowers/specs/2026-08-22-corrections-in-cloud-design.md:89` underspecifies the cloud route. Replacing the two `fs` calls is not enough.
Scenario: cloud user opens corrections after the menu is ungated. `CorrectionsPanel` POSTs `{ outputFolder: "", corrections }` (`components/CorrectionsPanel.tsx:49-52`), but the route requires `outputFolder` (`app/api/videos/[id]/regenerate/route.ts:20-21`) and uses `getPrincipal(outputFolder)` (`:30`). Even if `outputFolder` were present, `getStorageBundle()` without a Supabase client throws on the Supabase backend (`lib/storage/resolve.ts:51-57`).
Suggested fix: specify a real cloud branch mirroring quick-view/review: `?playlist=<uuid>`, `createServerSupabase`, `getUser`, `resolveOwnedPlaylistKey`, `getPrincipalFromSession`, `getStorageBundle({ supabaseClient })`; update `CorrectionsPanel`/client API to be scope-aware and reject `outputFolder` on cloud.

2. `docs/superpowers/specs/2026-08-22-corrections-in-cloud-design.md:212` says ledger metering is mandatory, but gives no implementable mechanism, and the current primitive cannot meter.
Scenario: cloud correction calls `fixSummary`; `fixSummary` has no `billing` parameter and never sets `billing.metered` (`lib/gemini.ts:470-510`), unlike `generateJson` (`lib/gemini.ts:273-274`). The route is not a job handler and has no `ctx.billing` (`lib/job-queue/handler-context.ts:5-10`). Result: paid Gemini calls can happen while `spend_ledger` is unchanged.
Suggested fix: design the route-side money path explicitly: reserve/admit RPC, estimated cents, per-owner/global guard, billing latch threaded into `fixSummary`/apply-core, settle/release semantics, and tests that fail on an unmetered `fixSummary`.

3. `docs/superpowers/specs/2026-08-22-corrections-in-cloud-design.md:245-248` understates the unattended `promote` failure. It is not merely “bounded honesty”; it pays for a correction that may be discarded and still writes corrected metadata.
Scenario: existing final blob is present. Worker applies corrections to `core.mdContent`, stages it, persists corrected `tldr`/`takeaways`/`mdCorrectionsHash`, then `SupabaseBlobStore.promote` sees destination exists and deletes the staged blob (`lib/storage/supabase/supabase-blob-store.ts:116-123`). Live body remains old; card/hash now describe the discarded corrected body. Existing tripwire already proves this shape for docVersion (`tests/lib/job-queue/summary-handler-promote-divergence.test.ts:140-162`).
Suggested fix: either defer unattended corrections until #22/M5, or make publication outcome observable and persist corrected card/hash only when the corrected body actually becomes live. Do not run paid correction before a known create-if-absent discard path unless the spec accepts and tests the wasted spend.

**High**

4. `docs/superpowers/specs/2026-08-22-corrections-in-cloud-design.md:169-177` misses `updated_at` as a skip side effect.
Scenario: skip updates only `mdCorrectionsHash` through `merge_video_data`, but that RPC always sets `updated_at = now()` (`supabase/migrations/0021_cloud_sync_signals.sql:79-90`). `deriveHumanSnapshot` uses `updatedAt ?? processedAt` as the fallback timestamp for legacy human fields (`lib/cloud-sync/backfill.ts:21-29`). A no-body-change correction skip can make old `personalNote`/`personalScore` look newly edited during sync.
Suggested fix: enumerate `updated_at` in the skip contract. Provide a narrow RPC for MD-currency-only updates that does not bump row `updated_at`, or prove and test that all affected rows have real `annotationsEditedAt` before allowing this path.

5. `docs/superpowers/specs/2026-08-22-corrections-in-cloud-design.md:116-129` leaves whitespace-only and empty corrections ambiguous, and the stated rule computes “run,” not “nothing to apply.”
Scenario: user clears the textarea to spaces. Current UI sends `"   "` and locally records `undefined` after success (`components/CorrectionsPanel.tsx:59-64`). Current route treats whitespace as “absent,” not clear (`app/api/videos/[id]/regenerate/route.ts:54-59`, `:77-79`). The new predicate would extract no terms and “anything else runs,” causing needless apply-core/card extraction and possibly preserving stored corrections while the UI thinks they were cleared.
Suggested fix: specify normalization before persistence and applicability: empty/whitespace means clear or absent, exactly one. Add explicit tests for `""` and `"   "` at route/UI/storage consumer level.

6. `docs/superpowers/specs/2026-08-22-corrections-in-cloud-design.md:278-279` tests ledger outcomes but the design does not define expected amount.
Scenario: apply-core has two paid calls on run, but `fixSummary` has retries and no caps; `extractQuickView` can retry through `generateJson`. A test asserting “moves by expected amount” cannot be written from this spec without inventing pricing/reservation rules.
Suggested fix: add a correction estimate constant/RPC and state whether the ledger records reservation estimate, actual spend, or a synthetic route charge.

**Medium**

7. `docs/superpowers/specs/2026-08-22-corrections-in-cloud-design.md:41-49` overcorrects backlog #23. Verified: blob key uses `startSec` (`lib/dig/cloud/dig-blob-key.ts:13-23`), enqueue validates by `startSec` (`lib/dig/cloud/enqueue-dig-core.ts:33-39`), titles are fallbacks (`lib/html-doc/dig-merge.ts:120-155`) and magazine freshness (`lib/html-doc/read-model.ts:12-24`). But stable-blob-addressing says orphaning occurs when both `startSec` and title move, and title is currently load-bearing (`docs/superpowers/specs/2026-08-03-stable-blob-addressing-design.md:51-58`, `:361-383`).
Suggested fix: change the spec claim to: “a reworded heading alone does not orphan a dig if `startSec` is stable; it does drop magazine gists and removes the fallback if `startSec` also drifts.”

8. `docs/superpowers/specs/2026-08-22-corrections-in-cloud-design.md:276-283` has mixed consumer/mechanism falsifiers.
Scenario: “irreducible clause always runs” asserts Gemini call count, not outcome; “one core, no drift” can pass with byte-identical wrong output from both callers. These would certify wiring while missing a discarded cloud blob or stale card.
Suggested fix: add consumer assertions: visible cloud card/body both corrected after attended run; published body and card both corrected after unattended run; skipped route leaves blob bytes, card fields, `processedAt`, `docVersion`, `mdGeneratedAt`, `annotationsEditedAt`, and effective sync decision unchanged except `mdCorrectionsHash`.

**Low / Verification Notes**

- Verified: only one current `fixSummary` apply path, `app/api/videos/[id]/regenerate/route.ts:63`; worker has zero `corrections` occurrences; cloud UI hides corrections in `VideoMenu` (`components/VideoMenu.tsx:48-52`, `:181-190`).
- Verified: `regenerate` does not call `summaryCore`, `generateSummary`, or `resolveTranscriptSegments`.
- Cost derivation: constants match `30` input cents and `250` output cents per 1M tokens (`lib/gemini-cost.ts:33-35`). Recomputing from the spec’s 7,288 chars gives about `0.64¢` for one successful fix+quick-view with a 300-token quick-view output; min/max from stated sizes gives about `0.56¢-0.77¢`. With 3 retry attempts, exposure is about `1.7¢-2.3¢`, so `≤0.6¢ per duplicate` is only true for typical successful calls, not retry/failure exposure.
- NOT VERIFIED: the `yps-sync-test/*/raw/0*.md` fixture table. `yps-sync-test` does not exist in this checkout, and no `raw/0*.md` files were found.
- NOT VERIFIED: backlog #23’s “99 existing free-form corrections,” same as the spec.

NOT CONVERGED
