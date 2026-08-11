# Whole-branch adversarial review — #46 serve-path bounding — ROUND 7 (Claude, isolated worktree)

Worktree at branch head `d6fc3d1`. Baseline measured this round, at clean HEAD:

- `npx tsc --noEmit` → exit 0
- `npx jest` → **264 suites / 2662 tests passed**
- `npm run test:integration -- serve` → **8 suites / 58 tests passed**
- `git status --short` → clean before and after every mutation below

Scope per the brief: attack the ENFORCEMENT that round 6 added, not the enumeration. I did not
re-derive the population; I accepted rounds 5 and 6's finding that there is no instance N+4 and
spent the round trying to add one.

**I added one, five different ways, with every gate green.**

---

## H-R7-1 (High) — the population gate accepts a MENTION of a budget, not a SPEND of it

**Claim.** `tests/lib/serve-budget-population.test.ts` is a substring test over the text of one
file. Three of its four rules can be satisfied by a value that is never added to the sum, and two of
them can be satisfied by a value the scan never sees at all. The gate catches the naive mutant it
was written against (round 6's M5) and nothing else in the same class.

**The rule, quoted at HEAD** [VERIFIED: `tests/lib/serve-budget-population.test.ts:100-106`]:

```ts
  it('EVERY branded budget is spent in the arithmetic that produces the floor', () => {
    const spending = spendingExpressions(code);
    const unaccounted = brandedExports(code).filter((name) => !spending.includes(name));
    expect(unaccounted).toEqual([]);
```

`spending` is the raw text of the two right-hand sides; `includes` is `String.prototype.includes`.
"Spent in the arithmetic" is therefore implemented as "this identifier occurs somewhere in that
text". The population it scans is `brandedExports(code)` [VERIFIED:
`tests/lib/serve-budget-population.test.ts:72-76`]:

```ts
  return [...code.matchAll(/export\s+const\s+([A-Z0-9_]+)\s*=\s*[^;]*?\bas\s+(\w*(?:Budget|AttemptCount))\s*;/g)]
```

— one file, `SCREAMING_SNAKE` names only, brand names ending in `Budget` or `AttemptCount` only.

**What caller reaches it.** `resolveMagazineModel` (`lib/html-doc/serve-doc.ts:43`), the serve path,
between `reserve_serve_model` returning `reserved` and `settle_serve_model` — i.e. inside the paid
lease. Every mutant below adds 30s of enforced wait to that window against a floor
(`SERVE_FLOOR_SECONDS` = 161) that does not pay for it, which is the lease overrun that admits a
second paid producer. That is the same harm round 6's H-R6-1 measured.

### The five surviving evasions, each MEASURED this round

Each mutant is round 6's M5 shape — a new brand, a new bounded helper (`warmCacheWithin`, added to
`lib/serve-rpc.ts`), one call inside the lease in `serve-doc.ts` — differing only in how the
constant is written.

| # | The one thing changed | `tsc` | population gate | other gates |
|---|---|---|---|---|
| **E1** | `+ 0 * SERVE_FETCH_TIMEOUT_MS` appended to `SERVE_BOUNDED_MS` | 0 | **PASS** | **264 suites / 2662 tests PASS** |
| **E2** | constant named `SERVE_ATTEMPT_TIMEOUT` — a substring of `SERVE_ATTEMPT_TIMEOUT_MS`, which is already in the sum. **The sum is not edited at all** | 0 | **PASS** | serve-budget + population suites PASS |
| **E3** | same constant named `serveFetchTimeoutMs` (camelCase) — not in the sum, not in `UNBRANDED_BY_DESIGN` | 0 | **PASS** | import guard + serve-budget suites PASS |
| **E4** | brand + constant declared in a new file `lib/serve-budget-extra.ts` | 0 | **PASS** | import guard + serve-budget suites PASS |
| **E5** | plain unbranded `SERVE_FETCH_TIMEOUT_MS = 30_000`, one line added to `UNBRANDED_BY_DESIGN` with a false reason, helper takes `number` | 0 | **PASS** | import guard + serve-budget suites PASS |

