<!-- codex-review: model=gpt-5.5 -->

**Blocking**
None found.

**High**
1. `ServeBudget` still has a mutable, unbranded attempt count, so the budget class is not closed.  
[lib/serve-budget.ts](/Users/kujinlee/.claude-tmp/claude-501/-Users-kujinlee-code-agentic-ai-docs-youtube-playlist-summaries-cloud/7f3e6e7c-48cc-4021-82de-bc8d060ca442/scratchpad/wt-codex-r4/lib/serve-budget.ts:140): `attempts: number;`  
Failure scenario: any future `lib/` module can do `SERVE_BUDGET.attempts = 3;` and `tsc --noEmit` still exits 0. I verified this with a temporary file, then removed it and confirmed a clean worktree. The production caller then reaches [lib/html-doc/serve-doc.ts](/Users/kujinlee/.claude-tmp/claude-501/-Users-kujinlee-code-agentic-ai-docs-youtube-playlist-summaries-cloud/7f3e6e7c-48cc-4021-82de-bc8d060ca442/scratchpad/wt-codex-r4/lib/html-doc/serve-doc.ts:137): `SERVE_BUDGET,` and [lib/gemini.ts](/Users/kujinlee/.claude-tmp/claude-501/-Users-kujinlee-code-agentic-ai-docs-youtube-playlist-summaries-cloud/7f3e6e7c-48cc-4021-82de-bc8d060ca442/scratchpad/wt-codex-r4/lib/gemini.ts:574): `budget ? budget.attempts - 1 : undefined`.  
Caller: `resolveMagazineModel` on the cloud serve materialization path.  
Premises: [VERIFIED: lib/serve-budget.ts:146 `export const SERVE_BUDGET = {`], [VERIFIED: lib/serve-budget.ts:150 `} as ServeBudget;`], [VERIFIED: lib/gemini.ts:574 `budget ? budget.attempts - 1 : undefined`].  
Fix: make the object immutable and make attempts load-bearing at type level, e.g. `readonly attempts: typeof SERVE_ATTEMPTS` plus `Object.freeze(...)`, or brand `ServeAttempts` as well.

2. `ledger_audit` is writable by session DB roles via `TRUNCATE`, so the settle witness is not durable against those roles.  
[supabase/migrations/0020_reservation_release.sql](/Users/kujinlee/.claude-tmp/claude-501/-Users-kujinlee-code-agentic-ai-docs-youtube-playlist-summaries-cloud/7f3e6e7c-48cc-4021-82de-bc8d060ca442/scratchpad/wt-codex-r4/supabase/migrations/0020_reservation_release.sql:21): `alter table ledger_audit force  row level security;   -- no policies → no session-client access at all`  
[supabase/migrations/0020_reservation_release.sql](/Users/kujinlee/.claude-tmp/claude-501/-Users-kujinlee-code-agentic-ai-docs-youtube-playlist-summaries-cloud/7f3e6e7c-48cc-4021-82de-bc8d060ca442/scratchpad/wt-codex-r4/supabase/migrations/0020_reservation_release.sql:22): `grant select, insert on ledger_audit to service_role;  -- the ONLY grant; mirrors spend_ledger`  
Failure scenario: live DB check showed `has_table_privilege('authenticated','public.ledger_audit','truncate') = true`; `begin; set local role authenticated; truncate public.ledger_audit; rollback;` succeeded. RLS does not save this property for `TRUNCATE`.  
Caller: any SQL-capable session using the `authenticated` or `anon` DB role. [ASSUMPTION] If the only exposed session surface is PostgREST, this may not be reachable through ordinary Supabase JS, but the DB grant invariant is false.  
Fix: explicitly `revoke all on ledger_audit from public, anon, authenticated; grant select, insert on ledger_audit to service_role;` and add a migration test for `TRUNCATE`.

**Medium**
1. The migration-file index does not support the documented prefix lookup on `note`; it only narrows by `kind`.  
[supabase/migrations/0025_settle_is_observable.sql](/Users/kujinlee/.claude-tmp/claude-501/-Users-kujinlee-code-agentic-ai-docs-youtube-playlist-summaries-cloud/7f3e6e7c-48cc-4021-82de-bc8d060ca442/scratchpad/wt-codex-r4/supabase/migrations/0025_settle_is_observable.sql:32): `create index if not exists ledger_audit_kind_note_idx on ledger_audit (kind, note);`  
Failure scenario: recreating that exact DDL on a temp table produced `Index Cond: (kind = 'serve_settle'::text)` and `Filter: (note ~~ '...:%'::text)`, so a growing table scans all `serve_settle` rows for each reconciliation. The live shared DB currently has `note text_pattern_ops`, but the checked-in migration does not.  
Caller: operator following [lib/html-doc/serve-doc.ts](/Users/kujinlee/.claude-tmp/claude-501/-Users-kujinlee-code-agentic-ai-docs-youtube-playlist-summaries-cloud/7f3e6e7c-48cc-4021-82de-bc8d060ca442/scratchpad/wt-codex-r4/lib/html-doc/serve-doc.ts:197): ``RESOLVE: select * from ledger_audit where kind = 'serve_settle' and note like ``.  
Fix: create the index with `note text_pattern_ops`, preferably under a new name or with drop/recreate so already-applied plain indexes are repaired.

