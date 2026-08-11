# Whole-branch adversarial review — #46 serve-path bounding, ROUND 4 (Claude)

Worktree at `d8e5222` (`fix/serve-path-deadline`). Every claim below is tagged `[VERIFIED: path:line]`
(read at this HEAD) or `[ASSUMPTION]`. Mutations were applied, measured, and restored;
`git status --short` is empty at the end of this review.

## Gates run

| gate | result |
|---|---|
| `npx tsc --noEmit` | exit 0 |
| `npm test` | 263 suites / **2656 passed** |
| `npm run test:integration` (full) | **67 suites / 487 passed**, 3 skipped, 176s |
| `scripts/check-docs.py` · `scripts/check-arch-findings.py` | OK |
| `check-guard-coverage.py` · `check-sentinel-meanings.py` · `check-vocabulary-collisions.py` | exit 1 — **byte-identical output on `master`** (`git archive master` into a scratch tree, `diff` empty). ADR-0007 residue, deferred by decision |

One caveat on the integration numbers. My *first* full run reported 5 failures across
`serve-model-charge`, `job-queue-producer` and `reservation-release`. Those were residue from two
targeted subset runs I had done first (the suite shares one `guardrail_config` singleton and one
`spend_ledger` day). Re-running the full suite immediately afterwards, with no code change, gave
487/487. I then re-ran the exact failing subset pair (`settle-rpc-shape reservation-release`) and got
38/38. **The self-poisoning is mine, not the branch's**, and the documented idempotence property
(`docs/roadmap-to-launch.md:355-359`) holds. Reporting it because a future reader will hit the same
thing: this suite is only idempotent full-run-to-full-run, not subset-then-full.

---

# Findings

## HIGH — H-R4-1. `attempts` is the one budget field with no brand, and the singleton is mutable — a fully-green mutant puts 240s of enforced work under a 161s lease

**Claim.** Redesign 1 makes a wrong *duration* unrepresentable but leaves the *count* — the exact field
of round-1 H1's mutant — an unbranded, writable property of an unfrozen exported object. There is a
mutation that compiles and passes all 2656 unit tests.

**Premises.**
- `[VERIFIED: lib/serve-budget.ts:135-143]` — the interface. Only the phantom is `readonly`:
  ```ts
  export interface ServeBudget {
    readonly [budgetBrand]: 'serveBudget';
    attempts: number;
    attemptTimeoutMs: AttemptBudget;
    countTokensTimeoutMs: CountTokensBudget;
  }
  ```
- `[VERIFIED: lib/serve-budget.ts:146-150]` — `export const SERVE_BUDGET = { … } as ServeBudget;`
  No `Object.freeze`.
- `[VERIFIED: lib/serve-budget.ts:47-48]` — the claim under test: *"Each budget carries a phantom brand
  naming the call site it belongs to… an integer literal is a plain `number`, so it no longer
  type-checks."* True of the three duration fields, false of `attempts`.

**MEASURED — mutant M3.** Inserted one statement into `resolveMagazineModel`, immediately before the
billing latch (`lib/html-doc/serve-doc.ts:132`):

```ts
SERVE_BUDGET.attempts = SERVE_ATTEMPTS + SERVE_ATTEMPTS;
```

Result: `npx tsc --noEmit` → **exit 0**. `npm test` → **263 suites, 2656 passed, 0 failed.**

Why every instrument misses it:
- **the brand** — `attempts: number`, and the field is not `readonly`, and the object is not frozen;
- **the no-literals rule** `[VERIFIED: tests/lib/html-doc/serve-bounded-import-guard.test.ts:112-121]` —
  `SERVE_ATTEMPTS + SERVE_ATTEMPTS` contains no numeric literal at all;
- **the import guard's `mustContain`** `[VERIFIED: …import-guard.test.ts:80]` — the call site still reads
  `SERVE_BUDGET` verbatim;
- **the value assertion** `[VERIFIED: tests/lib/html-doc/serve-doc-mapping.test.ts:193-198]` —
  `expect(budgetArg).toEqual(SERVE_BUDGET)` compares the mutated singleton **to itself**. It is the
  same object reference. It cannot fail on an in-place mutation;
- **`tests/lib/serve-budget.test.ts`** — jest gives each test file its own module registry, and that
  file never invokes `resolveMagazineModel`, so its copy of `SERVE_BUDGET` is pristine.

