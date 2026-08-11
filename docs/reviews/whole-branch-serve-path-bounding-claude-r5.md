# Whole-branch adversarial review — #46 serve-path bounding, ROUND 5 (Claude)

Worktree at `773fc9e` (`fix/serve-path-deadline`). Every load-bearing claim is tagged
`[VERIFIED: path:line]` (read at this HEAD) or `[ASSUMPTION]`. Every mutation was applied, measured,
and restored; `git status --short` is empty at the end of this review.

## Gates run

| gate | result |
|---|---|
| `npx tsc --noEmit` | exit 0 |
| `npm test` | **263 suites / 2657 passed** (round 4: 2656 — the +1 is the new freeze test) |
| `npm run test:integration` (full, `--runInBand`) | **67 suites / 487 passed**, 3 skipped, 154s. No subset run preceded it, so none of round 4's self-poisoning |
| `scripts/check-docs.py` | exit 0 |
| `scripts/check-arch-findings.py` | exit 0 — 2/18 criteria met, 0 regressed past baseline |
| `check-guard-coverage.py` · `check-sentinel-meanings.py` · `check-vocabulary-collisions.py` | exit 1 — I re-verified the "same on master" claim myself rather than inheriting it: `git archive master` into a scratch tree, ran all three, `diff` of both outputs is **empty for all three**. ADR-0007 residue, deferred by decision |

---

# Findings

## HIGH — H-R5-1. There are TWO counts on the serve path. Round 4 branded one of them. The other still takes arithmetic at its call site, and 2657 unit tests + `tsc` stay green

**Claim.** Round-4 H1 was *"the attempt COUNT is a plain mutable number"*. The fix branded
`SERVE_ATTEMPTS`/`ServeBudget.attempts` and froze the singleton. But `SERVE_SETTLE_ATTEMPTS` is also a
count, it is also spent inside the paid lease, it is also consumed at a serve call site — and it was
left a plain `number`. Arithmetic on it at that call site defeats every instrument on the branch.

**Premises.**
- `[VERIFIED: lib/serve-budget.ts:115]` — the constant, unbranded:
  ```ts
  export const SERVE_SETTLE_ATTEMPTS = 2;
  ```
  Compare `[VERIFIED: lib/serve-budget.ts:88]` `export const SERVE_ATTEMPTS = 2 as AttemptCount;`
  and `[VERIFIED: lib/serve-budget.ts:75-76]`
  `/** An attempt COUNT, not a duration — branded for the same reason (round-4 review H1). */`
  `export type AttemptCount = Budget<'attempts'>;`
- `[VERIFIED: lib/html-doc/serve-doc.ts:238]` — the call site, inside `settleBounded`:
  ```ts
  const attempts = released ? SERVE_SETTLE_ATTEMPTS : 1;
  ```
  which is the loop bound for `callRpcBounded` at `[VERIFIED: lib/html-doc/serve-doc.ts:244-253]`.
- `[VERIFIED: lib/serve-budget.ts:130]` — the sum pays for exactly two:
  `+ SERVE_SETTLE_ATTEMPTS * SERVE_SETTLE_RPC_TIMEOUT_MS`.
- `[VERIFIED: lib/serve-budget.ts:52-61]` — the claim under test, written by round 4:
  *"The division of labour is: TYPES cover literals, arithmetic and object literals; the GUARD covers
  site-swaps, counts and population."* False for this count: **neither** covers it.

**MEASURED — mutant MA.** One-token edit at `lib/html-doc/serve-doc.ts:238`:

```ts
const attempts = released ? SERVE_SETTLE_ATTEMPTS + SERVE_SETTLE_ATTEMPTS : 1;
```

Result: `npx tsc --noEmit` → **exit 0**. `npm test` → **263 suites, 2657 passed, 0 failed.**

