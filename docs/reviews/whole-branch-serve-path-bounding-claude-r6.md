# Whole-branch adversarial review — #46 serve-path bounding, ROUND 6 (Claude)

Worktree at branch head `9825758`. Base `master` = `1a7c076`.

## Gates run

| Gate | Result |
|---|---|
| `npx tsc --noEmit` | exit 0 |
| `npm test` | 263 suites, **2658 passed**, 0 failed |
| `npm run test:integration -- serve settle html-download pdf-cloud share-route` | 12 suites, **105 passed** |
| `git status --short` | empty, after every mutation restored |

Six mutants applied and reverted (M2, M3, M4a/b/c, M5, M6). Every one is recorded below with its
verdict, including the three that went **red as they should**.

---

# Findings

## HIGH — H-R6-1. The population of lease-spent bounds is not pinned. A twelfth bounded call can be added inside the paid lease, spending 30s the floor does not cover, with `tsc`, 2658 unit tests and 105 integration tests all green

**Claim.** The guard's own comment says the class assertion it makes — the thing that distinguishes
it from "four instance assertions" — is that the population of bounded call sites is pinned. Round 5
certified that claim in its *held* list. It is false. The guard pins the number of calls **to the
three functions it already knows about**; it has no rule saying those are the only bounded calls in
the file, and nothing anywhere relates the population of branded budgets to the terms of
`SERVE_BOUNDED_MS`.

**Premises.**

- `[VERIFIED: tests/lib/html-doc/serve-bounded-import-guard.test.ts:47-49]` — the claim under test:
  ```
  //   3. The POPULATION of bounded call sites is pinned. Adding a fifth bounded call without
  //      extending this table fails here, which is the difference between a class assertion and four
  //      instance assertions. Round 2's lesson was that round 1 wrote the latter.
  ```
- `[VERIFIED: tests/lib/html-doc/serve-bounded-import-guard.test.ts:135-144]` — what it actually
  asserts. `callArgs(code, fn)` is called **once per row of `BOUNDED_CALLS`**; a function not in
  that table is never searched for:
  ```ts
  it.each(BOUNDED_CALLS)('$fn is handed its own budget constant, at every call site', ({ fn, calls, mustContain }) => {
    const args = callArgs(code, fn);
    expect({ fn, sites: args.length }).toEqual({ fn, sites: calls });
  ```
- `[VERIFIED: docs/reviews/whole-branch-serve-path-bounding-claude-r5.md:347-348]` — round 5's
  certification of the claim: *"**The population check works.** `[VERIFIED: …import-guard.test.ts:128]`
  asserts `sites === calls` before checking any constant, so a fifth bounded call cannot be added
  silently."*
- `[VERIFIED: lib/serve-budget.ts:157-163]` — the sum is a hand-written expression over seven named
  terms. Nothing enumerates the file's `Budget<…>` exports and checks each appears in it.

**MEASURED — mutant M5.** The realistic future slice: *verify the write landed before settling*. Three
edits, all of them the shape a careful maintainer would write —

1. `lib/serve-budget.ts` — a new brand and a new constant, **not** added to `SERVE_BOUNDED_MS`:
   ```ts
   export type VerifyBudget = Budget<'verify'>;
   export const SERVE_VERIFY_TIMEOUT_MS = 30_000 as VerifyBudget;
   ```
2. `lib/html-doc/model-store.ts` — `verifyModelEnvelopeWithin(timeoutMs: VerifyBudget, …)`, a
   `Promise.race` mirroring `writeModelEnvelopeWithin` exactly, timer cleared in `finally`.
3. `lib/html-doc/serve-doc.ts` — one line inside the lease, between the put and the keep-settle:
   ```ts
   await verifyModelEnvelopeWithin(SERVE_VERIFY_TIMEOUT_MS, principal, base, blobStore);
   ```

Result: `npx tsc --noEmit` → **exit 0**. `npm test` → **263 suites, 2658 passed, 0 failed.**

Why every instrument misses it, one by one:

- **the brands** — the new call takes its own brand, correctly. Branding constrains *which* value may
  be spent at a site; it says nothing about whether a site exists;
- **the no-literals rule** `[VERIFIED: …import-guard.test.ts:123-133]` — `SERVE_VERIFY_TIMEOUT_MS` is
  an identifier, not a literal;
- **`BANNED`** `[VERIFIED: …import-guard.test.ts:93-104]` — lists the unbounded twin of each *known*
  bounded call. `verifyModelEnvelopeWithin` has no twin in the list;