**Consequence.** 4 attempts × 50s = 200_000ms, plus reserve 5_000 + countTokens 10_000 + backoff
(now 400+800+1600 = 2_800, not 400) + put 15_000 + 2 settles 10_000 = **~242.8s of enforced work
against the 161s lease floor** `[VERIFIED: supabase/migrations/0024_lease_covers_serve.sql:78]`. That is
larger than the 181.2s-vs-180s overrun this entire branch exists to close, and it re-opens the reclaim
clause admitting a second paid producer.

**What caller reaches it.** Every authenticated serve of a promoted summary whose model is absent or
drifted — `resolveMagazineModel` is on the single paid path.

**The shape.** This is standing shapes **#4** (a negative test that passes for the wrong reason — and
whose *name*, "hands the serve wrapper SERVE_BUDGET itself — **not merely some object of that shape**",
describes `toBe` identity while the assertion is structural `toEqual`; under an in-place mutation
*neither* would fail) and **#8** (a fix asserting the INSTANCE where the defect is a CLASS). The
redesign was meant to retire exactly this dependence on a per-call-site runtime assertion.

**Proposed fix**, in order of value:
1. `lib/serve-budget.ts:135-150` — make every `ServeBudget` field `readonly`, and mint the singleton as
   `Object.freeze({ … }) as ServeBudget`. `readonly` alone stops the compile; `freeze` also stops it
   through an `any`.
2. `tests/lib/serve-budget.test.ts` — pin `SERVE_ATTEMPTS`, `SERVE_ATTEMPT_TIMEOUT_MS` and
   `SERVE_COUNT_TOKENS_TIMEOUT_MS` against **independently written literals**, the way
   `tests/lib/gemini-serve-budget.test.ts:10-12` already pins the local path (`LOCAL_REQUEST_TIMEOUT_MS
   = 60_000`, `LOCAL_ATTEMPTS = 3`, with a comment saying importing them would defeat the point). The
   serve side is the only one currently asserted against itself.
3. `tests/lib/html-doc/serve-doc-mapping.test.ts:198` — `toBe(SERVE_BUDGET)`, so the test's name is true.

---

## MEDIUM — M-R4-1. Migration 0025's index does not serve the query migration 0025 exists to serve

**Claim.** The operator instruction printed on `indeterminate` uses `note like '<token>:%'`. With the
index exactly as 0025 writes it, that query plans as a **Parallel Seq Scan**. The migration's own
justification for the index is therefore not achieved.

**Premises.**
- `[VERIFIED: supabase/migrations/0025_settle_is_observable.sql:29-32]`
  ```sql
  -- The lookup this exists to serve is "did THIS token settle?", i.e. by (kind, note). Without an
  -- index that read is a sequential scan over every audit row ever written, and an operator
  -- instruction nobody can afford to follow is the same defect one layer out.
  create index if not exists ledger_audit_kind_note_idx on ledger_audit (kind, note);
  ```
- `[VERIFIED: lib/html-doc/serve-doc.ts:196-199]` — the log emits
  ``RESOLVE: select * from ledger_audit where kind = 'serve_settle' and note like '<token>:%'``.
- `[VERIFIED]` live DB collation is `en_US.UTF-8`. A plain btree opclass cannot answer a `LIKE
  'prefix%'` range under a non-C collation; only `text_pattern_ops` (or `= `) can.

**MEASURED**, inside `begin; … rollback;` on the shared stack, after recreating the index exactly as
0025 writes it and loading 200k `serve_settle` rows:

```
-- note like '<token>:%'
Gather  (actual time=20.418..22.610 rows=0)
  ->  Parallel Seq Scan on ledger_audit   Rows Removed by Filter: 100088
Execution Time: 22.635 ms

-- note = '<token>:false'
Index Scan using ledger_audit_kind_note_idx   Index Cond: ((kind = …) AND (note = …))
Execution Time: 0.040 ms
```

The `kind = 'serve_settle'` equality does still use the leading column — but `serve_settle` becomes
*the* dominant kind by construction (one row per paid serve, forever, versus `release_underflow` only
on an anomaly), so that prefix buys almost nothing. 566× on 200k rows, growing linearly.

**What caller reaches it.** An operator following the `indeterminate` instruction — which is the whole
deliverable of redesign 2.

**Proposed fix.** Prefer changing the *query*, not the index: `serve-doc.ts` has `released` in scope at
`:187`, and the note is fully determined by `<token>:<released>`, so emit
``note = '<token>:' || released`` (measured 0.040 ms, no opclass subtlety). Alternatively index
`(kind, note text_pattern_ops)`. Whichever is chosen, the two must be chosen *together* — that
coupling is the point.

