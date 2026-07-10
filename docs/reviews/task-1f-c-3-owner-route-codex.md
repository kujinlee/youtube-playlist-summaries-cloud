# Codex Adversarial Review — Stage 1F-c Task 3 (owner route format/download + MD branch)

**Reviewer:** Codex (gpt-5.5, run from coordinator) · **Date:** 2026-07-10 · **Diff:** 9d4477f..8e0ce76
**Verdict:** No Blocking/High. 1 Medium, 1 Low.

## Medium
- **`app/api/html/[id]/route.ts:32` — repeated `format` params bypass validation.** `searchParams.get('format')` reads only the first value. Scenario: `GET ?playlist=<uuid>&type=summary&format=html&format=pdf` returns 200 HTML and charges through the HTML path even though the request contains an invalid `format=pdf`; likewise `format=md&format=pdf` returns MD. Fix: validate `searchParams.getAll('format')` — allow zero values or exactly one value in `html|md`; reject duplicates/invalid before deriving `format`.

## Low
- **`tests/integration/html-download.test.ts:84` — C1 does not assert the full header set**, only selected headers. An unintended extra header (other than Referrer-Policy / Content-Disposition, which are asserted absent) could slip through. Fix: assert the normalized full header key set equals the legacy set plus `x-content-type-options`, CSP nonce pattern-matched.

## Verified Invariants
- **D4** holds: `format === 'md'` returns at route.ts:77 after blob read/409, before parseSummaryMarkdown/resolveMagazineModel (route.ts:86). Missing model cannot charge — model resolution unreachable for MD.
- **D5** preserved: `resolveMagazineModel` remains once, same post-parse position, before render + response wrapping.
- **C1** route call passes no `referrerPolicy`; fileResponse emits it only when supplied.
- Non-200 branches return `json(...)` directly before fileResponse; missing promoted blob remains 409.
- **C2/C3** money tests meaningful: spy on reserve_serve_model, compare spend_ledger, assert generation not called.

## Disposition
Medium + Low both fixed in follow-up (see task-3-report.md fix section) — `getAll` duplicate/invalid rejection + full-header-set C1 assertion. 0 Blocking/High → §8 convergence gate met on round 1.