- **`BOUNDED_CALLS`** — as quoted above, a table-driven `it.each`. A function absent from the table is
  never looked for;
- **`tests/lib/serve-budget.test.ts:15-24`** — asserts `SERVE_BOUNDED_MS` equals the sum of the same
  terms it was built from. A term that was never added is invisible to it;
- **`tests/lib/serve-budget.test.ts:101-120`** — pins migration 0024's literals to
  `SERVE_FLOOR_SECONDS`, which under the mutant is *still 161*, because the sum did not move.

**The money consequence, arithmetically.** Enforced work becomes 140.4s + 30s = **170.4s**;
`SERVE_FLOOR_SECONDS` stays **161**; migration 0024's CHECK permits `lease_ttl_seconds` to be exactly
161 `[VERIFIED: supabase/migrations/0024_lease_covers_serve.sql:78]`, and 0024's own fix-up *writes*
161 into any row below it `[VERIFIED: …:73-75]`. So on a database this branch itself repaired, the
enforced work provably exceeds the lease, the reclaim clause in `reserve_serve_model` admits a second
paid producer, and the branch's headline claim is false — with every gate green. That is the identical
end-state as round-4 H1 and round-5 H-R5-1.

**What caller reaches it.** `resolveMagazineModel` `[VERIFIED: lib/html-doc/serve-doc.ts:141-153]`,
reached from `serve-summary-core.ts:105`, on every cache-miss serve of a paid magazine doc.

**Why this is the round's finding rather than a seventh instance.** Rounds 4, 5 and the coordinator
sweep each found one more *value* nobody tied to the sum, and each was fixed by tying that value.
Every one of those fixes is real and holds (see the fix verdicts below). None of them installed the
thing that makes the *next* one impossible. M5 is not a value that was missed — it is the demonstration
that the set is closed today only by inspection, and stays closed only by whoever writes the next
bounded call remembering to add a term. `docs/review-method.md`'s escalation rule is on exactly this
pattern: three instances of one shape, three instance fixes.

**Fix.** One class assertion, in `tests/lib/serve-budget.ts`'s test, that closes it by construction:
parse `lib/serve-budget.ts` and require that **every exported constant whose type is a `Budget<…>`
brand appears as a term in the `SERVE_BOUNDED_MS` expression**. That is a population check over the
*population that matters* — the branded values — rather than over a hand-maintained list of function
names. It fails M5 at the moment `SERVE_VERIFY_TIMEOUT_MS` is declared, before the call site is even
written. A second, cheaper half: change `BOUNDED_CALLS`'s population assertion from "each listed `fn`
appears `calls` times" to "every `await`ed call in `serve-doc.ts` that receives a `lib/serve-budget`
identifier is a listed `fn`".

**Counter-argument, stated so it can be adjudicated down.** M5 requires *writing new code*, whereas
r4-H1 and r5-H-R5-1 were one-token edits to existing code — and no invariant survives arbitrary new
code. If the coordinator judges that distinction load-bearing, this is a **Medium**. I rate it High
because the branch explicitly claims to cover it, in a comment whose whole purpose is to tell the next
maintainer what they may rely on, and because round 5 relied on it.

---

## MEDIUM — M-R6-1. Round 5's backoff fix is real, and no test on this branch can fail if it is reverted — because the budgeted value and the inherited default are both 400

**Claim.** The round-5 coordinator sweep found the backoff by mutating `generateJson`'s
`baseDelayMs = 400` default. The fix passes the value instead of inheriting it, which is correct. But
`SERVE_BACKOFF_BASE_MS` is **also 400**, so passing it and not passing it are observationally
identical, and the test written to defend the fix cannot distinguish them.

**Premises.**

- `[VERIFIED: lib/serve-budget.ts:104]` `export const SERVE_BACKOFF_BASE_MS = 400 as BackoffBudget;`
- `[VERIFIED: lib/gemini.ts:263]` `baseDelayMs = 400,` — the inherited default, unchanged.
- `[VERIFIED: tests/lib/gemini-serve-budget.test.ts:78-95]` — the defending test, and its stated
  purpose:
  ```ts
  // The backoff is the term the serve path used to leave to generateJson's default — budgeted in
  // one place, slept in another, with nothing relating them. Assert it now travels WITH the budget.
  …
  expect(delays).toEqual([SERVE_BUDGET.backoffMs]);
  ```
  `SERVE_BUDGET.backoffMs` is 400 and the default is 400, so the assertion holds either way.
