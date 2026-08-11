<!-- codex-review: model=gpt-5.5 -->

**High**

Population gate can still be satisfied without increasing the enforced floor. `tests/lib/serve-budget-population.test.ts:100` says `EVERY branded budget is spent`, but the assertion at `tests/lib/serve-budget-population.test.ts:102` is only:

`const unaccounted = brandedExports(code).filter((name) => !spending.includes(name));`

`spendingExpressions` returns raw RHS text from `SERVE_BOUNDED_MS` and `SERVE_BACKOFF_TOTAL_MS` at `tests/lib/serve-budget-population.test.ts:55-61`, so any occurrence counts. I tested a mutant adding:

`export const SERVE_EXTRA_TIMEOUT_MS = 30_000 as ExtraBudget;`

and “accounting” it as:

`+ SERVE_EXTRA_TIMEOUT_MS * 0`

Result: `tests/lib/serve-budget-population.test.ts` passed, and `tests/lib/serve-budget.test.ts` also passed. The floor did not increase, but the gate accepted the brand.

Caller reaches it: `resolveMagazineModel` holds the paid lease after `reserve_serve_model` and before settle; e.g. generation starts at `lib/html-doc/serve-doc.ts:135` with `const model = await generateMagazineModelForServe(`, then upload at `lib/html-doc/serve-doc.ts:141` with `await writeModelEnvelopeWithin(SERVE_PUT_TIMEOUT_MS, principal, base, {`. A new bounded operation inserted there can spend extra lease time while the floor still permits the old 161s.

Fix: make this an AST/shape gate, not `includes`. Assert the exact positive budget expression shape: additive terms only, no zero coefficients, no string/comment matches, and known multiplicative pairs only. Also assert the backoff RHS structurally derives from `SERVE_ATTEMPTS` and `SERVE_BACKOFF_BASE_MS`.

**High**

The population gate only scans `lib/serve-budget.ts`, but the generic brand type is exported at `lib/serve-budget.ts:79`:

`export type Budget<Site extends string> = number & { readonly [budgetBrand]: Site };`

I tested a mutant adding `lib/extra-serve-budget.ts` with:

`export type ExtraBudget = Budget<'extra'>;`
`export const SERVE_EXTRA_TIMEOUT_MS = 30_000 as ExtraBudget;`

then importing and spending it from `resolveMagazineModel`. Result: `npm test -- tests/lib/serve-budget-population.test.ts --runInBand` passed and `npx tsc --noEmit` passed. The new branded lease-spent value never entered the scanned population.

Caller reaches it: same reserved path in `resolveMagazineModel`; the mutant spent the extra wait after `generateMagazineModelForServe` and before `writeModelEnvelopeWithin`.

Fix: either stop exporting generic `Budget`, or add a repo-wide gate forbidding `Budget<...>` aliases / `as *Budget` minting outside `lib/serve-budget.ts` and explicit test-support files. The population cannot be “closed” if new budget modules can exist.

**Medium**

`UNBRANDED_BY_DESIGN` can waive a plain exported value by documentation only. The map at `tests/lib/serve-budget-population.test.ts:83-90` is trusted by the unexplained-export filter at `tests/lib/serve-budget-population.test.ts:120-125`. I tested a mutant adding:

`export const SERVE_EXTRA_TIMEOUT_MS = 30_000;`

plus a map entry. Result: population gate passed. If a future helper accepts `number`, the old import guard will not catch it unless that helper is in its known table.

Fix: require unbranded entries to match an allowlist of exact current names, or add a negative repo-wide scan proving unbranded `SERVE_*` exports are not imported into `lib/html-doc/serve-doc.ts` / lease-held code.

**Can The Population Gate Be Evaded?**

Tried:

- Comment-only mention in RHS: failed correctly. `codeOnly` stripped `// + SERVE_EXTRA_TIMEOUT_MS`.
- Branded value in RHS multiplied by zero: passed incorrectly.
- Plain value plus `UNBRANDED_BY_DESIGN` entry: passed incorrectly.
- Branded value declared in a different file via exported `Budget<'extra'>`: passed incorrectly with `tsc`.
- Generation count passed to settle site: failed correctly with `TS2322`; distinct count brands work.
- Test minter reachability: `rg` found `serveBudgetWith` only under `tests/`, not `lib/`.

**Round-6 Fixes: Genuinely Fixed, Or Reworded?**

Distinct count brands: genuinely fixed. `GenerationAttemptCount` and `SettleAttemptCount` are separate at `lib/serve-budget.ts:93-94`; `ServeBudget.attempts` uses generation count at `lib/serve-budget.ts:207`; settle local is typed as `SettleAttemptCount | 1` at `lib/html-doc/serve-doc.ts:244`.

`serveBudgetWith`: genuinely improves observability. The backoff test uses `137` at `tests/lib/gemini-serve-budget.test.ts:94-100`, so default-vs-pass-through is observable.

Population gate: improved from the vacuous line-range version, but still not an enforcement of “genuinely spent.”

**Verification**

Ran on restored clean HEAD:

`npx tsc --noEmit` passed.  
`npm test` passed: 264 suites, 2662 tests.  
No Supabase reset/push commands run. `git status --short` clean.

**SHIP Verdict**

Not ready to open as PR. The enforcement gate still admits the exact class it is meant to prevent: a lease-spent value whose correctness nothing maintains. Remaining work: replace textual occurrence checks with structural budget-expression validation, and close the repo-wide minting escape hatch.

NOT CONVERGED