> **Contamination note.** The live DB currently carries `ledger_audit_kind_note_idx` as
> `btree (kind, note text_pattern_ops)`, which is **not** what `0025` writes. A concurrent reviewer's
> worktree (`wt-codex-r4`, same commit, byte-identical `0025`) evidently created it by hand and did
> not roll back. Two consequences worth stating: my EXPLAIN above deliberately dropped and recreated
> the migration's own definition inside a rolled-back transaction, so it measures the shipped
> artifact; and because `create index **if not exists**` is name-based, a database that already has
> some index of that name will silently skip 0025's — worth remembering for deploy.

---

## LOW — L-R4-1. The two RPC budgets share a union type, so a swap between them still compiles

`[VERIFIED: lib/serve-rpc.ts:31]` — `timeoutMs: ReserveRpcBudget | SettleRpcBudget`.

**MEASURED — mutant M2.** Replaced `SERVE_RESERVE_RPC_TIMEOUT_MS` with `SERVE_SETTLE_RPC_TIMEOUT_MS` at
the reserve call site (`lib/html-doc/serve-doc.ts:88`): `tsc --noEmit` → **exit 0**.

So `lib/serve-budget.ts:49-50`'s claim — *"one site's budget is not another's type, so a swap no longer
type-checks"* — is false at precisely the two sites that share a helper, which is where a swap is
easiest to write. The text guard does catch it (`import-guard.test.ts:78-82` asserts each constant
appears exactly once), and both values are `5_000` today, so there is no live consequence. But the
compile-time property is the one the redesign was bought for, and here it is the backstop doing the work.

**Proposed fix.** Make `callRpcBounded` generic over the site: `callRpcBounded<T, S extends string>(…,
timeoutMs: Budget<S>, …)` does not help by itself; the honest form is two thin wrappers
(`callReserveRpc` / `callSettleRpc`) each taking its own brand, or a `site` discriminator paired with
the budget. Low priority — the values are equal and the text guard covers it.

## LOW — L-R4-2. `ledger_audit` becomes an unbounded append log in a table nothing may prune

`[VERIFIED]` live grants: `service_role` holds `INSERT, SELECT, REFERENCES, TRIGGER, TRUNCATE` on
`ledger_audit` — **no DELETE**. `[VERIFIED: docs/roadmap-to-launch.md:348-352]` this is deliberate:
*"`ledger_audit`: **cannot be wiped, and must not be.**"*

0025 changes the table from exception-only to one row per settled serve, forever, with no retention
path available to the app role. At this project's scale that is small, and the append-only property is
worth more than the bytes — but it is a policy change made implicitly, and it is the same growth curve
that makes M-R4-1's seq scan get worse rather than better. Worth one sentence in the migration saying
the decision was taken knowingly.

## LOW — L-R4-3. `expected_amt` now means two different things depending on `kind`

`[VERIFIED: supabase/migrations/0020_reservation_release.sql:16]` — `expected_amt int not null`. In
every pre-existing writer it is *the amount whose guarded decrement failed* (an anomaly). In 0025 it is
*the amount refunded, 0 on a keep* `[VERIFIED: 0025:56-59]` — a routine value, and `0` is now a legal
value where previously every row carried a real amount.

No live consequence found: every assertion in the repo filters on `kind` first
(`reservation-release.test.ts:200,364`; `settle-rpc-shape.test.ts:94,105,118`), and the full
integration suite passes. Flagging it because a future "sum `expected_amt` for today" alarm — the
obvious thing to build on a money audit table — would now silently include routine serve settles.

---

# Required section 1 — Redesign 1 (brands): does it close the class?

**Partly. It closes the three duration shapes by type, and leaves the count shape to the same
runtime/text instruments the escalation rule was invoked to retire.**

What I threw at it, all measured with `npx tsc --noEmit` on a real mutation, each restored:

| # | mutant at the serve call site | tsc | unit suite |
|---|---|---|---|
| M4 | `{ attempts: 3, attemptTimeoutMs: 60_000, countTokensTimeoutMs: 10_000 }` (round-1 H1 verbatim) | **error TS2322** ×2 | — |
| M5 | `writeModelEnvelopeWithin(120_000, …)` (round-2 H-R2-1 verbatim) | **error TS2345** | — |
| M6 | `writeModelEnvelopeWithin(SERVE_PUT_TIMEOUT_MS + SERVE_MARGIN_MS, …)` (round-3 H-R3-1 verbatim) | **error TS2345** | — |
| M7 | `writeModelEnvelopeWithin(SERVE_RESERVE_RPC_TIMEOUT_MS, …)` (cross-site swap) | **error TS2345**, `'reserveRpc' is not assignable to 'put'` | — |
| M2 | reserve site given `SERVE_SETTLE_RPC_TIMEOUT_MS` | **exit 0** | caught by import guard (1 fail) → L-R4-1 |
| M1 | `{ ...SERVE_BUDGET, attempts: SERVE_ATTEMPTS + 1 }` | **exit 0** | caught by `serve-doc-mapping.test.ts:198` (1 fail) |
| M3 | `SERVE_BUDGET.attempts = SERVE_ATTEMPTS + SERVE_ATTEMPTS` | **exit 0** | **2656 passed, 0 failed** → H-R4-1 |