- `[VERIFIED: tests/support/budget.ts:15-17]` — the test helpers mint `PutBudget`,
  `ReserveRpcBudget`, `SettleRpcBudget`. There is **no** `ServeBudget` minter, so no test can call
  `generateMagazineModelForServe` with a `backoffMs` that differs from the production constant.

**MEASURED — mutant M3.** One edit at `lib/gemini.ts:578`, reverting the round-5 fix:

```ts
-      budget ? budget.backoffMs : undefined,
+      undefined,   // MUTANT M3
```

Result: `npx tsc --noEmit` → **exit 0**. `npm test` → **263 suites, 2658 passed, 0 failed.**
`tests/lib/gemini-serve-budget.test.ts` alone: **5 passed.**

**Contrast — the other three fields of `ServeBudget` are genuinely defended.** Same mutation shape,
applied to each (mutants M4a/b/c), running only `gemini-serve-budget.test.ts`:

| field | budgeted | inherited default | mutant verdict |
|---|---|---|---|
| `attempts` | 2 | `GENERATE_JSON_RETRIES + 1` = 3 | **2 failed / 3 passed — RED ✓** |
| `attemptTimeoutMs` | 50_000 | `REQUEST_TIMEOUT_MS` = 60_000 | **1 failed / 4 passed — RED ✓** |
| `countTokensTimeoutMs` | 10_000 | key omitted entirely | **1 failed / 4 passed — RED ✓** |
| `backoffMs` | 400 | **400** | **5 passed — GREEN ✗** |

The pattern is exact: the three whose budgeted value differs from the default are caught; the one
whose value coincides is not. This is a fixture-masked mutation — the standing shape *"a green gate
testing the wrong thing"*, and the *"negative test passing for the wrong reason"* one.

**Concrete failure scenario.** A refactor of `generateMagazineModel`'s six-positional-argument call
drops or reorders the `backoffMs` argument. Today that is invisible on every gate. It stays invisible
right up until someone retunes either number — at which point the serve path spends one number while
the sum budgets another, which is the exact defect the round-5 sweep found and this fix was written to
close by construction. The construction *is* right; what is missing is anything that would notice it
being undone.

**What caller reaches it.** No runtime caller today — the values agree, so behaviour is correct. This
is a defect in the instrument, not in the shipped path.

**Fix.** Add `serveBudget(overrides)` to `tests/support/budget.ts` and assert the pass-through with a
value that is *not* 400 — e.g. `serveBudget({ backoffMs: 137 })` → `expect(delays).toEqual([137])`.
That kills M3 regardless of what the production constants happen to be, and it is the same technique
that makes the other three rows of the table red.

---

## MEDIUM — M-R6-2. The two attempt COUNTS share one brand, so the generation count can be spent as the settle count — and unlike the RPC-budget swap this one has no guard behind it

**Claim.** Round 5's fix branded `SERVE_SETTLE_ATTEMPTS` and typed its consuming local, which closes
*arithmetic* (mutant MA is now a compile error). It does not close a *swap*: `SERVE_ATTEMPTS` and
`SERVE_SETTLE_ATTEMPTS` are both `AttemptCount`, i.e. both `Budget<'attempts'>`, so each satisfies the
other's type exactly.

This is structurally the deferred **r4 L-R4-1** (the two RPC budgets share `ReserveRpcBudget |
SettleRpcBudget`). I am not re-reporting that decision — I am reporting that **its justification does
not carry over.** L-R4-1 was accepted because *"The text guard … is what covers that case — it asserts
each constant appears at exactly one site"* `[VERIFIED: lib/serve-budget.ts:54-58]`. For the counts,
no guard covers it.

**Premises.**

- `[VERIFIED: lib/serve-budget.ts:77]` `export type AttemptCount = Budget<'attempts'>;` — one brand.
- `[VERIFIED: lib/serve-budget.ts:89]` `export const SERVE_ATTEMPTS = 2 as AttemptCount;`
- `[VERIFIED: lib/serve-budget.ts:148]` `export const SERVE_SETTLE_ATTEMPTS = 2 as AttemptCount;`
- `[VERIFIED: lib/html-doc/serve-doc.ts:244]`
  `const attempts: AttemptCount | 1 = released ? SERVE_SETTLE_ATTEMPTS : 1;`
- `[VERIFIED: tests/lib/html-doc/serve-bounded-import-guard.test.ts:84-90]` — `BOUNDED_CALLS` has
  three rows, none of them `settleBounded`; the counts are not in the table at all.