**Low**
None.

**Redesign 1 (Brands): Does It Close The Class?**
Not fully. I tried literals, arithmetic, `Number(x)`, unary `+x`, `Math.min(A, B)`, wrong branded constants, object literals, spread/object assign replacements, and test minters. The timeout fields do their job: [VERIFIED: lib/serve-budget.ts:141 `attemptTimeoutMs: AttemptBudget;`], [VERIFIED: lib/serve-rpc.ts:31 `timeoutMs: ReserveRpcBudget | SettleRpcBudget,`], [VERIFIED: lib/html-doc/model-store.ts:67 `timeoutMs: PutBudget,`]. `tests/support/budget.ts` is test-only and warns against `lib/` imports at [tests/support/budget.ts](/Users/kujinlee/.claude-tmp/claude-501/-Users-kujinlee-code-agentic-ai-docs-youtube-playlist-summaries-cloud/7f3e6e7c-48cc-4021-82de-bc8d060ca442/scratchpad/wt-codex-r4/tests/support/budget.ts:12): `If you find yourself importing these from lib/, something has gone wrong`.

But `attempts` remains mutable plain `number`, so `SERVE_BUDGET.attempts = 3` compiles. Local generation remains unaffected: [VERIFIED: lib/gemini.ts:105 `const REQUEST_TIMEOUT_MS = 60_000;`], [VERIFIED: lib/gemini-cost.ts:22 `export const GENERATE_JSON_RETRIES = 2;`], [VERIFIED: lib/gemini.ts:267 `timeoutMs = REQUEST_TIMEOUT_MS,`], and the unit test pins it at [tests/lib/gemini-serve-budget.test.ts](/Users/kujinlee/.claude-tmp/claude-501/-Users-kujinlee-code-agentic-ai-docs-youtube-playlist-summaries-cloud/7f3e6e7c-48cc-4021-82de-bc8d060ca442/scratchpad/wt-codex-r4/tests/lib/gemini-serve-budget.test.ts:100): `expect(seen).toEqual(Array(LOCAL_ATTEMPTS).fill(LOCAL_REQUEST_TIMEOUT_MS));`.

**Redesign 2 (Observable Settle): Is The Biconditional True, And Is The SQL Faithful To 0020?**
Mostly yes on function semantics. The witness is past the no-op gate: [VERIFIED: supabase/migrations/0025_settle_is_observable.sql:50 `if not found then return false; end if;`], then [VERIFIED: supabase/migrations/0025_settle_is_observable.sql:56 `insert into ledger_audit(day, kind, expected_amt, note, at)`]. A later underflow branch is in the same transaction, so if it raises, the witness and settle update roll back together. Same-token double settle is blocked for the normal one-row case because the first update clears the token: [VERIFIED: supabase/migrations/0025_settle_is_observable.sql:47 `set reserved_cents = 0, release_token = null`].

Faithfulness to `0020:268-298`: I diffed the bodies. The only semantic difference I found is the documented witness insert; remaining textual differences are `create or replace` and blank/comment lines. Security definer/search path are preserved: [VERIFIED: supabase/migrations/0025_settle_is_observable.sql:38 `returns boolean language plpgsql security definer set search_path = public as $$`]. Grants on the function remain because the signature is unchanged, and live DB showed `EXECUTE` for `anon` and `authenticated`.

The durability promise is weakened by the table `TRUNCATE` grant finding above, and the checked-in index is not the index needed for the documented `LIKE '<token>:%'` lookup.

**Escalation Verdict**
Not converged. The settle redesign is conceptually the right shape, but its operational witness needs grant hardening and the checked-in index must match the lookup. The budget redesign improved the timeout fields, but the class still leaks through mutable plain `attempts`.

Verification run:
`npx tsc --noEmit --pretty false` passed.  
`npm test -- --runInBand` passed: 263 suites, 2656 tests.  
`npm run test:integration -- settle-rpc-shape` passed.  
`npm run test:integration -- reservation-release` failed 2 existing behavior assertions around active/crashed job reservation retention; I did not attribute those to the two redesigns.  
Final `git status --short` was clean.

NOT CONVERGED.
