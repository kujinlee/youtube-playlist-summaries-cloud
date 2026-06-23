# Quick Reference Callout — Fallback So It's Never Silently Skipped

**Date:** 2026-06-23
**Branch:** `fix/quick-reference-fallback`
**Status:** Design — pending adversarial review gate.

## Problem

The `> [!summary] Quick Reference` callout is inserted by `writeSummaryDoc` (`lib/pipeline.ts:68`) **only when both `tldr` and `takeaways` are present**:
```ts
const mdContent = (tldr && takeaways) ? insertQuickViewCallout(...) : baseContent;
```
`tldr`/`takeaways` come from `generateSummary`, where they are **optional** in the response schema — the model sometimes omits one or both. When it does, the callout is silently skipped. **7 of 269** summaries currently lack it (e.g. `hermes` has tldr but no takeaways; `ponytail` has neither).

This also caused a regression: my PR #17 timestamp repair **re-summarized** `n32qq7Kwzh0` (hermes), and that re-generation returned no `takeaways` → its Quick Reference callout was dropped. Any re-summarize/sync is exposed to this.

A backfill mechanism already exists (`app/api/quick-view/backfill/route.ts` → `extractQuickView` + `insertQuickViewCallout`), but it is an after-the-fact, user-triggered cure; newly-generated docs still ship without the callout until backfilled.

## Decision

Add a **fallback in `writeSummaryDoc`**: when `generateSummary` does not return both `tldr` and `takeaways`, derive them from the generated summary via the existing `extractQuickView`, then insert the callout. This guarantees the callout is present on every newly-generated/re-summarized doc, using the same primitive the backfill route uses.

**Behavior:**
- `generateSummary` returns **both** `tldr` && `takeaways` → unchanged (insert callout with those; no extra call).
- `generateSummary` returns **not both** (neither, or only one) → call `extractQuickView(summary)` to derive a consistent `{tldr, takeaways}` pair, insert the callout with the derived values, and **return the derived values** (so the caller persists them in the index and the "missing Quick Reference" count stays correct). The partial value from `generateSummary` is discarded in favor of the consistent derived pair.
- `extractQuickView` **throws** (Gemini failure after its own retries) → graceful: write the summary **without** the callout (today's behavior) and return `tldr`/`takeaways` as `undefined`. A missing callout must never fail the whole summary.

`extractQuickView` is a second Gemini call, but it fires **only** when `generateSummary` omitted the fields (rare) — a targeted, cheaper fallback than re-rolling the entire summary JSON.

## Why here (not a generateSummary retry)

The timestamp guard (PR #17) retries `generateSummary` on missing ▶. Retrying for missing tldr/takeaways would re-roll the whole summary (ratings, sections, …) when the summary itself is fine — wasteful. `extractQuickView` targets exactly the missing fields from the already-good summary text, and is the same function the backfill route trusts.

## Components & boundaries

| Unit | Responsibility | Change |
|------|----------------|--------|
| `lib/pipeline.ts` `writeSummaryDoc` | fallback to `extractQuickView` when generateSummary omits tldr/takeaways; persist derived values | Modify |

`extractQuickView`, `insertQuickViewCallout` unchanged. No signature change to `writeSummaryDoc` (its result already carries `tldr`/`takeaways`). All `writeSummaryDoc` callers (runIngestion, ensure/repair via `ensureHtmlDoc`) automatically benefit.

## Migration

After merge, backfill the **7** affected summaries (mirror the backfill route: read `.md` → `extractQuickView` → `insertQuickViewCallout` → write `.md` → `updateVideoFields({tldr, takeaways})`). No re-summarize. A throwaway script over the 7 ids, run with env sourced.

## Testing (TDD — mock `lib/gemini`)

`tests/lib/pipeline.test.ts` already mocks `lib/gemini` wholesale; add `mockExtractQuickView = jest.mocked(gemini.extractQuickView)`. Test `writeSummaryDoc` directly (it is exported):
1. **Both present → no fallback:** `generateSummary` returns tldr+takeaways → `extractQuickView` NOT called; `.md` contains the callout with those values; result carries them.
2. **Neither present → fallback inserts:** `generateSummary` returns no tldr/takeaways; `extractQuickView` resolves `{tldr:'X', takeaways:['a','b']}` → `extractQuickView` called once; `.md` contains the callout with X/a/b; result `.tldr==='X'`, `.takeaways==['a','b']`.
3. **Only one present (the hermes case) → fallback inserts:** `generateSummary` returns tldr but no takeaways → fallback derives both; callout present.
4. **extractQuickView throws → graceful:** `generateSummary` omits both, `extractQuickView` rejects → `.md` written WITHOUT the callout (no `[!summary] Quick Reference`), `writeSummaryDoc` resolves (does not throw), result `tldr`/`takeaways` undefined.
5. **Regression:** existing writeSummaryDoc/ingestion tests (callout-present, frontmatter, tags) stay green.

Full `npm test` + `npx tsc --noEmit` green before commit. Dual review per task.

## Out of scope

- Changing `generateSummary`'s schema/prompt (tldr/takeaways stay optional there; the fallback handles omission).
- The backfill route/UI (unchanged; still available for older docs).
- The other ~? older summaries missing the callout beyond the audited 7 from older doc versions (they re-gen lazily and now get the fallback; a corpus-wide backfill is the user's optional call, not in this fix).