**MEASURED — mutant M2.** Import `SERVE_ATTEMPTS` into `serve-doc.ts` and swap it in:

```ts
const attempts: AttemptCount | 1 = released ? SERVE_ATTEMPTS : 1;   // MUTANT M2
```

Result: `npx tsc --noEmit` → **exit 0**. `npm test` → **263 suites, 2658 passed, 0 failed.**

**Live consequence today: none** — both constants are 2. **Latent consequence:** `SERVE_ATTEMPTS` was
3 before this branch and is a plausible retune target (its own doc comment discusses the value). At 3,
the settle loop spends 3 × 5s = 15s while `SERVE_BOUNDED_MS` pays `SERVE_SETTLE_ATTEMPTS × 5s` = 10s —
5s of unbudgeted spend inside the lease, on the refund path, with the floor under-stated.

**What caller reaches it.** `settleBounded` on the refund path, `serve-doc.ts:175` — a failed paid
generation, which is the path where money is actually at stake.

**Fix (cheap).** Give the two counts distinct brands — `type GenerationAttemptCount =
Budget<'generationAttempts'>` and `type SettleAttemptCount = Budget<'settleAttempts'>`. That makes M2
a compile error and costs two type aliases; it is strictly less machinery than the two per-site
wrappers that were (reasonably) declined for L-R4-1, because there is no shared consumer here forcing
a union. Alternatively, add a `settleBounded` row to `BOUNDED_CALLS` — but a type is better, and this
is the one place where the brand system's "one brand per call site" rule was not followed.

---

## LOW — L-R6-1. The fourth overclaimed comment, and it is the one round 5 asked to have corrected. The same false sentence now stands falsified in two independent ways

**Claim.** Round 5 recommended three things for H-R5-1: brand the constant, annotate the local, and
*"correct the division-of-labour sentence at `lib/serve-budget.ts:60-61`"*
`[VERIFIED: docs/reviews/whole-branch-serve-path-bounding-claude-r5.md:377-378]`. The first two were
done. The third was not — `git diff 773fc9e..HEAD -- lib/serve-budget.ts` contains no change to that
sentence.

**Premises.**

- `[VERIFIED: lib/serve-budget.ts:59-61]`, unchanged at HEAD:
  ```
   * labour is: TYPES cover literals, arithmetic and object literals; the GUARD covers site-swaps,
   * counts and population.
  ```
- `[VERIFIED: tests/lib/html-doc/serve-bounded-import-guard.test.ts:32-35]` — the same claim, in the
  guard's own file:
  ```
  //   THIS GUARD    a swap between the TWO RPC budgets … · the POPULATION of bounded
  //                 call sites · counts, which the brand cannot reach at a call site
  ```
- **"the GUARD covers … population"** — falsified by mutant M5 (H-R6-1). It covers the population of
  call sites *for three named functions*.
- **"the GUARD covers … counts"** — falsified by mutant M2 (M-R6-2). It covers *literal* counts, via
  the no-literals rule. It does not cover a swapped branded count; `settleBounded` is not in the table.
- **"the GUARD covers site-swaps"** — this third clause is **true**, and round 5 measured it (mutant
  MB turns the guard red on `seen: 1`). The sentence is not wholly wrong, which is precisely why it
  keeps surviving review.

**Concrete failure scenario.** The stated harm is unchanged from rounds 4 and 5 and has now been
realised once: a reviewer reads the sentence, believes the population is pinned, and writes it into
the *held* list of a review (round 5, line 347). A maintainer who trusts it adds a bounded call and
never learns the floor no longer covers it.

**Fix.** Both files, one edit each. State what is actually true:
*TYPES cover literals, arithmetic, object literals, and swaps between budgets with different brands.
THE GUARD covers the reserve/settle RPC swap, literal durations and counts, and the number of calls to
the functions it lists. **NOTHING covers the population of bounded calls or the two attempt counts'
shared brand** — see H-R6-1 and M-R6-2.* And if H-R6-1's population assertion is built, rewrite the
sentence around it rather than deleting the caveat.

---

## LOW — L-R6-2. `create index` (non-concurrent) on `ledger_audit` now blocks the money path it was added to observe

**Claim.** 0025 does two things to `ledger_audit`: it makes every settled serve INSERT a row, and it
rebuilds an index with `drop index … ; create index …`. A plain `CREATE INDEX` takes a `SHARE` lock,
which blocks INSERT for the duration of the build. A `settle_serve_model` blocked longer than
`SERVE_SETTLE_RPC_TIMEOUT_MS` returns `indeterminate` — and on the refund path that is the money
alarm at `serve-doc.ts:195-200`. The migration can manufacture the exact state its own witness exists
to resolve.

