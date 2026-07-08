# Stage 1E-b Task 5 — Claude Task Review (summaryCore extraction) + fix

**Reviewer:** Claude (Opus), read-only, adversarial. **Target:** diff `971f500..5cde2dc` (extract store-agnostic `summaryCore`; local re-wire). **Date:** 2026-07-07.
**Verdict:** Approved (byte-identical) → **1 Important fixed** (decoupling leak) → clean.

## Spec compliance: ✅
- **Byte-identical local output:** golden `pipeline-write-summary.test.ts` has zero diff and passes; content-building moved verbatim; `writeSummaryDoc` returns the identical field-set; `runIngestion`'s Video-construction caller destructures the same names; the single `blobStore.put(localPrincipal(...))` unchanged.
- `summaryCore` store-agnostic (no `blobStore`/`localPrincipal`); only the `put` was removed.
- Deps-injected `resolveTranscriptSegments`/`generateSummary` receive `opts?.signal` via a branch that OMITS the 4th arg when absent (preserves `toHaveBeenCalledWith` 3-arg shape); `extractQuickView` called without signal (known Task 4 boundary).
- All three QuickView paths (insert / extractQuickView fallback / fallback-throws→clear) line-identical; `quickView` = `{tldr,takeaways}` else `null`; `geminiFields` same optionality; `checkSummaryCompleteness` warn retained.
- `frontmatter`/`markdown` return fields are spec-required by the brief interface and tested.

## Important (FIXED in follow-up commit)
- **Transitive-dep leak defeated the extraction's purpose.** `summary-core.ts` imported `insertQuickViewCallout` back from `@/lib/pipeline`, forming a `pipeline ↔ summary-core` cycle. The cycle is **runtime-safe** (both symbols used only inside function bodies, never at module-eval time; `tsc` clean, suites green), BUT it transitively pulled pipeline.ts's server-only graph (`fs`, storage/resolve, storage/principal, blob-store, html-doc, index-store) into the "store-agnostic" core. Task 7's cloud worker will `import { summaryCore }` and inherit `fs` → edge/serverless bundle risk, and the "share ONE ingestion core" goal is defeated.
  **Fix:** extracted `insertQuickViewCallout` + `stripQuickViewCallout` (pure string transforms, zero deps) into `lib/quick-view-callout.ts`; `pipeline.ts` re-exports them (so the `regenerate` + `quick-view/backfill` routes that import from `@/lib/pipeline` are unchanged); `summary-core.ts` now imports from the pure module. Cycle broken, transitive leak closed. Full suite 1588 green, golden unchanged, tsc 0.

## Minor — CARRIED FORWARD
- `summary-core.ts` still imports `detectLanguage` (value) from `../youtube` — pre-existing (old `writeSummaryDoc` did too) and NOT the flagged pipeline-graph leak; if `lib/youtube.ts` pulls heavy deps at module-eval, a later cleanup could relocate `detectLanguage` to a pure module. Not in scope; note for Task 7 bundling if it bites.

## ⚠️ Unverifiable from diff — RESOLVED
- Task 7 runtime (edge vs node) severity of the leak: mooted — the leak is now closed regardless.
- Full 1588-suite: re-run by controller (green).

## Task quality verdict: Approved (post-fix — behavior-preserving, byte-identical, and now genuinely decoupled for Task 7).
