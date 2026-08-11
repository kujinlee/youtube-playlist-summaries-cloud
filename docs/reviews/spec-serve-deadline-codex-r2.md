<!-- codex-review: model=gpt-5.5 -->

**Blocking**

- [v2-REGRESSION] [§3.2 lines 160-172](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-10-serve-path-deadline-design.md:160) uses the wrong clock start for queued/rescheduled RPCs.  
  Concrete failure: app captures `t0`, then the Supabase/PostgREST request sits behind connection pooling or a client retry delay for 170s before the DB function actually starts. The DB grants a fresh 180s lease and returns `budget_seconds ~= 180`, but the app deadline has only ~10s left because it started before the lease existed. `countTokens`/generation aborts, money may refund, but `attempt_count` is still burned. Five such queued reserves brick the document as `attempts_exhausted`.  
  What I checked: current release path does not decrement `attempt_count` in [0020_reservation_release.sql](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/supabase/migrations/0020_reservation_release.sql:277); `attempt_count` is bounded by `max_serve_attempts` in [0012_serve_model_charge.sql](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/supabase/migrations/0012_serve_model_charge.sql:21). The proof `t0 <= lease_start` is true but proves the wrong thing: it converts pre-lease queue time into post-reserve budget loss.

- [v2-REGRESSION] [§3.1/§3.5 lines 122-127, 241-255](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-10-serve-path-deadline-design.md:122) has an unresolved seconds/ms split that can make the gate either fail open or fail closed.  
  Concrete failure: RPC argument is `p_required_seconds int`, DB columns are seconds, returned value is `budget_seconds`; the app constant is named `SERVE_REQUIRED_MS`, built from `*_MS` constants, and §3.2 says `performance.now() + budget_seconds` even though `performance.now()` is milliseconds. Literal implementation either passes milliseconds into a seconds column (`70000` seconds -> `lease_too_short` forever) or adds seconds to a millisecond clock (`180` ms deadline -> immediate abort).  
  What I checked: spec lines above; current DB TTL is seconds in [0012_serve_model_charge.sql](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/supabase/migrations/0012_serve_model_charge.sql:22); current timeout constants are milliseconds in [gemini.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/gemini.ts:94).

- [v2-REGRESSION] [§4.1-§4.3 lines 277-320](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-10-serve-path-deadline-design.md:277) rests the refund rule on an unproven and likely unsafe premise: “`countTokens` is free.”  
  Concrete failure: `countTokens` completes or is issued, no `generateContent` is attempted, then the path throws/aborts and v2 refunds because `billing.attempted === false`. If Google bills `countTokens` input tokens or counts it as an applicable operation, this creates an under-count.  
  What I checked: SDK only says aborted operations may still be charged in [generative-ai.d.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/node_modules/@google/generative-ai/dist/generative-ai.d.ts:1297); official Gemini billing says pricing is based on input/output/cached token counts, not that `countTokens` is non-billable: https://ai.google.dev/gemini-api/docs/billing. The official token guide describes `count_tokens` as an API call for request inputs, but does not state it is free: https://ai.google.dev/gemini-api/docs/tokens.

**High**

- [v2-REGRESSION] [§3.1 lines 125-140, §6 lines 383-400](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-10-serve-path-deadline-design.md:125) adds `min_required_seconds` without specifying its migration default or synchronization rule with the app constant.  
  Concrete failure: migration adds `min_required_seconds default 1`; hostile callers can pass `1` and the B2 bypass mostly remains. Migration defaults to the intended app value but the app computes a different value after deploy; all fresh materializations return `required_understated`. Existing deployed DBs with customized `lease_ttl_seconds` can also become unusable if the new floor exceeds their TTL.  
  What I checked: current `reserve_serve_model` is granted to `authenticated, anon` in [0020_reservation_release.sql](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/supabase/migrations/0020_reservation_release.sql:263); current config columns have explicit defaults in [0012_serve_model_charge.sql](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/supabase/migrations/0012_serve_model_charge.sql:20). v2 gives no default for the new load-bearing column.

- [v2-REGRESSION] [§3.3/§3.5 lines 201-204, 243-246](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-10-serve-path-deadline-design.md:201) says the declared requirement is “one attempt plus tail,” but actually derives it from `MIN_VIABLE_ATTEMPT_MS`, not the attempt timeout the code spends.  
  Concrete failure: choose `MIN_VIABLE_ATTEMPT_MS = 5s`, `RESERVED_TAIL = 10s`, `countTokens = 5s`; DB accepts a 20s lease as sufficient. Under §3.3 the first `generateContent` timeout is `min(REQUEST_TIMEOUT_MS, remaining - tail)`, so the “one attempt” is only ~5s, not the existing 60s attempt. This is not “one attempt plus settling”; it is “one shortest-worth-trying attempt plus settling.”  
  What I checked: current generate timeout is 60s in [gemini.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/gemini.ts:259); §2.1’s conclusion depends on a truthful declared requirement.

- [v2-REGRESSION] [§4.2 lines 290-302](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-10-serve-path-deadline-design.md:290) changes the shared `BillingLatch` shape without specifying impact on existing worker callers.  
  Concrete failure: making `attempted` a required field breaks existing initializers like [worker-runner.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/job-queue/worker-runner.ts:35). Making it optional preserves compile but leaves two semantics for one latch depending on caller.  
  What I checked: `BillingLatch` currently has only `metered` in [billing-latch.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/job-queue/billing-latch.ts:7); it is used by serve, summary worker, transcript, summary, dig paths via `rg BillingLatch`.

**Medium**

- [§3.4 lines 232-235](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-10-serve-path-deadline-design.md:232) overstates what `RESERVED_TAIL` proves.  
  Concrete failure: generation can finish within its allowed budget and upload can still timeout because `RESERVED_TAIL` was undersized or because v2’s pre-RPC timer consumed budget before the DB lease began. That is not necessarily “the whole lease exceeded”; it can be a bad tail constant or pre-lease latency accounting.  
  What I checked: write is a plain uncancellable `put` in [model-store.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/html-doc/model-store.ts:45); v2 itself admits failed late upload causes repeat charge bounded by `max_serve_attempts`.

- [§5 lines 369-373](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-10-serve-path-deadline-design.md:369) call-site assertion can be tautological unless it has mutation coverage.  
  Concrete failure: implementation imports `SERVE_REQUIRED_MS` and the test asserts the mock RPC received `SERVE_REQUIRED_MS`; both change together and pass while the constant is incorrectly derived or unit-converted.  
  What I checked: current production call site is [serve-doc.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/html-doc/serve-doc.ts:74); the proposed test does not say to mutate the call site to `1` or mutate ms/seconds conversion and require red.

**Verdict**

NOT CONVERGED.
