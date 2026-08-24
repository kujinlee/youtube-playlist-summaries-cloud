<!-- codex-review: model=gpt-5.5 -->

**Blocking**

1. `docs/superpowers/specs/2026-08-22-corrections-in-cloud-design.md:287` uses `exists(finalKey)` as if it means “promotion cannot publish.” It does not.
Scenario: `SupabaseBlobStore.exists()` is `get() !== null` (`lib/storage/supabase/supabase-blob-store.ts:85-87`), and `get()` converts every download error to `null` (`:34-43`). A transient storage failure, timeout, or permission-shaped read can make the pre-check return false even when the final key exists. The handler then pays for correction, stages corrected bytes, `promote()` sees the final key and discards the staged blob (`:116-123`), and the row can still persist corrected card/hash for an old body. This reintroduces the round-1 promote divergence through the new guard.
Suggested fix: do not use `exists()` for a money/publication predicate on Supabase. Use `tryGet()` and fail closed on `unreadable`; or make `promote` return an observable `published | already-existed | failed` result and persist corrected card/hash only on `published`.

2. `docs/superpowers/specs/2026-08-22-corrections-in-cloud-design.md:287-289` is TOCTOU even when `exists()` is accurate.
Scenario: pre-check sees final key present and skips correction/stamp. The key is deleted before `promote()`. The worker publishes the uncorrected `summaryCore` body, with no `mdCorrectionsHash`, despite stored corrections existing. That is no longer merely “do not spend on an impossible publish”; the stale observation changed the document that gets published.
Suggested fix: make publication and decision atomic/observable. If final exists, skip the whole write sequence, not just correction; or re-check immediately before promote and abort if the premise changed. Better: fix #22/M5 first and base metadata writes on the actual promotion result.

**High**

3. `docs/superpowers/specs/2026-08-22-corrections-in-cloud-design.md:167-171` still leaves apostrophe tokenization buildable two ways.
Scenario: `'Clawcode's' → 'Claude Code's'`. A first-pair scanner extracts `Clawcode`; a first/last scanner extracts `Clawcode's`; the “single `'` not followed by a closing `'` on the same clause” rule does not choose between them, because the internal apostrophe is followed by a closing quote. Most cases run because `Clawcode` is a substring, but the spec has not actually guaranteed “no false skip” for apostrophe-containing quoted terms.
Suggested fix: define the tokenizer precisely. For ASCII apostrophes, treat `'` as a quote delimiter only at token boundaries, not between word characters; add required cases for quoted possessives and contractions in both left and right terms.

4. `docs/superpowers/specs/2026-08-22-corrections-in-cloud-design.md:243-250` bases the `fixSummary` cap on an unreproducible, undersized sample.
Scenario: the measured max is 8,961 bytes from `~/code/agentic-ai-docs/yps-sync-test/*/raw/0*.md`, outside this repo. I found no `raw/0*.md` files here. Also `wc -c` is bytes, not chars; Korean summaries can diverge materially. A local document above the chosen cap now fails a path that currently succeeds. `assertNotTruncated()` only rejects non-STOP finish reasons (`lib/gemini.ts:245-249`); it does not prove the returned document is complete if the model returns `STOP` after omitting content.
Suggested fix: derive cloud correction output cap from the enforced summary output cap (`MAX_SUMMARY_OUTPUT_TOKENS = 8192`, `lib/gemini-cost.ts:16`), not from local sample bytes. Add semantic post-checks: document still has required sections/timestamps/frontmatter and is not materially shorter except where expected.

5. `docs/superpowers/specs/2026-08-22-corrections-in-cloud-design.md:257-260` defers the load-bearing reservation arithmetic.
Scenario: current summary worst case recomputes to 114.984¢, so `summary_est_cents = 150` has about 35¢ slack. A correction with 8,192 output tokens costs about 7¢ for `fixSummary` plus about 10.2¢ for the second quick-view extraction, so it fits. But if the spec chooses a 32,768-token correction output cap, the extra path is about 36¢ and no longer fits. Since §6.1 does not state the cap, §6.3 cannot prove whether the existing reservation is sound.
Suggested fix: put the arithmetic in the spec, not only the plan. State the exact cap and either prove `summary_est_cents >= summaryWorst + correctionWorst + quickViewWorst`, or require raising `summary_est_cents`.