The four shapes the redesign claims to make unrepresentable (M4–M7) **are** unrepresentable, and the
error messages name the brand, so a developer hitting one is told what is wrong. That is a real
improvement over three rounds of text detectors, and it is the right move.

The gap is that `attempts` — a count, not a duration — carries no brand, `ServeBudget`'s fields are
not `readonly`, and `SERVE_BUDGET` is not frozen. Object spread over the singleton reproduces the
type (M1); direct assignment mutates it for every consumer in the process (M3). M1 survives only
because of a value assertion at one call site, and M3 survives that assertion too because the
assertion compares the mutated object to itself.

Other evasions tried that did **not** work, and why:
- `as` casts in `lib/` — there are none on the budget path; the only casts are the three minters in
  `lib/serve-budget.ts` itself and the three in `tests/support/budget.ts`.
- `tests/support/budget.ts` imported from `lib/` — nothing structurally prevents it, but it does not
  occur and the file says so `[VERIFIED: tests/support/budget.ts:11-13]`. Not worth a guard.
- `Number(x)` / `+x` / `Math.min(A, B)` — all yield plain `number`, so all fail at the boundary. This
  is the arithmetic property working as designed.
- an `any`/`unknown` erasing the brand mid-path — none found between `lib/serve-budget.ts` and the
  four bounded call sites.

**Did branding break existing behaviour?** No. `[VERIFIED: lib/gemini.ts:518, 262-267]` the local caller
omits the 4th parameter, so `generateJson` falls back to `GENERATE_JSON_RETRIES` and
`REQUEST_TIMEOUT_MS`, and `tests/lib/gemini-serve-budget.test.ts:90-101` pins that at 3 × 60_000
against hardcoded literals. I also confirmed the countTokens bound is a real bound rather than a term
that is merely added: `[VERIFIED: node_modules/@google/generative-ai/dist/index.js:441-455]`
`buildFetchOptions` does `setTimeout(() => controller.abort(), requestOptions.timeout)` and
`countTokens` routes through it (`:1293`, `:1410-1421`), and `timeout >= 0` is false for `undefined`,
so the local path reaches `countTokens` with exactly the call it made before. One deliberate-looking
side effect worth naming: the cloud **worker** path now passes `opts.signal` into `countTokens` where
it previously passed nothing, so a job cancellation now aborts the preflight. That is an improvement,
but it is a behaviour change outside the serve path and it is not asserted anywhere.

# Required section 2 — Redesign 2 (observable settle): is the biconditional true, and is the SQL faithful to 0020?

**The SQL is faithful. The biconditional is true, and I proved it rather than reasoning about it.
The only defect is in the index, not the money rules.**

**Faithfulness.** Mechanical `difflib` of `0020_reservation_release.sql:268-299` against `0025:37-78`.
The complete set of differences is:

1. `create function` → `create or replace function`
2. the ten added lines (5 comment, 4 statement, 1 blank) of the witness insert

Nothing else. Every money rule is byte-identical: the `>= v_cfg.magazine_est_cents` guard on the
one-shot update, `returning day into v_day`, the `if not found then return false` idempotence gate,
both guarded decrements with their `>=` predicates, and both `release_underflow` audit notes with
their exact text. `create or replace` preserves ACLs and ownership; confirmed live —
`prosecdef = t`, `proconfig = {search_path=public}`,
`proacl = {postgres=X/postgres,authenticated=X/postgres,anon=X/postgres}`, identical to
`reserve_serve_model`'s. `0025` correctly does not re-issue `revoke`/`grant`, and does not need to.

**The biconditional, tested not assumed.** The interesting direction is "the settle applies but no row
is written". The witness sits between the `not found` gate and the first money branch with no
intervening statement, and there is no exception block anywhere in the function, so any failure
unwinds the whole call. I forced it: inside `begin; … rollback;`, seeded a `serve_model_charge` row
with a known token, set `request.jwt.claims`, added `check (kind <> 'serve_settle') not valid` to make
the witness insert fail, and called `settle_serve_model`:

```
NOTICE:  settle RAISED as expected: new row for relation "ledger_audit" violates check constraint
NOTICE:  AFTER FAILED WITNESS: release_token still set? t  reserved_cents = 6 (est 6)
```

The settle rolled back with it. The same argument covers the `release_underflow` branches the brief
asked about: they run *after* the witness, and if one raises, the transaction takes the witness and the
settle with it. There is no state in which the row and the settle disagree.

The consequence to state plainly: **the settle now depends on `ledger_audit` accepting an insert.**
That is a new availability coupling on the money path. It is the correct trade — the alternative
(an autonomous or exception-swallowed insert) would break the biconditional the migration exists to
create — and it fails closed: the reservation stands, the token stays valid, and `settleBounded`
reports `indeterminate`, which is now resolvable. Worth one line in the migration comment.

**Double settle.** Proved from the SQL, not assumed: the successful update sets `release_token = null`
`[VERIFIED: 0025:47]`, and the match predicate is `release_token = p_token` `[VERIFIED: 0025:48]`, so a
second call with the same token cannot match. `settle-rpc-shape.test.ts:64-79` measures it against the
live database. `note` is therefore unique per token in practice. The update is not scoped by
`doc_key`/`day`, so two rows sharing a token would both settle and `v_day` would be arbitrary — but
tokens are `gen_random_uuid()` (`0020:250`), and this is pre-existing 0020 behaviour either way.

**RLS and grants.** Verified live under `set local role`, in a rolled-back transaction:
```
NOTICE:  SELECT DENIED: permission denied for table ledger_audit
NOTICE:  INSERT DENIED: permission denied for table ledger_audit
NOTICE:  anon SELECT DENIED: permission denied for table ledger_audit
```
`ledger_audit` remains `relrowsecurity = t`, `relforcerowsecurity = t`, zero policies, and
`anon`/`authenticated` hold only `REFERENCES, TRIGGER, TRUNCATE`. The insert succeeds because the
function is `security definer` owned by `postgres`, which has `rolbypassrls = t`. `0020:20-22` is intact.

**Suite interaction.** Every `ledger_audit` assertion in the repo is `kind`-scoped, and the new file
scopes by a freshly minted token — the same per-run-discriminator pattern
`docs/roadmap-to-launch.md:352-354` prescribes. Full integration suite: 487 passed.

**Retention and index** — see L-R4-2 and M-R4-1. The index is the one thing in this redesign that does
not do what its comment says.

# Required section 3 — Escalation verdict

**Converging, but not converged. One High, and `docs/dev-process.md`'s four-non-converging-rounds
trigger for Phase 6 is now armed.**

| round | Highs | source |
|---|---|---|
| 1 | 3 | original defects |
| 2 | 2 | round 1's own fixes |
| 3 | 2 | round 2's own fixes |
| **4** | **1** | **redesign 1's own gap** |

Redesign 2 is finished work. I attacked it at the level it deserved — a byte-level diff of a money
function, a forced-failure atomicity proof, live RLS and grant checks, a proof-from-SQL that a token
cannot settle twice, and an EXPLAIN of the query it exists to enable — and the only thing that fell out
is a one-line index/query mismatch that costs an operator latency, not money. It genuinely dissolves
the recurrence: the round-1→3 sequence was three refinements of a *report*, and this makes the *fact*
observable.

Redesign 1 is most of the way there. It converts three of four measured mutant shapes from
"detected by a text guard someone must keep sharpening" into "rejected by `tsc`, which already runs in
CI". That is the right direction and it should not be undone. But it left `attempts` unbranded and the
singleton writable, and the result is the **fourth consecutive round** in which a wrong serve budget
reaches a bounded call with every gate green. Severity is falling — round 1's mutant was an ordinary
expression at a call site, round 4's requires deliberately assigning to an exported constant — and the
fix is mechanical: `readonly` + `Object.freeze`, plus pinning the serve values against independent
literals the way the local path already is.

I do not think a third shape is wrong. Both redesigns are sound in their premise; redesign 1 was
applied to three of the four fields of the object it protects. Round 5 should be short and should
re-run exactly M1 and M3.

Two process observations, offered as leads rather than findings:
- The instrument that failed here is `expect(x).toEqual(SERVE_BUDGET)` — an assertion whose expected
  value is the object under test. That is not specific to this branch and would be cheap to grep for
  across the money suites.
- `create index if not exists` in a migration silently accepts a *differently defined* index of the
  same name. The live stack is in exactly that state right now.

**NOT CONVERGED**