Why every instrument misses it, one by one:
- **the brand** — `SERVE_SETTLE_ATTEMPTS` has none, so there is no brand for the addition to strip;
- **the no-literals rule** `[VERIFIED: tests/lib/html-doc/serve-bounded-import-guard.test.ts:112-121]`
  — `SERVE_SETTLE_ATTEMPTS + SERVE_SETTLE_ATTEMPTS` contains no numeric literal at all. This is
  round-3 H-R3-1's exact evasion (`SERVE_PUT_TIMEOUT_MS + SERVE_MARGIN_MS`), still open on the one
  identifier the redesign did not brand;
- **`BOUNDED_CALLS`** `[VERIFIED: …import-guard.test.ts:73-79]` — the table pins `callRpcBounded`'s
  *timeout argument*, never the surrounding loop bound. `settleBounded` is not in it;
- **`tests/lib/serve-budget.test.ts:15-24`** — asserts `SERVE_BOUNDED_MS` equals the sum of the same
  constants it was built from. A call site spending a different number is invisible to it;
- **`serve-doc-mapping.test.ts`'s settle-count tests** — `[VERIFIED: …:219-232]`
  `expect(settles).toBe(2)` and `[VERIFIED: …:356]` `expect(settles).toBe(1)`. These *would* catch it
  — except the retry only fires when an attempt fails, and under the mutant attempt 2 returns
  `{data:true}` and the loop returns `'applied'` before attempts 3–4 run. **The count is only spent
  when things are already going wrong**, which is precisely the production case.

**Consequence.** Budgeted settle time `2 × 5_000 = 10_000ms`; spent `4 × 5_000 = 20_000ms`. Worst-case
enforced work becomes `140_400 + 10_000 = 150_400ms`, and the floor `150_400 + 20_000 = 170_400ms`
= **170.4s against a lease the branch's own constraint permits to be 161s**
`[VERIFIED: supabase/migrations/0024_lease_covers_serve.sql:78]`
`check (lease_ttl_seconds >= 161)`. That is a 9.4s overrun of the lease, and the overrun is the
reclaim clause admitting a second paid producer — two charges, one document — which is the single
defect this branch exists to close.

