<!-- codex-review: model=gpt-5.5 -->

**Blocking**

- [v3-REGRESSION] §4.2 lines 353, 392-395 silently revokes the existing verified 429/503 refund behavior.  
  Concrete failure: `generateContent` returns `GoogleGenerativeAIFetchError` 429 before a body. Today `billing.metered === false`, `classifyGeminiFailure()` returns `release`, and `serve-doc.ts:130-133` settles with `p_released := true`. v3 sets `attempted := true` before the call and says “otherwise keep the charge,” so the same rejected call now keeps 6¢.  
  What I checked: [gemini-failure.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/gemini-failure.ts:4) has an explicitly verified release set `{429,503}`; [serve-doc.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/html-doc/serve-doc.ts:130) releases on classifier `release && !billing.metered`.

- [v3-REGRESSION] §3.2 lines 229-231 returns `busy` for a refunded self-abandon, collapsing a new condition into the existing single-flight sentinel.  
  Concrete failure: RPC takes 100s, returns `reserved`, `budget_seconds = 180`; local remaining is ~80s, below `SERVE_REQUIRED_MS = 85s`. v3 settles/release and returns `busy`. The caller sees the same status as “another producer holds the lease” from `serve-doc.ts:83-86`, but no producer exists. Worse, `settle_serve_model` clears money/token but does not clear `lease_expires_at`, so retries continue to see `in_flight` until expiry.  
  What I checked: `busy` currently means unreadable transient or in-flight generation at [serve-doc.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/html-doc/serve-doc.ts:68) and [serve-doc.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/html-doc/serve-doc.ts:84); `settle_serve_model` only clears `reserved_cents`/`release_token` at [0020_reservation_release.sql](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/supabase/migrations/0020_reservation_release.sql:277).

**High**

- [v3-REGRESSION] §4.2 lines 392-395 claims the only reachable refund is the viability check, but there are pre-Gemini throws after reserve.  
  Concrete failure: after `reserved`, `generateMagazineModel` can throw before any Gemini call: `GEMINI_API_KEY` missing, `GoogleGenerativeAI`/`getGenerativeModel` construction failure, caps missing `magazineInputTokens/magazineOutputTokens`, or cap missing inside `assertMagazineInputWithinCap` before `countTokens`. If the rule is literally “refund iff no Gemini call,” these should refund; if “only viability refunds,” they keep. The spec states both.  
  What I checked: pre-call throw sites at [gemini.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/gemini.ts:109), [gemini.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/gemini.ts:508), and [gemini.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/gemini.ts:79).

- [v3-REGRESSION] §4.2.1 lines 401-418 adds `BillingLatch.attempted` as a shared required field but only gives it serve-path semantics.  
  Concrete failure: construction sites that must change are `serve-doc.ts:110`, `worker-runner.ts:35`, and multiple tests/typed contexts using `{ metered:false }`. If `generateJson` mutates `attempted` globally but `worker-runner.ts:66-76` still consults only `metered`, the same latch field means “refund guard” on serve and “unused bookkeeping” on workers. That is two mechanisms for one concern.  
  What I checked: `BillingLatch` is only `{ metered:boolean }` at [billing-latch.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/job-queue/billing-latch.ts:7); worker release still uses classifier plus `!billing.metered` at [worker-runner.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/job-queue/worker-runner.ts:66).

- [v3-REGRESSION] §3.0/§3.5 lines 184-186 and 324-331 present invented constants as already sourced.  
  Concrete failure: `85 = ceil((10000 + 60000 + 15000)/1000)` is arithmetically correct and `85 <= 180` matches the shipped TTL, but `COUNT_TOKENS_BUDGET_MS`, `RESERVED_TAIL_MS`, `MIN_VIABLE_ATTEMPT_MS`, and exported `SERVE_REQUIRED_MS` do not exist today. `REQUEST_TIMEOUT_MS` exists but is private in `gemini.ts`. A test cannot compute the migration literal from “app constants” until the spec defines where those constants live and how they avoid import cycles.  
  What I checked: [gemini.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/gemini.ts:94) has private `REQUEST_TIMEOUT_MS`; [gemini-cost.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/gemini-cost.ts:20) has retry constants but not these deadline constants.

**Medium**

- [v3-REGRESSION] §3.1 lines 199-204 misuses `ledger_audit` for migration-time configuration reporting.  
  Concrete failure: an install has `lease_ttl_seconds = 60`; migration inserts a `ledger_audit` row so the condition is “visible.” The table is explicitly for guarded ledger decrement invariant violations, with current `kind='release_underflow'` rows tied to failed money reconciliation. A config warning has no meaningful `expected_amt`, is not caused by a decrement, and is hidden from anon/authenticated by forced RLS/no policies.  
  What I checked: schema and comment at [0020_reservation_release.sql](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/supabase/migrations/0020_reservation_release.sql:7); existing inserts are all release-underflow paths at [0020_reservation_release.sql](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/supabase/migrations/0020_reservation_release.sql:85).

- [v3-REGRESSION] §6 lines 521-536 still says “function first, then app” but v3 added a load-bearing config column.  
  Concrete failure: if migration 0024 creates/replaces `reserve_serve_model` before `guardrail_config.min_required_seconds` exists, the function body references a missing column and the migration fails. If the column lands after the function outside the same transaction, the new app can call a function whose required-understated gate cannot run. The column must precede the function in the DB migration order; §6 does not state that.  
  What I checked: v3 requires `min_required_seconds` in the RPC gate at §3.1; current `guardrail_config` only has `lease_ttl_seconds` default 180 from [0012_serve_model_charge.sql](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/supabase/migrations/0012_serve_model_charge.sql:20).

NOT CONVERGED.
