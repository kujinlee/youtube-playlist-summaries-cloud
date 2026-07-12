# Task 2 Review — dig-blob-key + write-dig-section-blob (Approved, converged)

Task review of commit `9eb3949` (base `d829f68`); test-gap fix `4dee576`.
Diff: `lib/dig/cloud/dig-blob-key.ts` (`digSectionKey`, `digJobVersion`), `lib/dig/cloud/write-dig-section-blob.ts` (`writeDigSectionBlob`), + their tests.

Pure-function pair, no money/auth/concurrency surface → single Claude task-reviewer (sonnet) is proportionate per the plan; Codex not dispatched (task risk does not meet the money/auth bar that warrants the adversarial pass).

## Claude task-reviewer — ✅ Spec compliant, Task quality Approved
All five binding constraints verified against the diff:
- **Key shape** `dig/{base}/{sectionId}.r{DIG_GENERATOR_VERSION}.md` — `dig-blob-key.ts:20`.
- **Text-only writer** — no `resolveSlideTokens` import/call; `bodyMarkdown` only `trimEnd()`'d, `[[SLIDE:...]]` tokens untouched (`write-dig-section-blob.ts:93`); `slides: []` literal in frontmatter (`:89`).
- **Base guard** rejects `/`, `\`, `\0`, `.`, `..` (`dig-blob-key.ts:65`); `digJobVersion()` → `dig-${DIG_GENERATOR_VERSION}` (`:25`).
- **staged→promote only** — `putStaged` → `exists(tempKey)` → `promote`; `put()` never called (`write-dig-section-blob.ts:96-100`).
- **Version single-sourced** — `DIG_GENERATOR_VERSION` imported once from `lib/dig/generate.ts:13` (`= 9`), reused for both key suffix and `genVersion:`; never hard-coded.

Verified beyond the diff (named-risk checks): `BlobStore`/`Principal`/`StagedRef` shapes match the real interfaces (`lib/storage/blob-store.ts:5-14`, `lib/storage/principal.ts:5-8`) — 4-arg `putStaged` matches production, not just the looser mock. Writer test proves ordering via a real call-sequence array (`putStaged` → `exists` → `promote`) and verbatim token survival — non-vacuous.

## Findings

### Important (plan-mandated) — FIXED (`4dee576`)
Base-guard `it.each` asserted `slash`/`parent`/`nul` but not the lone-`\`, lone-`.`, or empty-string branches. Guard logic already rejects all five correctly (reviewer confirmed against the implementation); only the per-branch assertions were missing. **Disposition:** fixed inline — test-only, additive; added `backslash`/`lone-dot`/`empty` cases; `npx jest dig-blob-key` 11/11 pass. No re-review round: the fix adds assertions for branches the reviewer already confirmed correct in the shipped guard; it changes no production code.

### Minor (rolled up for whole-branch triage)
- `write-dig-section-blob.ts:71-73` `yamlScalar` escapes `\` and `"` but not embedded `\n`/`\r`, unlike sibling `yamlQuote` in `lib/dig/companion-doc.ts:56-60`. Low-risk (YouTube titles can't contain literal newlines). Align if `title` provenance ever changes.
- Single-path-component base-guard logic now duplicated across `lib/pdf/pdf-render-version.ts:18`, `lib/dig/cloud/dig-blob-key.ts:65`, and `lib/html-doc/assert-cloud-summary-md-key.ts`. A future `assertSinglePathComponent(base)` helper would consolidate. Note: `pdfCacheKey`'s guard does NOT reject a lone `.` — the new one is intentionally stricter per this task's spec, so a naive unification would change `pdfCacheKey` behavior.

## Disposition
Converged. Approved with the one Important test-gap fixed inline; 2 Minor deferred to whole-branch triage. Tests: dig-blob-key 11/11, writer 2/2; full suite 2086/2086 per implementer report; tsc clean.
