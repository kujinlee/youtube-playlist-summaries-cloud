<!-- codex-review: model=gpt-5.5 -->

**Findings**

No Blocking / High / Medium / Low findings found in round 6.

I did not find an N+4 lease-spent value. The set appears closed.

**The Population Of Lease-Spent Values**

1. Reserve RPC timeout  
[VERIFIED: `lib/html-doc/serve-doc.ts:85`] `const reserve = await callRpcBounded(`  
[VERIFIED: `lib/html-doc/serve-doc.ts:89`] `SERVE_RESERVE_RPC_TIMEOUT_MS, 'reserve_serve_model',`  
[VERIFIED: `lib/serve-budget.ts:80`] `export const SERVE_RESERVE_RPC_TIMEOUT_MS = 5_000 as ReserveRpcBudget;`  
Brand: yes. Passed: yes. What breaks: literals/arithmetic fail `tsc`; reserve/settle RPC swap is covered by `tests/lib/html-doc/serve-bounded-import-guard.test.ts`.

2. Gemini countTokens timeout  
[VERIFIED: `lib/gemini.ts:567`] `await assertMagazineInputWithinCap(model, prompt, generationConfig, caps, {`  
[VERIFIED: `lib/gemini.ts:569`] `...(budget ? { timeoutMs: budget.countTokensTimeoutMs } : {}),`  
[VERIFIED: `lib/serve-budget.ts:83`] `export const SERVE_COUNT_TOKENS_TIMEOUT_MS = 10_000 as CountTokensBudget;`  
Brand: yes in `ServeBudget`; final helper accepts `number`. Passed: yes. What breaks: `tests/lib/gemini-serve-budget.test.ts` observes SDK request options.

3. GenerateContent attempt timeout  
[VERIFIED: `lib/gemini.ts:273`] `const result = await model.generateContent(prompt, { timeout: timeoutMs, signal: opts?.signal });`  
[VERIFIED: `lib/gemini.ts:580`] `budget ? budget.attemptTimeoutMs : undefined,`  
[VERIFIED: `lib/serve-budget.ts:86`] `export const SERVE_ATTEMPT_TIMEOUT_MS = 50_000 as AttemptBudget;`  
Brand: yes. Passed: yes. What breaks: `tsc` at wrapper boundary for wrong brand/literal, plus `tests/lib/gemini-serve-budget.test.ts`.

4. GenerateContent attempts / retry bound  
[VERIFIED: `lib/gemini.ts:270`] `for (let attempt = 0; attempt <= retries; attempt++) {`  
[VERIFIED: `lib/gemini.ts:574`] `budget ? budget.attempts - 1 : undefined,`  
[VERIFIED: `lib/serve-budget.ts:89`] `export const SERVE_ATTEMPTS = 2 as AttemptCount;`  
Brand: yes. Passed: yes, as retries = attempts - 1. What breaks: `tsc` for widened/arithmetic local/object changes; `tests/lib/gemini-serve-budget.test.ts` call count.

5. Retry backoff base and total  
[VERIFIED: `lib/gemini.ts:281`] `if (baseDelayMs > 0) await abortableSleep(baseDelayMs * 2 ** attempt, opts?.signal);`  
[VERIFIED: `lib/gemini.ts:578`] `budget ? budget.backoffMs : undefined,`  
[VERIFIED: `lib/serve-budget.ts:104`] `export const SERVE_BACKOFF_BASE_MS = 400 as BackoffBudget;`  
[VERIFIED: `lib/serve-budget.ts:114`] `export const SERVE_BACKOFF_TOTAL_MS = Array.from(`  
Brand: base yes; total derived plain number. Passed: yes. What breaks: execution test observes actual `setTimeout` delay; total derivation test scales correctly for `SERVE_ATTEMPTS = 3`, and shipped-lease test would fail because 3 attempts no longer fit 180s.

6. Model put timeout  
[VERIFIED: `lib/html-doc/serve-doc.ts:141`] `await writeModelEnvelopeWithin(SERVE_PUT_TIMEOUT_MS, principal, base, {`  
[VERIFIED: `lib/html-doc/model-store.ts:67`] `timeoutMs: PutBudget,`  
[VERIFIED: `lib/serve-budget.ts:120`] `export const SERVE_PUT_TIMEOUT_MS = 15_000 as PutBudget;`  
Brand: yes. Passed: yes. What breaks: `tsc` for literal/arithmetic/wrong brand; import guard pins call population.

7. Settle RPC timeout  
[VERIFIED: `lib/html-doc/serve-doc.ts:254`] `const out = await callRpcBounded<boolean | null>(`  
[VERIFIED: `lib/html-doc/serve-doc.ts:258`] `SERVE_SETTLE_RPC_TIMEOUT_MS, \`settle_serve_model(released=${released})\`,`  
[VERIFIED: `lib/serve-budget.ts:123`] `export const SERVE_SETTLE_RPC_TIMEOUT_MS = 5_000 as SettleRpcBudget;`  
Brand: yes. Passed: yes. What breaks: literals/arithmetic fail `tsc`; reserve/settle swap covered by import guard.

8. Settle attempt count  
[VERIFIED: `lib/html-doc/serve-doc.ts:244`] `const attempts: AttemptCount | 1 = released ? SERVE_SETTLE_ATTEMPTS : 1;`  
[VERIFIED: `lib/html-doc/serve-doc.ts:250`] `for (let i = 0; i < attempts; i++) {`  
[VERIFIED: `lib/serve-budget.ts:148`] `export const SERVE_SETTLE_ATTEMPTS = 2 as AttemptCount;`  
Brand: yes. Passed: local typed consumer, not function argument. What breaks: arithmetic/widening at that local fails `tsc`.

9. Margin  
[VERIFIED: `lib/serve-budget.ts:154`] `export const SERVE_MARGIN_MS = 20_000;`  
Brand: no, deliberately not spent/enforced. Passed: no. What breaks: floor tests and migration literal pin.

Verdict: CLOSED for values that can extend lease-held runtime.

**Round-5 Fixes: Genuinely Fixed, Or Reworded?**

Genuinely fixed.

`SERVE_SETTLE_ATTEMPTS` is branded and consumed by an explicitly typed local. `SERVE_BACKOFF_BASE_MS` is passed into `generateJson`; the execution test observes the actual slept delay. `SERVE_BACKOFF_TOTAL_MS` is derived from the base and attempt count. Migration 0025 now uses `text_pattern_ops`; catalog read confirms `note | text_pattern_ops`.

Migration lock note: regular `CREATE INDEX` can run in a transaction, while `CREATE INDEX CONCURRENTLY` cannot, per PostgreSQL docs: https://www.postgresql.org/docs/current/sql-createindex.html. The current normal index build can block writes during build, but the local table is 60 rows / 8KB, so I would not block this PR on splitting a concurrent index migration.

**Verification**

Ran:

`npx tsc --noEmit`  
`npm test -- --runTestsByPath tests/lib/gemini-serve-budget.test.ts tests/lib/serve-budget.test.ts tests/lib/html-doc/serve-bounded-import-guard.test.ts`  
`npm test` → 263 suites, 2658 tests passed  
Read-only `docker exec ... psql` catalog checks for `ledger_audit` size/opclass/plan.

I did not run integration tests because this repo’s integration global setup runs `supabase migration up`, and the prompt warned the stack is shared.

**SHIP Verdict**

Ready to open as a PR. No round-6 blocker found.

CONVERGED
