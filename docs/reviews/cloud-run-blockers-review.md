# Dual Review — Cloud-Run Blockers (BUG-1, BUG-2, BUG-3)

Branch `fix/cloud-run-blockers`. Fixes for the three blocking defects the first live run surfaced
(see `docs/local-validation-findings.md`). Money/pipeline-critical (job-completion RPC + Gemini
cost-bound schema) → dual adversarial review.

Reviewers: **Claude** (code review) + **Codex adversarial** (gpt-5.5), independent.

## The fixes (all TDD, RED watched before GREEN)
- **BUG-1** `supabase-job-queue.ts` `complete()`: `p_result: result` → `p_result: result ?? null`.
  Handlers return `undefined`; supabase-js drops undefined JSON keys → PostgREST 3-arg lookup →
  `PGRST202` → every job failed at completion. Unit test (JSON-serialization faithful) + integration
  test (real PostgREST — reverting the fix throws the exact `PGRST202`), both RED→GREEN.
- **BUG-2** `gemini.ts` `generateMagazineModel`: removed the cloud-only `maxItems: MAGAZINE_MAX_SECTIONS`
  schema clone (and the now-dead const). A large bound on the nested `sections` array exploded Gemini's
  structured-output constraint-state count → live `400 too many states for serving` on every doc.
  Unit test inverted (cloud schema now has NO maxItems) + **live-gate test run against real Gemini**
  (`RUN_LIVE_GEMINI=1`) confirming the bare schema is accepted.
- **BUG-3** `lib/supabase/client.ts`: dynamic `process.env[name]` → static `process.env.NEXT_PUBLIC_*`
  (Next inlines only literal refs; the helper was `undefined` in the browser → sign-in threw). Smoke
  test for the wrapper contract; the inlining itself is E2E-verified (login works), not jest-catchable.

## Convergent verdict — 0 Blocking / 0 High (both reviewers)

**Claude:** All three correct. BUG-2 cost bound intact — `withCaps` sets `maxOutputTokens =
MAX_MAGAZINE_OUTPUT_TOKENS` (the real cost driver; test-proven), input capped by
`assertMagazineInputWithinCap`, section count validated post-parse; **no** cost proof / guardrail
references `MAGAZINE_MAX_SECTIONS` (grep + tsc). BUG-1 `?? null` maps only null/undefined — valid
falsy results (`0`/`''`/`false`) preserved; `complete()` was the only rpc caller with a possibly-
undefined param (fail_job's `p_error` is always a string). BUG-3 has no server-side caller of the
browser client.

**Codex (gpt-5.5):** "Blocking: None. High: None. Medium: None. Low: None. VERDICT: the three fixes
look correct and safe to merge. BUG-2's removed schema `maxItems` does not remove the real cost bound:
cloud magazine calls still enforce `magazineInputTokens` via `countTokens`, `magazineOutputTokens` via
`maxOutputTokens`, retry count is fixed, `thinkingBudget: 0` is set, section count is validated
post-parse, and `magazine_est_cents = 6` still covers the current worst-case capped magazine call."

## Verification
Unit **2146/2146**, integration **355 passed / 3 skipped** (live-gemini gates opt-in), `tsc` clean,
live Gemini accepts the fixed magazine schema.

## Not in scope (deferred to follow-up branches — see local-validation-findings.md)
BUG-3 (`/api/videos` sort NPE on null title), BUG-4 (Storage "Invalid key" for non-ASCII titles),
BUG-5 (worker swallows handler errors), the worker deploy findings, and the paged-ingestion feature.