**And 161 is not a hypothetical configuration: this migration creates it.**
`[VERIFIED: supabase/migrations/0024_lease_covers_serve.sql:72-74]`
```sql
update guardrail_config
   set lease_ttl_seconds = 161
 where lease_ttl_seconds < 161;
```
Any database whose lease was ever tuned below the floor is left sitting exactly on it. The migration's
own comment records that the local stack was one such database (*"the local stack sat at 30 and
refused the migration outright"*). `[VERIFIED: live stack]` `lease_ttl_seconds = 180` today, so the
shipped default absorbs the mutant — the exposure is the repaired-database case, not the fresh one.

**What caller reaches it.** `resolveMagazineModel` → `settleBounded` on the **refund** path
(`released = true`), i.e. every paid serve whose generation failed class-A under an open release gate
— the money path, on the branch whose reason for existing is money.

**The shape.** Standing shape **#8** — a fix asserting the INSTANCE of a CLASS defect — applied to the
round-4 fix itself. Round 4's finding was "the count is not branded"; the fix branded *the count round
4 named*. There are exactly two counts in `lib/serve-budget.ts` and it closed one. Also **#10**: the
comment at `lib/serve-budget.ts:60-61` states a division of labour that is false for this identifier.

**Proposed fix.** Mirror what was done for the durations — a per-site brand, so the arithmetic stops
compiling:

```ts
export type SettleAttemptCount = Budget<'settleAttempts'>;
export const SERVE_SETTLE_ATTEMPTS      = 2 as SettleAttemptCount;   // refund: retry once
export const SERVE_SETTLE_ATTEMPTS_KEEP = 1 as SettleAttemptCount;   // keep: the charge is already correct
```
```ts
// serve-doc.ts:238
const attempts: SettleAttemptCount = released ? SERVE_SETTLE_ATTEMPTS : SERVE_SETTLE_ATTEMPTS_KEEP;
```
`SERVE_SETTLE_ATTEMPTS * SERVE_SETTLE_RPC_TIMEOUT_MS` in the sum still compiles (arithmetic on branded
numbers yields `number`), and mutant MA becomes `TS2322: Type 'number' is not assignable to type
'SettleAttemptCount'` — the same error mutant N1 already produces for `attempts`. It also removes the
last bare `1` from `serve-doc.ts`, which is the literal the guard's `0`/`1` exemption has to wave
through. Then correct `lib/serve-budget.ts:60-61` to say the types cover the counts too.

---

## MEDIUM — M-R5-1. The `text_pattern_ops` fix cannot reach the databases that have the defect: `create index if not exists` never changes an existing index

**Claim.** Round-4's index finding was fixed by editing the opclass in place, leaving the DDL as
`create index if not exists`. On any database that already applied 0025 in its pre-fix form, that
statement is a **no-op**: the plain `text_ops` index survives, the migration reports success, and no
gate on this branch can tell the difference.

**Premises.**
- `[VERIFIED: supabase/migrations/0025_settle_is_observable.sql:56-57]`
  ```sql
  create index if not exists ledger_audit_kind_note_idx
    on ledger_audit (kind, note text_pattern_ops);
  ```
- Postgres semantics: `if not exists` matches on **name**, not definition. An existing
  `ledger_audit_kind_note_idx` with any opclass satisfies it. (No mutation needed — this is what the
  clause means.)
- `[VERIFIED: live stack]` `0025` is recorded in `supabase_migrations.schema_migrations`, and the
  index is `CREATE INDEX ledger_audit_kind_note_idx ON public.ledger_audit USING btree (kind, note
  text_pattern_ops)`. `[ASSUMPTION, resting on the round-4 Codex review's measurement that "the live
  shared DB currently has note text_pattern_ops, but the checked-in migration does not"]` — the
  correct index on this stack was therefore produced by out-of-band DDL, not by the checked-in file.
  The finding does not depend on that provenance; it depends only on the semantics of the clause.
- Round-4 Codex named the remedy explicitly and it was not taken: *"preferably under a new name or
  with drop/recreate so already-applied plain indexes are repaired."*

**MEASURED — the plan claim itself is TRUE, and worth recording because it is the thing being
protected.** On the live stack, inside `begin; … rollback;`, two temp tables with 50 000 rows each:

```
--- PLAIN text_ops ---
 Seq Scan on la_plain
   Filter: ((note ~~ 'abc123:%'::text) AND (kind = 'serve_settle'::text))

--- text_pattern_ops ---
 Index Scan using la_pat_kind_note_idx on la_pat
   Index Cond: ((kind = 'serve_settle'::text) AND (note ~>=~ 'abc123:'::text) AND (note ~<~ 'abc123;'::text))
```
`[VERIFIED: live stack]` `datcollate = en_US.UTF-8`. The migration's quoted `Index Cond` is exactly
right. And the opclass change breaks nothing: equality on `note` still plans as
`Index Cond: ((kind = 'serve_settle') AND (note = 'abc123:false'))`, and no other query in the repo
touches `note` — `[VERIFIED]` `grep -rn ledger_audit` over `*.ts`/`*.py`/`*.sh` outside `docs/` returns
only `reservation-release.test.ts`, `settle-rpc-shape.test.ts` and three comment lines in
`serve-doc.ts`.

**Consequence.** Production has never seen 0025, so this is not a live production defect *today*. What
it is, is a fix that is inert on every environment that currently has the problem — and there is no
instrument anywhere on the branch that reads the opclass, so nothing will ever say so. That is
standing shape **#3** (a green gate testing the wrong thing) in its weakest form: the gate is not
wrong, it is absent, and the migration's own success is the false green.

**What caller reaches it.** An operator following the `indeterminate` log at
`[VERIFIED: lib/html-doc/serve-doc.ts:197-198]`
``RESOLVE: select * from ledger_audit where kind = 'serve_settle' and note like '<token>:%'`` on a
database repaired-in-place rather than built from scratch.

**Proposed fix.** Two lines, no new mechanism:
```sql
drop index if exists ledger_audit_kind_note_idx;
create index ledger_audit_kind_note_idx on ledger_audit (kind, note text_pattern_ops);
```
(or rename to `ledger_audit_kind_note_pattern_idx` and drop the old name). If the opclass is worth a
27-line comment justifying it, it is worth a statement that actually applies it.

---

## LOW — L-R5-1. The third overclaimed comment: `expected_amt` for `serve_settle` is written *before* the ledgers move, so it cannot be "the amount actually returned"

**Claim.** Round 4 answered L-R4-3 (does `expected_amt` mean two things?) with a gloss that is false
in the one case the column was originally invented for.

**Premises.**
- `[VERIFIED: supabase/migrations/0025_settle_is_observable.sql:81-83]`
  > `expected_amt` MEANS ONE THING across every kind: THE CENTS THIS ROW IS ABOUT. For
  > `release_underflow` that is the amount whose guarded decrement failed; for `serve_settle` it is
  > **the amount actually returned to the ledgers**, hence 0 on a keep, where nothing moved.
- `[VERIFIED: supabase/migrations/0025_settle_is_observable.sql:97-100]` — the witness insert.
- `[VERIFIED: supabase/migrations/0025_settle_is_observable.sql:102-117]` — the two guarded
  decrements, and their `if not found then insert … 'release_underflow'` branches, all of which run
  **after** line 100.

The insert precedes both `update`s, so it cannot know what moved. When either guarded decrement finds
no row, the transaction commits a `serve_settle` row asserting `magazine_est_cents` alongside a
`release_underflow` row recording that that exact amount did **not** move. The umbrella sentence
("THE CENTS THIS ROW IS ABOUT") survives; the `serve_settle` gloss does not.

The same wording is repeated in the test: `[VERIFIED: tests/integration/settle-rpc-shape.test.ts:121]`
`expect(data![0].expected_amt).toBeGreaterThan(0);   // the magazine estimate that was returned`.

**Consequence.** Documentation only — no behaviour changes, and reconciliation still works because the
`release_underflow` row is right there. But it is a comment claiming a guarantee the code does not
give (standing shape **#10**), on the exact line a future operator would trust when reconciling money.

**Proposed fix.** One word: *"…for `serve_settle` it is the amount this settle **undertook to return**
(0 on a keep). If the guarded decrement then failed, a `release_underflow` row for the same token
records that it did not land — the two rows are read together."*

---

## LOW — L-R5-2. Two premise citations point at the wrong line, in a branch whose own rule is to quote rather than characterise

- `[VERIFIED: lib/serve-budget.ts:90]` — `/** generateJson backoff: 400 * 2**n summed over
  (SERVE_ATTEMPTS - 1) gaps (`gemini.ts:267`). */` and `[VERIFIED: tests/lib/serve-budget.test.ts:64]`
  — `// gemini.ts:267 — baseDelayMs * 2**attempt, baseDelayMs = 400`.
  `[VERIFIED: lib/gemini.ts:267]` is `timeoutMs = REQUEST_TIMEOUT_MS,`. The default is at
  `[VERIFIED: lib/gemini.ts:263]` `baseDelayMs = 400,` and the sleep at
  `[VERIFIED: lib/gemini.ts:281]`. The citation was correct before this branch inserted the
  `timeoutMs` parameter above it, and both copies moved with neither being re-read.
- `[VERIFIED: lib/html-doc/serve-doc.ts:258]` and `[VERIFIED: tests/lib/html-doc/serve-doc-mapping.test.ts:236]`
  both cite `0020_reservation_release.sql:280` for `if not found then return false`.
  `[VERIFIED: supabase/migrations/0020_reservation_release.sql:280]` is `returning day into v_day;`;
  the cited statement is line **281**.

**Consequence.** None to behaviour. Reported because premise citations are the mechanism this review
process uses to verify claims cheaply, and two of them are now off by a line or six.

**Not a finding, recorded so it is not re-raised:** while checking the backoff I confirmed the term is
genuinely *enforced*, not merely *added* — `[VERIFIED: lib/gemini.ts:279-282]` the sleep is guarded by
`if (attempt < retries)`, so `retries = 1` yields exactly one 400ms gap, matching
`SERVE_BACKOFF_TOTAL_MS`. `baseDelayMs`'s default is duplicated in three places with nothing tying
them, but the whole term is 400ms against a 20 000ms margin, so a drift there cannot reach the lease.
That is a different class from `SETTLE_SLACK_MS` (a term that bounded nothing) and I am not raising it.

---

# Round-4 fixes: genuinely fixed, or reworded?

**Fix 1 — branded `AttemptCount`, `readonly` fields, `Object.freeze`. GENUINELY FIXED for the field it
names; the class is not closed (H-R5-1).**

I attacked it with nine mutants, all applied to `lib/html-doc/serve-doc.ts` at HEAD, each run through
`tsc --noEmit` and (where it compiled) the unit suite:

| # | mutant | result |
|---|---|---|
| M1 | `SERVE_BUDGET.attempts = SERVE_ATTEMPTS + SERVE_ATTEMPTS` | **TS2540** `Cannot assign to 'attempts' because it is a read-only property` |
| M4 | `structuredClone(SERVE_BUDGET).attempts = …` | **TS2540** — the clone keeps the type, so it keeps `readonly` |
| M6 | `const B: ServeBudget = JSON.parse(JSON.stringify(SERVE_BUDGET)); B.attempts = …` | **TS2540** |
| N1 | `{ ...SERVE_BUDGET, attempts: SERVE_ATTEMPTS + SERVE_ATTEMPTS }` passed at the call site | **TS2322** `Type 'number' is not assignable to type 'AttemptCount'` |
| N3 | `{ ...SERVE_BUDGET, attempts: 4 as AttemptCount }` | compiles; **2 suites red** (no-literals guard + mapping) |
| N2 | `{ ...SERVE_BUDGET, attempts: (SERVE_ATTEMPTS + SERVE_ATTEMPTS) as AttemptCount }` | compiles, guard green; **mapping test red** — `toEqual` catches the value drift |
| R1 | `Object.assign(SERVE_BUDGET, { attempts: … })` at runtime | compiles; **10 tests red** — `Object.assign` uses `[[Set]]` with throw-on-failure, so a frozen target throws `TypeError` regardless of strict mode |
| R2 | `Reflect.defineProperty(SERVE_BUDGET, 'attempts', { value: … })` | compiles, all green — **and harmless**: verified directly in node that on a frozen object it returns `false` and leaves the value at 2 |
| R3 | delete `Object.freeze` from `lib/serve-budget.ts` | **the new test goes red**, so the freeze is load-bearing rather than decorative |

The only surviving escape (N2) needs a hand-written `as AttemptCount`, which forges the brand
outright — a limit the file states and accepts ("The one place the brand is minted") — and it is still
caught by a test. The freeze being **shallow** does not matter here: every value in `SERVE_BUDGET` is
a primitive `number` `[VERIFIED: lib/serve-budget.ts:163-167]`. `readonly` + the brand break no
legitimate use: `tsc --noEmit` is exit 0 at HEAD and both suites are green.

What is *reworded* rather than fixed is round 4's own recommendation list. Of its three proposed fixes
only #1 was applied:
- #2 (pin the constants against independently-written literals) — **not applied, and I now think it
  was wrong**. `[VERIFIED: tests/lib/serve-budget.test.ts:93-112]` already pins all three of migration
  0024's floor literals to `SERVE_FLOOR_SECONDS`, and `[VERIFIED: …:59-61]` pins
  `SERVE_FLOOR_SECONDS <= 180`. I checked the pair actually closes the loop: raising any enforced
  constant moves `SERVE_FLOOR_SECONDS` off 161 and the migration-literal test fails; "fixing" the
  migration to match then fails the `<= 180` test. The constants are anchored. Saying so would have
  been better than silence, but the omission is correct.
- #3 (`toBe(SERVE_BUDGET)` so the test's name is true) — **not applied.**
  `[VERIFIED: tests/lib/html-doc/serve-doc-mapping.test.ts:193-198]` the test is still named *"hands
  the serve wrapper SERVE_BUDGET itself — **not merely some object of that shape**"* while asserting
  `expect(budgetArg).toEqual(SERVE_BUDGET)`, which is precisely "some object of that shape". The
  identity claim is now delivered by the freeze rather than by this assertion, so there is **no live
  defect** — mutants R1/R2 confirm an in-place retune is impossible — but the sentence is still
  false, on standing shape **#9** (vocabulary refined while the fact stays unobservable). One word.

**Fix 2 — `note text_pattern_ops`. The claim is TRUE and MEASURED; the delivery mechanism is not
(M-R5-1).** Plans reproduced above, matching the migration's quoted `Index Cond` exactly.

**Fix 3 — the comment corrections. Two of three hold; one overreaches (L-R5-1).**
- `lib/serve-budget.ts:52-61` — "a swap between the two RPC budgets DOES still type-check" is
  **MEASURED true** (mutant MB: `SERVE_SETTLE_RPC_TIMEOUT_MS` at the reserve site, `tsc` exit 0) and
  "the text guard is what covers that case" is **MEASURED true** (mutant MB turns
  `serve-bounded-import-guard` red on the `seen: 1` assertion for both constants). But the last
  sentence of that paragraph — *"the GUARD covers site-swaps, counts and population"* — is false for
  `SERVE_SETTLE_ATTEMPTS`, which is H-R5-1.
- `0025`'s TRUNCATE paragraph — **fully verified on the live stack**:
  `has_table_privilege('authenticated','public.ledger_audit','truncate')` and the `anon` equivalent
  are both `t`; `has_table_privilege('service_role','public.ledger_audit','delete')` is `f`, so the
  retention paragraph's "`service_role` holds no DELETE" is also true. The scope claim ("not
  reachable through PostgREST") matches the code: `[VERIFIED]` no repo query touches TRUNCATE.
- `0025`'s "byte-identical to 0020:268-298 apart from the marked insert — verified by diffing" —
  **I re-diffed the two function bodies mechanically** (comments and blank lines stripped). The only
  differences are `create` → `create or replace` and the four-line witness insert. The claim holds.
- `0025`'s alarm warning (`sum(expected_amt)` must now filter on kind) — **checked for a live break,
  found none.** Every existing `ledger_audit` assertion is already scoped:
  `[VERIFIED: tests/integration/reservation-release.test.ts:200-201]`
  `.eq('kind','release_underflow').eq('note', 'fail_job '+jobId)`. The hazard is genuinely
  future-only, and it is written down.
- `0025`'s retention paragraph — a stated policy change with the grant checked. Holds.

---

# What else I threw at it that held

Recorded so a bare verdict is not the only output.

- **The lease premise.** `[VERIFIED: supabase/migrations/0012_serve_model_charge.sql:60,62]` the lease
  is `now() + make_interval(secs => lease_ttl_seconds)` stamped at reserve **commit**, so the app's
  budget (which starts before the reserve is sent and pays 5s for it) is measured conservatively
  against it. No clock-skew exposure: both sides measure durations, never compare timestamps.
- **Every enforced term is really enforced.** The one new external bound is `countTokens`, and it is
  real: `[VERIFIED: node_modules/@google/generative-ai/dist/generative-ai.d.ts:778]` takes
  `SingleRequestOptions`, and `[VERIFIED: node_modules/@google/generative-ai/dist/index.js:443-446]`
  `buildFetchOptions` turns `timeout` into `setTimeout(() => controller.abort(), …)` on the fetch
  signal, via `makeModelRequest` `[VERIFIED: …/index.js:1293]`. Installed version 0.24.1. No
  `SETTLE_SLACK_MS`-class term (added but unenforced) remains.
- **Both terminal paths, re-derived by hand.** Keep: reserve 5 + countTokens 10 + 2×50 + 0.4 + put 15
  + settle 5 = 135.4s. Refund: 5 + 10 + 100 + 0.4 + 2×5 = 125.4s. Pathological (put ran *and* refund):
  140.4s. All ≤ `SERVE_BOUNDED_MS`. Nothing unbounded runs between the reserve and the settle —
  `readFreshMagazineModel` and the `tryGet` probe are both **before** the reserve
  `[VERIFIED: lib/html-doc/serve-doc.ts:66,80]`, and the two post-reserve blob reads are on the
  `in_flight` and `owner_over_budget` branches, where no lease is held.
- **No unhandled rejection or leaked timer.** `Promise.race` attaches handlers to the losing promise,
  and both bounded wrappers clear their timer in `finally`
  `[VERIFIED: lib/serve-rpc.ts:58-60]`, `[VERIFIED: lib/html-doc/model-store.ts:95-102]`.
- **`releaseToken` is non-null exactly when `status = 'reserved'`.**
  `[VERIFIED: supabase/migrations/0020_reservation_release.sql:200,250,254,257-258]` — declared null,
  minted only in the reserved branch, nulled on both exception branches.
- **The delegating `generateMagazineModelForServe` mocks in the integration files do not create
  vacuity.** They discard arguments, but every assertion on them is a **call count**
  (`[VERIFIED: tests/integration/html-download.test.ts:142,160,176]` and five more), which the
  delegate preserves; and the *identity* of the function called is pinned by the import guard's
  `BANNED` list `[VERIFIED: …import-guard.test.ts:82-93]`, not by these files.
- **The population check works.** `[VERIFIED: …import-guard.test.ts:128]` asserts `sites === calls`
  before checking any constant, so a fifth bounded call cannot be added silently.
- **`git status --short` is empty**, and every mutant above was restored and re-verified.

---

# SHIP verdict

**Not yet — one line of code away.** The branch is in good shape: `tsc` clean, 2657 unit and 487
integration tests green, the schema-gate residue proven identical to `master`, the spec's accepted
residual pinned by a characterisation test, three backlog entries carrying the deferred work, and the
round-4 High genuinely closed against nine mutants rather than reworded. Round 5 found **no Blocking**
and nothing that changes the design.

What stops it is H-R5-1, and it stops it for the same reason round 4 stopped: a mutation that restores
over-spend inside a paid lease is **green on every gate this branch owns**. Shipping with it means the
branch's headline claim — *the serve path's work fits the lease, for every configuration the
constraint permits* — is false for the configuration migration 0024 itself writes. The fix is two
constants and a type annotation, and it makes mutant MA a compile error.

Recommended before opening the PR:

1. **H-R5-1** — brand `SERVE_SETTLE_ATTEMPTS` (and its `1`), annotate the local, correct the
   division-of-labour sentence at `lib/serve-budget.ts:60-61`. Re-run mutant MA to confirm it now
   fails `tsc`.
2. **M-R5-1** — `drop index if exists` before the `create`, or rename it.
3. **L-R5-1 / L-R5-2** — three comment edits, no code. Cheap, and this branch has now had three
   overclaimed comments caught by reviewers, which is itself the signal.

Items 2 and 3 are individually shippable-with-follow-up; item 1 is not, because it is the same class
of defect that has now consumed rounds 1, 2, 3, 4 and 5, and the whole point of the round-3 redesign
was to stop paying for it one identifier at a time. Closing it for the *class* — both counts, not the
one a reviewer named — is what would let round 6 be short.

**NOT CONVERGED**