6. `docs/superpowers/specs/2026-08-22-corrections-in-cloud-design.md:199-202` deliberately changes local bare-pass behavior without proving it is required.
Scenario: `tests/api/regenerate.test.ts:113-116` asserts absent corrections do not call `fixSummary`; `tests/lib/cloud-sync/regenerate-stamp.test.ts:98-107` asserts a bare regenerate stamps against stored corrections. v2 changes apply input to effective corrections, so a bare local press can re-run stored free-form corrections. For irreducible stored text, this becomes a paid full-doc rewrite from a UI action that currently only refreshes quick-view/stamping.
Suggested fix: split stamp input from apply input unless the UX explicitly opts into “re-apply stored corrections.” If decision 3 really requires unifying them, rename the route action and update the local UX/tests as intentional behavior changes.

7. `docs/superpowers/specs/2026-08-22-corrections-in-cloud-design.md:100` still omits validation after `fixSummary` rewrites the document.
Scenario: `generateSummary()` repairs section timestamps with `ensureSectionTimestamps()` (`lib/gemini.ts:390-402`). `fixSummary()` only prompts the model to preserve structure (`:479-489`) and then returns text. A correction can damage `▶` timestamps or headings, weakening dig anchoring and section identity.
Suggested fix: apply the same structural/timestamp validation or repair after `fixSummary`, before extracting quick-view or writing the blob.

**Medium**

8. `docs/superpowers/specs/2026-08-22-corrections-in-cloud-design.md:145-156` handles the named punctuation cases safely, but only by forcing RUN.
`""` and whitespace hit rule 1. Bare `;`, bare arrow, empty quotes, punctuation-only clauses, and arrow-without-quotes all reach RUN through irreducible/no-terms branches. That avoids the old empty-case inversion, but it also means many no-op inputs can still spend. Suggested fix: explicitly document this as “fail toward spend,” and return outcome evidence so callers can distinguish “irreducible spend” from “matched-term spend.”

9. `docs/superpowers/specs/2026-08-22-corrections-in-cloud-design.md:315` still has a consumer/mechanism mismatch for spending.
“A run spends a bounded amount | ledger moves by `correction_est_cents`, and actual ≤ cap” is not a consumer assertion unless the route/job reservation and settlement semantics are specified. `fixSummary()` currently has no billing opts (`lib/gemini.ts:470-496`), while `generateJson()` flips the latch (`:264-275`).
Suggested fix: specify route-side reserve/settle/release or explicitly make corrections job-scoped. Add a test that fails if `fixSummary` receives no latch.

10. `docs/superpowers/specs/2026-08-22-corrections-in-cloud-design.md:245-247` assumes `thinkingBudget: 0` is safe for correction quality.
NOT VERIFIED. The repo has live gates for `thinkingBudget: 0` billing behavior (`tests/integration/gemini-live-gates.test.ts`), but I did not find evidence that full-document correction quality remains acceptable with thinking disabled.
Suggested fix: require a small live/fixture eval before enabling cloud correction caps, or state quality risk explicitly.

**Low**

11. `docs/superpowers/specs/2026-08-22-corrections-in-cloud-design.md:45` still says “chars” for a `wc -c` measurement. That is bytes, and the source path is outside this repo. NOT VERIFIED.

12. Several citations still drift: `getStorageBundle()` is at `app/api/videos/[id]/regenerate/route.ts:36`, not spec `:35`; the effective rule is `:77-79`, not `:78-80`; the UI gate is `components/VideoMenu.tsx:181`, not the `VideoRow.tsx:19` prop comment.

**Round-1 Disposition**

Codex: C1 fixed; C2 partly fixed; C3 partly fixed with new `exists()`/TOCTOU defect; C4 partly fixed, mitigation deferred; C5 fixed; C6 partly fixed, cap/amount still missing; C7 fixed; C8 partly fixed.

Claude: B1 fixed but creates local no-write/test churn; B2 fixed deliberately but scope/UX risk remains; B3 fixed in spec; H1 partly fixed; H2 partly fixed; H3 partly fixed, timestamp validation still absent; H4 partly fixed, apostrophe tokenizer still ambiguous; H5 fixed; H6 partly fixed but §8 guard is wrong; H7 partly fixed. M1 fixed; M2 fixed at spec level; M3 fixed; M4 fixed at spec level; M5 partly fixed; M6 fixed; M7 fixed at spec level; M8 fixed. L1/L2/L3/L4/L5/L6/L8 partly or not fixed; L7 fixed.

**Derivations Re-run**

`fixSummary` apply paths: one current call site, `app/api/videos/[id]/regenerate/route.ts:63`. Worker has zero current `corrections` references.

Cost: recomputed summary worst case is 114.984¢, ceiling 115¢, so default 150¢ has ~35¢ slack. Correction worst depends on the missing cap: at 8,192 output tokens, fix-only is ~7¢; plus quick-view worst is ~10.2¢.

Summary-size row: unreproducible in this repo; no `raw/0*.md` fixtures found. Also byte/char wording is wrong.

NOT CONVERGED
