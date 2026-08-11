<!-- codex-review: model=gpt-5.5 -->

**Blocking**
None.

**High**
None.

**Medium**
None.

**Low**
Comment overclaims the type guarantee in the import guard. `tests/lib/html-doc/serve-bounded-import-guard.test.ts:19-22` says:

`// the call site it belongs to, so a literal, an arithmetic expression, an object literal and a`
`// swapped constant are all COMPILE errors — verified against all four mutants.`

That is false for the reserve/settle RPC swap. The actual code admits both RPC brands: `lib/serve-rpc.ts:31` has `timeoutMs: ReserveRpcBudget | SettleRpcBudget,` and `lib/serve-budget.ts:52-61` correctly documents that this swap still compiles and is guard-covered. Concrete failure scenario: a future maintainer trusts the stale test comment and weakens/removes the text guard, thinking TypeScript covers all swaps. What caller reaches it: no runtime caller; this is maintainer-facing test documentation. Fix: reword lines 19-22 to match `lib/serve-budget.ts`: types cover literals/arithmetic/object literals; the guard covers reserve/settle site swaps and population.

**Round-4 fixes: genuinely fixed, or reworded?**
Genuinely fixed for the live defect.

I threw assignment, spread replacement, `Number(3)`, and `Math.min(3, 3)` at `ServeBudget.attempts`; `tsc` rejected all. Runtime mutation is blocked by `Object.freeze` at `lib/serve-budget.ts:163-167`, and the shallow freeze is sufficient because the fields are primitive branded numbers, not nested mutable objects. `structuredClone(SERVE_BUDGET)` can copy the same values, but it does not create a wrong count without an explicit cast/`any`. `JSON.parse`, a second cast object, or `as ServeBudget` can still lie, but no type-only design closes deliberate `any`/assertion abuse; the production caller passes the singleton directly at `lib/html-doc/serve-doc.ts:134-138`.

The DB index fix holds. Live `EXPLAIN` showed the prefix lookup using `Index Cond` with `note ~>=~ token:` and `note ~<~ token;`, and equality lookup on `note` also remained an `Index Cond`. Source matches that intent at `supabase/migrations/0025_settle_is_observable.sql:56-57`.

Validation run:
`npx tsc --noEmit` passed.
`npm test` passed: 263 suites, 2657 tests.
`npm run test:integration -- serve settle html-download pdf-cloud` passed: 11 suites, 82 tests.
`git status --short` was clean.

**SHIP Verdict**
Ready to open as a PR. The only remaining issue I found is a Low stale comment in the guard test, not a blocking serve-path bounding failure.

CONVERGED