**Premises.**

- `[VERIFIED: supabase/migrations/0025_settle_is_observable.sql:61-63]`
  ```sql
  drop index if exists ledger_audit_kind_note_idx;
  create index ledger_audit_kind_note_idx
    on ledger_audit (kind, note text_pattern_ops);
  ```
- `[VERIFIED: supabase/migrations/0025_settle_is_observable.sql:~85]` — the added INSERT runs on every
  successful settle, past the `not found` gate.
- `[VERIFIED: lib/serve-budget.ts:123]` `SERVE_SETTLE_RPC_TIMEOUT_MS = 5_000`.

**Assessment — this is Low, and the migration is right as written.**

- `ledger_audit` is exception-only today; `[VERIFIED: live stack]` it carries two indexes and, before
  this migration, effectively no routine traffic. An index build on a table this size is sub-second,
  so the blocking window is far under 5s.
- `create index concurrently` **cannot** be used here: it may not run inside a transaction block, and
  migrations are applied by `supabase migration up`
  `[VERIFIED: tests/integration/global-setup.ts:46]`, which runs each file transactionally
  `[ASSUMPTION — not verified by execution]`. Even if it could, it would need its own migration file.
- The round-5 reasoning for drop-then-create over `if not exists` is **correct and I re-verified the
  premise it rests on**, independently, on a 20 001-row temp table on the live stack (no repo table
  touched, nothing persisted):

  ```
  -- with (kind, note)                   → Seq Scan on la
  --                                       Filter: ((note ~~ '…:%') AND (kind = 'serve_settle'))
  -- with (kind, note text_pattern_ops)  → Index Scan using la_pattern
  --                                       Index Cond: ((kind = 'serve_settle')
  --                                                AND (note ~>=~ '…:') AND (note ~<~ '…;'))
  ```
  `text_pattern_ops` is load-bearing exactly as claimed. (One imprecision, not worth a finding: the
  comment says the default opclass makes the planner *"use the index for `kind` only and apply the
  prefix as a FILTER"*; I measured a full Seq Scan. Same conclusion, different plan.)

**Fix.** No code change. A one-line deploy note in the migration header: *run when the table is
small, or accept a brief settle-blocking window; the alternative (`CONCURRENTLY`) needs its own
non-transactional migration.* Worth writing down because the table is now designed to grow forever.

---

# 1. The population of lease-spent values

Enumerated by walking every reachable call between `case 'reserved': break;`
`[VERIFIED: lib/html-doc/serve-doc.ts:120]` and the settle, into `lib/gemini.ts`, `lib/serve-rpc.ts`
and `lib/html-doc/model-store.ts`. Defaults inherited from called functions and loop bounds are
included.

**The four awaits inside the lease, exhaustively** — everything else in `serve-doc.ts:120-204` is
synchronous (`mdHash`, `new Date().toISOString()`, `releaseGateOpen()` which reads `process.env`
`[VERIFIED: lib/gemini-failure.ts:44-47]`, `classifyGeminiFailure` which walks a cause chain
`[VERIFIED: lib/gemini-failure.ts:76-86]`, and `console.*`):

1. `generateMagazineModelForServe` `[:135]` 2. `writeModelEnvelopeWithin` `[:141]`
3. `settleBounded` (keep) `[:153]` 4. `settleBounded` (refund) `[:175]`

| # | value | today | spent at | branded | passed | in `SERVE_BOUNDED_MS` | what actually fails if it changes |
|---|---|---|---|---|---|---|---|
| 1 | `SERVE_RESERVE_RPC_TIMEOUT_MS` | 5 000 | `callRpcBounded`, `serve-doc.ts:89` | `ReserveRpcBudget` | arg | ✓ | guard pins constant→site (`seen: 1`); r5 mutant MB red |
| 2 | `SERVE_COUNT_TOKENS_TIMEOUT_MS` | 10 000 | `countTokens` `timeout`, `gemini.ts:93` | `CountTokensBudget` | via `budget.countTokensTimeoutMs` | ✓ | **M4c → RED** |
| 3 | `SERVE_ATTEMPTS` | 2 | `generateJson` loop bound (`retries = attempts - 1`), `gemini.ts:270, 574` | `AttemptCount` | via budget | ✓ (× #4) | **M4a → RED**; but **M2 → GREEN** (see M-R6-2) |
| 4 | `SERVE_ATTEMPT_TIMEOUT_MS` | 50 000 | `generateContent` `timeout`, `gemini.ts:273` | `AttemptBudget` | via budget | ✓ | **M4b → RED** |
| 5 | `SERVE_BACKOFF_BASE_MS` | 400 | `abortableSleep`, `gemini.ts:281` | `BackoffBudget` | via budget | ✓ (via #6) | **M3 → GREEN — undefended** (M-R6-1) |
| 6 | `SERVE_BACKOFF_TOTAL_MS` | 400 | *derived, never spent* | plain `number` | — | ✓ | derivation re-checked by hand at `SERVE_ATTEMPTS` = 2 **and** 3 — see below |
| 7 | `SERVE_PUT_TIMEOUT_MS` | 15 000 | `writeModelEnvelopeWithin` expiry, `model-store.ts:79-92` | `PutBudget` | arg | ✓ | guard pins constant→site; r2 H-R2-1 mutant red |
| 8 | `SERVE_SETTLE_RPC_TIMEOUT_MS` | 5 000 | `callRpcBounded`, `serve-doc.ts:258` | `SettleRpcBudget` | arg | ✓ | guard pins constant→site |
| 9 | `SERVE_SETTLE_ATTEMPTS` | 2 | `settleBounded` loop bound, `serve-doc.ts:244, 250` | `AttemptCount` | direct import | ✓ (× #8) | **M6 (`i <= attempts`) → RED**; **M2 swap → GREEN** |
| 10 | the literal `1` | 1 | keep-path settle count, `serve-doc.ts:244` | none (guard permits `0`/`1`) | — | covered — sum pays the worst case | `serve-budget.test.ts:31-44` asserts *both* terminal paths independently |
| 11 | `SERVE_MARGIN_MS` | 20 000 | *nothing — an assumption* | plain `number` | — | in `SERVE_FLOOR_MS`, deliberately not in `SERVE_BOUNDED_MS` | labelled ASSUMPTION at `serve-budget.ts:151-153`; the brand makes `X + SERVE_MARGIN_MS` a compile error at any site (r3 H-R3-1) |

**#6, checked rather than assumed.** `generateJson` sleeps under `if (attempt < retries)`
`[VERIFIED: gemini.ts:279-281]` with `retries = attempts - 1`, so a 2-attempt budget yields exactly one
gap at `base × 2⁰` = 400. At `SERVE_ATTEMPTS = 3`: gaps after attempts 0 and 1 = 400 + 800 = 1 200; the
derivation `Array.from({length: SERVE_ATTEMPTS - 1}, (_, gap) => base * 2 ** gap)` gives 400 + 800 =
1 200. **The derivation stays correct at 3.**

**Defaults inherited from called functions — every one verified overridden on the serve path:**

| inherited default | value | overridden by | verified |
|---|---|---|---|
| `generateJson` `retries = GENERATE_JSON_RETRIES` | 2 (→3 attempts) | `budget.attempts - 1` | `gemini.ts:574`; M4a red |
| `generateJson` `baseDelayMs = 400` | 400 | `budget.backoffMs` | `gemini.ts:578`; **M3 green — the override is unobservable** |
| `generateJson` `timeoutMs = REQUEST_TIMEOUT_MS` | 60 000 | `budget.attemptTimeoutMs` | `gemini.ts:580`; M4b red |
| `assertMagazineInputWithinCap` `opts.timeoutMs` | absent → no `timeout` key | `budget.countTokensTimeoutMs` | `gemini.ts:569`; M4c red |
| `writeModelEnvelopeWithin` `blobStore = localBlobStore` | — | passed | not a duration |
| `GenerativeModel._requestOptions` (from `getGenerativeModel`) | `{}` — second arg omitted at `gemini.ts:542` | merged `{...this._requestOptions, ...requestOptions}`, ours wins | `[VERIFIED: node_modules/@google/generative-ai/dist/index.js:1420]` |
| SDK internal retry | **none exists** | — | `[VERIFIED: dist/index.js]` `makeModelRequest` → `constructModelRequest` → `makeRequest`; a single `fetch`, no retry loop, no `retry`/`backoff` identifier anywhere in the bundle |
| undici `headersTimeout` 300s / `connectTimeout` 10s | — | — | upper bounds, never extenders |
| `postgrest-js` / `@supabase/storage-js` | no internal retry | irrelevant either way | `callRpcBounded` and `writeModelEnvelopeWithin` race their own timer, bounding the whole `await` regardless of what the client does |

**Excluded, with the reason** (these look like lease work and are not):
`readFreshMagazineModel` `[serve-doc.ts:67]` and the `tryGet` probe `[:81]` run **before** the reserve;
`readFreshMagazineModel` on the `in_flight` branch `[:108]` and `readTitleStableModel` on
`owner_over_budget` `[:115]` run on branches where **we hold no lease** (`in_flight` = someone else
holds it; `owner_over_budget` = nothing was charged). All four are unbounded, and correctly so.

### VERDICT: the set is CLOSED at HEAD — and closure is not maintained by any mechanism

There is **no instance N+4**. Eleven values, every one either bounded-and-summed or explicitly
labelled an assumption; the four fan-out fields all reach their sites; the derived total is right at
2 attempts and at 3; no default leaks in; no loop bound is unrelated to the sum; nothing unbounded runs
between the reserve and the settle. The `⚠ RUNNING THINGS` question — *does the serve path really spend
the base it passes?* — is answered **yes by construction and no by observation**: it does spend it, and
mutant M3 proves nothing on this branch could tell you if it stopped.

But the enumeration above is *my* enumeration. Mutant M5 shows a twelfth entry can be added, inside the
paid lease, spending 30s the floor does not cover, with every gate green. **The set is closed; the
closure is not enforced.** That distinction is H-R6-1, and it is the difference between shipping this
branch and shipping the thing the branch says it is.

---

# 2. Round-5 fixes: genuinely fixed, or reworded?

| Fix | Verdict | Evidence |
|---|---|---|
| **H-R5-1** brand `SERVE_SETTLE_ATTEMPTS`, type the local | **Genuinely fixed — for arithmetic.** Not for a swap | Round-5 mutant MA (`SERVE_SETTLE_ATTEMPTS + SERVE_SETTLE_ATTEMPTS`) is now a **compile error**: `Budget<'attempts'> + Budget<'attempts'>` is `number`, and the local is typed `AttemptCount \| 1`. I also confirmed the annotation is load-bearing, not decorative — dropping it restores the inference site. **But mutant M2 (the swap) stays green**: M-R6-2 |
| **Backoff base branded and PASSED** | **Genuinely fixed in the code; the defending test is dead** | The value now travels with the budget `[gemini.ts:578]`. **Mutant M3 → tsc 0, 2658 green**: M-R6-1 |
| **`SERVE_BACKOFF_TOTAL_MS` DERIVED** | **Genuinely fixed** | No longer a re-typed `400`. Hand-checked against `generateJson`'s actual sleep guard at `SERVE_ATTEMPTS` = 2 (400) and = 3 (1 200); both agree |
| **0025 index drop-then-create** | **Genuinely fixed** | `if not exists` provably could not change the opclass. The live index is now `USING btree (kind, note text_pattern_ops)` `[VERIFIED: live stack]`, and I re-measured the opclass claim independently on a 20 001-row temp table — Seq Scan with `text_ops`, `Index Cond` with `text_pattern_ops`. Lock note: L-R6-2 |
| **L-R5-1 `expected_amt` as intent-not-receipt** | **Genuinely fixed and TRUE** | The `insert` is written before both ledger decrements `[VERIFIED: 0025, statement order]`, so "undertakes to return" is exactly right and "actually returned" would have been impossible |
| **0025 "byte-identical to 0020:268-298 apart from the marked insert"** | **TRUE — re-verified mechanically, not taken on trust** | I diffed the two function bodies with comments and blanks stripped and the four-line witness removed. **The only difference is `create` → `create or replace`.** Nothing else moved |
| **L-R5-2 the four line citations** | **Fixed.** All re-checked at HEAD | `0012:22` lease default 180 ✓ · `0012:53` doc_key formula ✓ · `0020:21` "no policies → no session-client access" ✓ · `blob-store.ts:10-13` `BlobRead` union ✓ · `supabase-blob-store.ts:22-24` `put` takes no signal ✓ · `generate.ts:40` the local caller ✓ · `generative-ai.d.ts:1297-1307` `SingleRequestOptions` ✓ · `gemini.ts:274` the billing latch ✓ · `gemini.ts:281` the sleep ✓. One stretch, below Low: `docs/process-checklists.md:64-68` is cited at `gemini.ts:601` for "a required parameter, never an optional field", and those lines are about union *members*, not function parameters — the principle transfers ("an optional one does not propagate"), the citation is loose |
| **The division-of-labour sentence r5 asked to correct** | **NOT DONE** | L-R6-1 — and it is now falsified in a second, independent way |

---

# 3. What else I threw at it that held

- **The settle loop bound.** Mutant M6, `i < attempts` → `i <= attempts` — an off-by-one with no
  literal and no type violation. **1 test failed.** The count is genuinely pinned against
  miscounting; only the *identity* of the constant is not (M-R6-2).
- **The other three `ServeBudget` fields.** M4a/b/c, all red, all for the right assertion — see the
  table in M-R6-1. Three of four fan-out values are properly defended.
- **The catch path spends nothing unmodelled.** `releaseGateOpen()` reads `process.env`;
  `classifyGeminiFailure` walks a cause chain with a `seen` set (no cycle, no I/O). Both synchronous.
- **The put-timeout path cannot mis-refund.** A `put` timeout throws `TimeoutError`, which
  `classifyGeminiFailure` maps to `'keep'`; and `billing.metered` is already latched `true`
  `[gemini.ts:274]` because the response body must have arrived for the put to run at all. So
  `released` is false twice over — the coupling is redundant, which is the right shape.
- **The reserve/lease direction is conservative.** The budget's clock starts before the reserve is
  sent; the lease's starts at reserve **commit**, no earlier. Durations only — no timestamp is
  compared across the two clocks, so there is no skew exposure.
- **`countTokens` really is bounded.** `[VERIFIED: dist/index.js:443-446]` `buildFetchOptions` turns
  `timeout` into `setTimeout(() => controller.abort(), …)` on the fetch signal, and
  `undefined >= 0` is `false`, so the local path (which passes no `timeout`) is untouched.
- **Both bounded wrappers clear their timer in `finally`** `[serve-rpc.ts:58-60]`,
  `[model-store.ts:~95]`, and `Promise.race` attaches a handler to the loser, so no unhandled
  rejection and no leaked event-loop hold. (The SDK's own `setTimeout` at `dist/index.js:446` is never
  cleared — a dangling ≤50s timer per attempt. It cannot extend the lease; noted, not a finding.)
- **0024's constraint sweep.** The `~*` / `!~*` narrowing still excludes compound constraints, and the
  fix-up still runs before `add constraint`. Live `guardrail_config` reads `lease_ttl_seconds = 180`,
  `max_serve_attempts = 5`, `magazine_est_cents = 6`.
- **`git status --short` is empty**, and every one of the six mutants was reverted and re-verified
  (`grep -rn "MUTANT" lib/` → 0 matches).

---

# 4. SHIP verdict

**Not yet — but the remaining work is an instrument, not a redesign, and it is the last one.**

The branch is in genuinely good shape. Round 6 found **no Blocking**, nothing that changes the design,
and — the central question of this round — **no instance N+4**. I enumerated the complete population of
values spent inside the paid lease and the set is closed: eleven entries, every default traced,
every loop bound accounted for, the backoff derivation checked at two configurations, and no unbounded
call anywhere between the reserve and the settle. The round-5 fixes are real, including the two whose
correctness I could only establish by re-measuring rather than reading. That verdict is the deliverable
the brief asked for, and I would not withhold the branch over anything I found *in* the enumeration.

What stops it is that the closure is not enforced. H-R6-1 is the same end-state as rounds 4 and 5 —
over-spend inside a paid lease, green on every gate — but arrived at by a different and more general
route: not a value someone forgot to tie to the sum, but the absence of anything that would make the
next one impossible. Three rounds have now paid for three instance fixes. The population assertion in
H-R6-1's *Fix* is roughly fifteen lines and kills all three retroactively, plus M5.

Recommended before opening the PR:

1. **H-R6-1** — assert that every exported `Budget<…>` constant in `lib/serve-budget.ts` appears as a
   term in `SERVE_BOUNDED_MS`. Re-run M5 to confirm it now fails at the *declaration*, before the call
   site exists. This is the one item I would not ship without.
2. **M-R6-1** — add `serveBudget()` to `tests/support/budget.ts` and re-assert the backoff
   pass-through with a value that is not 400. Re-run M3.
3. **M-R6-2** — split `AttemptCount` into two brands. Re-run M2.
4. **L-R6-1 / L-R6-2** — the sentence in two files, and a deploy note in 0025. No code.

Items 2–4 are individually shippable-with-follow-up. Item 1 is not, for the reason round 5 gave about
item 1 of *its* list, and which is now one round more expensive: this is the fourth consecutive round in
which a mutation restoring over-spend inside a paid lease is green on every gate the branch owns. The
difference is that this time the fix is not another identifier — it is the check that ends the series.

**NOT CONVERGED**