E1 was run against the **entire** unit suite and `tsc`: `TSC=0`, `264 passed, 264 total` /
`2662 passed, 2662 total` — byte-identical to the clean-HEAD baseline. The other four were run
against `tests/lib/serve-budget-population.test.ts`, `tests/lib/serve-budget.test.ts` and
`tests/lib/html-doc/serve-bounded-import-guard.test.ts` (22 tests, all green).

Why each survives, mechanically:

- **E1** — `includes('SERVE_FETCH_TIMEOUT_MS')` is true; the *value* contributed is zero, so
  `SERVE_BOUNDED_MS` is unchanged and `serve-budget.test.ts:15` ("exactly the sum of the enforced
  terms", which re-types the sum) still passes, as does the migration-0024 literal pin. Any
  discarding expression works: `Math.max(0, 0 * X)`, `X - X`, `(false ? X : 0)`.
- **E2** — needs *no* sum edit. `spending.includes('SERVE_ATTEMPT_TIMEOUT')` is true because the sum
  contains `SERVE_ATTEMPT_TIMEOUT_MS`. Any new name that is a prefix of an existing summed name is
  accounted for free, and this family of names is exactly the family a maintainer would pick.
- **E3** — `[A-Z0-9_]+` appears in *both* regexes, so a camelCase export is invisible to the branded
  scan **and** to the unbranded-export scan. The naming convention it depends on is enforced nowhere:
  the repo has no ESLint config (no `.eslintrc*`, no `eslint.config*`, no `lint` script), and CI runs
  `tsc`, `npm test`, `check:confinement`, `check-docs.py`, `check-arch-findings.py`
  [VERIFIED: `.github/workflows/ci.yml:44-80`]. The same hole swallows `const X = … ; export { X };`.
- **E4** — `SERVE_BUDGET_SRC` is `lib/serve-budget.ts` and nothing else
  [VERIFIED: `tests/lib/serve-budget-population.test.ts:28`]. `serve-budget.ts`'s own comment says
  "`lib/serve-budget.ts` is the only place production can obtain a brand" — that is a convention, and
  the gate assumes it rather than checking it.
- **E5** — the map is the documented escape hatch, but nothing tests that a reason is true, and the
  map lives in the same commit as the constant it excuses. A brand is optional: any *new* bounded
  helper can take a plain `number`, and only `serve-doc.ts` is checked for literals.

### What the gate DOES catch (it is not vacuous)

Measured, each failing the expected assertion:

| mutant | result |
|---|---|
| uppercase branded export, not in the sum (round 6's M5) | RED — *"EVERY branded budget is spent in the arithmetic…"* |
| brand type named `FetchTimeout` (not `…Budget`/`…AttemptCount`) | RED — *"every UNBRANDED export is unbranded ON PURPOSE…"* |
| new plain-number export, no map entry | RED — *"every UNBRANDED export is unbranded ON PURPOSE…"* |

So it is a real guard against the literal mutant it was built from, and against nothing one edit
away from it.

### Fix

Stop scanning text; make the sum the **only mint**. The arithmetic should *produce* the population
instead of being searched for it:

```ts
const SPENT: number[] = [];
function spend<S extends string>(ms: number, site: S): Budget<S> { SPENT.push(ms); return ms as Budget<S>; }
function spendEach<S extends string>(n: number, ms: number, site: S): Budget<S> { SPENT.push(n * ms); return ms as Budget<S>; }

export const SERVE_PUT_TIMEOUT_MS = spend(15_000, 'put');
…
export const SERVE_BOUNDED_MS = SPENT.reduce((a, b) => a + b, 0);
```

Minting a brand then *is* joining the sum — one mechanism, no regex, no naming convention, no
file-scoping assumption, and E1–E4 all become unrepresentable rather than undetected. `spend` stays
unexported, so the ordinary way to get a serve budget is the accounted way. Keep one small text
guard for what types cannot reach — that `SPENT` is non-empty and that `SERVE_BOUNDED_MS` is the
reduction — and drop the three rules that this round defeated.

**Residual, stated honestly:** a maintainer can still declare a private brand in a new file (E4) and
never touch `serve-budget.ts`. No type closes that. What *would* is a guard aimed at the right
population — every module transitively reachable from `serve-doc.ts` inside the lease, scanned for
`setTimeout` / `AbortSignal.timeout` / `abortSignal(` — i.e. scan for **bounded work**, not for
**exported names**. That is the population the branch actually cares about; the current gate scans a
proxy for it.

---

## M-R7-1 (Medium) — the division-of-labour comment overclaims again, in three places

Round 5 corrected this sentence, round 6 corrected it again (L-R6-1, "the fourth overclaimed
comment"), and round 6's replacement is false as written [VERIFIED: `lib/serve-budget.ts:69-72`]:

```
 *   THE POPULATION GATE  (tests/lib/serve-budget-population.test.ts) every branded budget is spent in
 *                      the sum, every ServeBudget field is an accounted scalar, and every unbranded
 *                      export is unbranded on purpose — so a TWELFTH bounded value cannot be added
 *                      without either joining the sum or declaring why it does not
```

E1–E4 each add a twelfth bounded value without joining the sum and without declaring anything. The
same claim appears at `tests/lib/html-doc/serve-bounded-import-guard.test.ts:36-39` and again at
`:51-55` ("which tests/lib/serve-budget-population.test.ts now closes by requiring every branded
budget to be spent in the sum"), and in `docs/reviews/…-adjudication-r6.md`.

This is standing shape #10 — a comment claiming a guarantee the code does not give — for the
**fifth** time on this branch, and the concrete harm is the one round 5 named: the next maintainer
reads it, believes the population is closed, and weakens something else. It must be corrected in all
three code locations when H-R7-1 is fixed, and worded against what is measured.

---

## M-R7-2 (Medium) — `serveBudgetWith` is a second mint of the `ServeBudget` brand, and nothing confines it to tests

`ServeBudget`'s value is that production cannot construct one: round-1 H1 was
`{ attempts: 3, attemptTimeoutMs: 60_000, … }` at the serve call site, and the fix was to make that
object literal unrepresentable. `tests/support/budget.ts:33` now exports a factory that produces one
from arbitrary numbers:

```ts
export const serveBudgetWith = (over: Partial<Record<keyof ServeBudget, number>>) =>
  Object.freeze({ ...SERVE_BUDGET, ...over }) as unknown as ServeBudget;
```

MEASURED (mutant G5): a new production module

```ts
// lib/serve-doc-alt.ts
import { serveBudgetWith } from '../tests/support/budget';
export async function altServe(sections, caps) {
  return generateMagazineModelForServe(sections, 'en',
    serveBudgetWith({ attempts: 3, attemptTimeoutMs: 60_000 }), { caps });
}
```

compiles with `tsc --noEmit` exit 0 and leaves the population gate, the import guard and
`serve-budget.test.ts` all green (22/22). That is round-1 H1 restored verbatim through a second
producer. `tsconfig.json` includes `**/*.ts`, so `tests/` is on the production module graph;
`check-service-confinement` is about `service_role`, not this; and the import guard reads
`lib/html-doc/serve-doc.ts` only.

Nothing under `lib/`, `app/`, `worker/` or `scripts/` imports from `tests/` today (grepped, zero
hits), so there is no live defect — the file's own docstring ("If you find yourself importing these
from `lib/`, something has gone wrong") is the only thing standing there, and it is prose.

**Severity.** Medium, not High: it needs a *new* caller, and `generateMagazineModelForServe` has
exactly one today. But this branch's whole thesis is "unrepresentable, not merely asserted", and the
round-6 fix widened the mint from one call site to an arbitrary factory. The three older helpers
(`putBudget`, `reserveRpcBudget`, `settleRpcBudget`) have the same exposure and predate this round —
one guard covers all four.

**Fix.** A five-line text guard: no file under `lib/`, `app/`, `worker/`, `scripts/` may contain an
import specifier resolving into `tests/`. It generalises past the serve path and costs nothing.

---

## L-R7-1 (Low) — the carrier test does not do what its name says; another test does

`tests/lib/serve-budget-population.test.ts:108-118` claims *"the CARRIER cannot smuggle a value
across the boundary"*, via `/:\s*([A-Z0-9_]+)\s*,/g` — which requires a **trailing comma** and an
uppercase value.

MEASURED (mutant D): adding `readonly fetchMs: number;` to the interface and `fetchMs: 30_000` as the
**last** property of the `SERVE_BUDGET` literal (no trailing comma) passes this test — the carrier
smuggles a 30s unaccounted value across into `lib/gemini.ts`. It is caught instead by
`serve-budget.test.ts:77` (`expect(SERVE_BUDGET).toEqual({…})`, whose exactness rejects the extra
key). So the coverage is real, but it lives in a test that does not claim it, and the test that does
claim it is decorative. Either delete this rule or state that the `toEqual` shape-pin is what holds
it.

## L-R7-2 (Low) — `codeOnly` diverges from its sibling and from its own docstring

`tests/lib/serve-budget-population.test.ts:31-33` strips comments only; the sibling guard's version
(`serve-bounded-import-guard.test.ts:61-68`) also strips template, single- and double-quoted strings
"so prose cannot satisfy or trip a rule". The population gate's docstring makes the same promise but
its implementation leaves string literals in the text that feeds `includes()`. I could not build an
exploit from this that E1 does not already give more cheaply, so: Low, and it is one line to align.

---

# 1. Can the population gate be evaded?

**Yes — five ways, all measured this round, all with `tsc` exit 0.**

| evasion | how | result |
|---|---|---|
| named inside the RHS but discarded (`+ 0 * X`) | E1 | **EVADED** — full suite 264/2662 green, identical to baseline |
| name is a substring of a summed name (`SERVE_ATTEMPT_TIMEOUT`) | E2 | **EVADED** — and the sum is never touched |
| camelCase export name | E3 | **EVADED** — invisible to both regexes |
| brand + constant in a second file | E4 | **EVADED** — the gate reads one path |
| `UNBRANDED_BY_DESIGN` entry with a false reason, helper takes `number` | E5 | **EVADED** — no test checks a reason |
| naive M5 (uppercase, branded, absent from the sum) | — | **CAUGHT** |
| brand type not ending `Budget`/`AttemptCount` | — | **CAUGHT** (by the unbranded rule) |
| new plain export, no map entry | — | **CAUGHT** |
| 5th carrier field, trailing comma, uppercase value | — | **CAUGHT** |
| 5th carrier field, no trailing comma | D | **EVADED by this gate**, caught by `serve-budget.test.ts` `toEqual` |

**The inverse defect the brief asks about — a budget summed but never PASSED to a call — the gate
does not detect, and does not need to.** Verified where that coverage actually lives:
`SERVE_RESERVE_RPC_TIMEOUT_MS` / `SERVE_PUT_TIMEOUT_MS` / `SERVE_SETTLE_RPC_TIMEOUT_MS` by the import
guard's `mustContain`; the four `ServeBudget` fields by `tests/lib/gemini-serve-budget.test.ts`;
`SERVE_SETTLE_ATTEMPTS` by `serve-doc-mapping.test.ts` — MEASURED by pinning the local to `1`, which
turns three tests red ("retries the settle ONCE…", and both INDETERMINATE cases).

# 2. Round-6 fixes: genuinely fixed, or reworded?

| fix | verdict |
|---|---|
| **1. `tests/lib/serve-budget-population.test.ts` — the population gate** | **NOT fixed — instance, not class.** It closes the exact mutant it was written from. Five one-edit variants walk through it (H-R7-1). The gate is real work and catches something; it does not deliver the guarantee its comments claim |
| **2. Distinct brands `GenerationAttemptCount` / `SettleAttemptCount`** | **GENUINELY FIXED.** Three mutants, three `tsc` errors: the generation count at the settle site → `TS2322: Type 'GenerationAttemptCount \| 1' is not assignable to type '1 \| SettleAttemptCount'`; the settle count carried as `SERVE_BUDGET.attempts` → `TS2352` at `serve-budget.ts:214`; `SERVE_SETTLE_ATTEMPTS + SERVE_SETTLE_ATTEMPTS` at the typed local → `TS2322: Type 'number'`. The `SettleAttemptCount \| 1` local is doing its job. A `countTokens`↔`attempt` swap is also a type error |
| **3. `serveBudgetWith` test minter** | **FIXED for what it was for, with a new exposure.** The backoff pass-through is now genuinely observable — `137` is a value no default produces, and reverting the pass-through is red where it was green. `Object.freeze({ ...SERVE_BUDGET, ...over })` preserves the runtime invariants (frozen, all four fields present; the phantom brand has no runtime existence so the spread loses nothing real), and no test asserts a pass-through production does not perform: `serve-doc.ts` still hands the frozen `SERVE_BUDGET`, pinned by the import guard. The exposure is M-R7-2 |

## The structural finding: the stop condition has fired

`docs/review-method.md:46` — *"If a component produces findings caused by the PREVIOUS round's fixes
in two consecutive rounds, it escalates from FIX to REDESIGN, and the next round is a design review
— not another defect hunt."*

Count it on this component (the serve-budget accounting instruments):

- **Round 6** produced M-R6-1 (the backoff assertion could not fail if reverted) and M-R6-2 (the two
  counts shared one brand) — both defects **in round 5's own fixes**.
- **Round 7** produces H-R7-1, M-R7-1 and M-R7-2 — all three **in round 6's own fixes**.

That is two consecutive rounds, and the rule says two, not three. The shape is also the one the
branch has already documented about itself: `lib/serve-budget.ts:33-44` records that rounds 1, 2 and
3 each built a detector defeated by the next expression, and concludes *"the signature of patching an
instrument instead of changing a shape"*. The population gate is the **fourth** text detector in that
lineage and I defeated it with five expressions in one round. The right next move is not a sixth
regex — it is the redesign in H-R7-1's fix (the sum as the mint), which removes the text scan rather
than sharpening it.

Note also that this is standing shape #3 — *a green gate testing the wrong thing* — for the **ninth**
time, exactly as the brief predicted, and again written by the coordinator while fixing shape #3.

# 3. SHIP verdict

**Not yet — but the remaining work is small and bounded, and nothing at HEAD is incorrect.**

To be explicit about what is and is not wrong: the eleven lease-spent values are enumerated
correctly, the sum is right, the floor is right, the migration literals agree with it, the brands
hold, `tsc` is clean, 2662 unit tests and 58 serve integration tests pass. **No user is charged twice
by anything on this branch today.** The defect is that the mechanism round 6 added to keep it that
way does not, and it is documented in three places as if it does.

Required before PR:

1. **H-R7-1** — replace the three text rules with the accounting mint (`spend()` feeding `SPENT`
   feeding `SERVE_BOUNDED_MS`), and re-run E1–E4 against it; each must be red or impossible to write.
2. **M-R7-1** — correct the division-of-labour claim in `lib/serve-budget.ts:69-72` and
   `serve-bounded-import-guard.test.ts:36-39, 51-55` to what the new mechanism actually gives.
3. **M-R7-2** — the `lib|app|worker|scripts` → `tests/` import guard.

L-R7-1 and L-R7-2 are one-line cleanups that can ride along or be dropped by decision.

Because the stop condition has fired, round 8 should be a **design review of the enforcement
mechanism** — "what already serves this concern, and which shape is this?" — not another defect hunt
over a fifth regex.

**What I threw at it that held:** the brand separation (three swaps, three type errors), the typed
settle local, the carrier's `toEqual` shape pin, the settle-retry count's observability, the
migration-0024 literal population pin, the `countTokens`/`attempt` brand distinction, the backoff
derivation, and the whole integration serve path. Rounds 1-5's fixes all survived this round intact.

---

**NOT CONVERGED**
