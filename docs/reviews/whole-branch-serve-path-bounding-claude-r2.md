# Whole-branch adversarial review — #46 serve-path bounding — Claude, ROUND 2

Branch `fix/serve-path-deadline` at `2098ebf`, base `master` = `1a7c076`. Own git worktree
(`.claude/worktrees/agent-a8b4be87e2dd79386`), isolated per the round-1 adjudication's process fix.

**Verdict: NOT CONVERGED** — 2 High, 1 Medium, 3 Low.

Both Highs are **introduced by round-1's own fixes**, which is the rate the brief told me to assume.

Gates run at HEAD: `npx tsc --noEmit` exit 0 · `npm test` **263 suites / 2647 tests** green (×2) ·
`npm run test:integration -- serve` **8 suites / 59 tests** green · `npm run test:integration --
serve-config-invariant reservation-release` **2 suites / 37 tests** green ·
`python3 scripts/check-docs.py` OK · **11 mutations run, all restored**, `git status --short` clean.

---

## High

### H-R2-1 — the round-1 H1 fix covered ONE of the four bounded call sites; the put timeout's VALUE is still unasserted, and the pre-fix double charge is still reachable

**Claim.** `lib/html-doc/serve-doc.ts:133` can be changed from `SERVE_PUT_TIMEOUT_MS` to any number
of the right type and nothing anywhere goes red — the exact defect round-1 graded H1, one argument
over.

```ts
// lib/html-doc/serve-doc.ts:133  [VERIFIED at HEAD]
    await writeModelEnvelopeWithin(SERVE_PUT_TIMEOUT_MS, principal, base, {
```

**MEASURED this round.** Replacing `SERVE_PUT_TIMEOUT_MS` with `120_000`:

| gate | result under the mutant |
|---|---|
| `npx tsc --noEmit` | **exit 0** |
| `npm test` | 263 suites / **2647 passed, 0 failed** |
| `npm run test:integration -- serve-doc-materialize serve-config-invariant …` | green |
| `tests/lib/html-doc/serve-bounded-import-guard.test.ts` (the NEW guard) | **passes** |

The new import guard passes by construction: it asserts the *identifier* `writeModelEnvelopeWithin`
is used rather than `writeModelEnvelope` `[VERIFIED: tests/lib/html-doc/serve-bounded-import-guard.test.ts:22-33]`.
It never looks at the argument. And every serve test drives a fake `BlobStore` whose `put` resolves
immediately `[VERIFIED: tests/lib/html-doc/serve-doc-mapping.test.ts:66]`, so the timeout is never
exercised at the call site.

**Why this is the same defect, not a new one.** Round-1 H1's lesson, in the branch's own commit
message: *"a required positional `ServeBudget` defends against OMISSION, never against a wrong value
of the right shape."* `writeModelEnvelopeWithin`'s `timeoutMs` is a **required positional
parameter of type `number`** `[VERIFIED: lib/html-doc/model-store.ts:65-66]`, with a docblock making
exactly the round-1 argument — *"`timeoutMs` is REQUIRED: an optional one would let the serve caller
silently restore the unbounded await this exists to remove"* `[VERIFIED: model-store.ts:62-63]`. The
fix asserted the value of the one argument the reviewer had named and stopped there. This is the
shape `docs/plugins.md` already names in another context: *"solving one instance and reading as if it
covered the class."*

**Count the class.** Inside the lease window (`case 'reserved': break;`, `serve-doc.ts:112`) there
are four bounded calls, each parameterised by a value that could be wrong:

| # | call site | bound | is the VALUE asserted at the call site? |
|---|---|---|---|
| 1 | `generateMagazineModelForServe(…, SERVE_BUDGET, …)` `:130` | budget object | **YES** — round-1's fix, `serve-doc-mapping.test.ts:198` |
| 2 | `writeModelEnvelopeWithin(SERVE_PUT_TIMEOUT_MS, …)` `:133` | 15 s | **NO** — this finding |
| 3 | `callRpcBounded(…, SERVE_SETTLE_RPC_TIMEOUT_MS, …)` `:187` | 5 s | no — mocked to 20 in the only test file that reaches it |
| 4 | `callRpcBounded(…, SERVE_RESERVE_RPC_TIMEOUT_MS, …)` `:83` | 5 s | no — see L-R2-3 (caught only by Jest's own timeout) |

This is **standing shape #6**: the promise *"every call inside the lease window is bounded to the
value the sum was built from"* is a negative property over a set of call sites, and the set was
never counted.

**Money.** With the put at 120 s the enforced work is `5 + 10 + (2×50 + 0.4) + 120 + (2×5) = 245.4 s`
against a lease floor of 161 s `[VERIFIED: supabase/migrations/0024_lease_covers_serve.sql:59]` and
the shipped default of 180 s `[VERIFIED: 0012_serve_model_charge.sql:22]`. The lease expires mid-put;
the reclaim clause in `reserve_serve_model` `[VERIFIED: 0020_reservation_release.sql:217-222]` admits
a **second paid producer** — 6¢ → 12¢, two charges, one document. That is the branch's entire thesis,
silently restored, with every gate green. Identical consequence to round-1 H1.

**Worse than a wrong number: the sum and the code disagree with nothing to say so.**
`SERVE_BOUNDED_MS` still computes `140_400` from `SERVE_PUT_TIMEOUT_MS = 15_000`
`[VERIFIED: lib/serve-budget.ts:74-80]` and `SERVE_FLOOR_SECONDS` still yields 161, so migration 0024
still declares a floor derived from a number the code no longer spends. `lib/serve-budget.ts`'s own
docblock names this as the Blocking class it was written to prevent: *"A term that is only *added* is
not a bound — an earlier draft carried a `SETTLE_SLACK_MS` that appeared in this sum and nowhere else,
and it was a Blocking finding"* `[VERIFIED: lib/serve-budget.ts:14-17]`. The mutant reproduces that
exact condition from the opposite direction: the sum is honest, the call site is not.

**What caller reaches it.** Every authenticated owner serving an uncached document:
`app/api/html/[id]/route.ts` → `serve-summary-core.ts:105` `resolveAndParse` → `resolveMagazineModel`
→ `:133`. `serve-summary-core.ts` is the only production caller
`[VERIFIED: grep -rn "resolveMagazineModel" lib/ app/ worker/`].

**Premise tags.** All `[VERIFIED]` at HEAD this round; the mutant table is a measurement.

**Fix.** Assert the value at the boundary, the same way H1 was fixed — the fake blob store already
records its calls, so capture the timeout the same way the budget is captured:

```ts
// tests/lib/html-doc/serve-doc-mapping.test.ts — alongside the SERVE_BUDGET assertion
it('bounds the model put with SERVE_PUT_TIMEOUT_MS itself', async () => { … });
```
Cheapest complete form: have `writeModelEnvelopeWithin` be reached through a jest spy on
`@/lib/html-doc/model-store` and assert `mock.calls[0][0]` `toBe(SERVE_PUT_TIMEOUT_MS)`. Do the same
for the two `callRpcBounded` timeouts, or state in `serve-budget.ts` why they are exempt. **Assert
the class, not the instance** — otherwise round 3 finds call site #3.

---

### H-R2-2 — the H3 fix moved the absent-vs-failed conflation one level up: `settleBounded`'s `false` means three different things, and the new `REFUND NOT APPLIED` alarm fires when the refund DID apply

**Claim.** `lib/html-doc/serve-doc.ts:156-158` asserts a fact the code cannot know. The alarm round-1
H3 was fixed to create has a false-positive mode on **exactly the path the retry exists for**.

```ts
// lib/html-doc/serve-doc.ts:156-158  [VERIFIED at HEAD]
    if (releaseToken && !await settleBounded(supabaseClient, releaseToken, released) && released) {
      console.error('[serve-model] REFUND NOT APPLIED — the owner was charged for a failed generation');
    }
```

`settleBounded` returns `false` in three distinct situations `[VERIFIED: serve-doc.ts:174-208]`:

| # | situation | did the refund apply? |
|---|---|---|
| a | attempt 1 returned `data:false` — stale/duplicate/forged token, or lease reclaimed | **no** |
| b | every attempt returned `!ok` (timeout / transport) | **unknown** |
| c | attempt 1 timed out CLIENT-side but COMMITTED server-side; attempt 2 sees the idempotent no-op | **YES — it applied** |

Only (a) is what the message claims. The retry loop runs *only* on the refund path
(`attempts = released ? SERVE_SETTLE_ATTEMPTS : 1`, `:178`), so (c) is reachable only where the money
is, and it is the case the second attempt was budgeted for.

**MEASURED.** I added a probe to `serve-doc-mapping.test.ts` (removed afterwards; worktree clean)
scripting settle attempt 1 to hang and attempt 2 to answer `{ data:false, error:null }` — the exact
pair the live database produces, pinned by an existing integration test:

```ts
// tests/integration/reservation-release.test.ts:452-454  [VERIFIED, ran green this round]
    const first  = await session.rpc('settle_serve_model', { p_token: token, p_released: true });
    const second = await session.rpc('settle_serve_model', { p_token: token, p_released: true });
    expect(first.data).toBe(true);
    expect(second.data).toBe(false);
```

Probe result:

```
PROBE errorLog calls: [["[serve-model] REFUND NOT APPLIED — the owner was charged for a failed generation"]]
```

The refund had applied. The ledger was correct. The alarm said money was lost.

**Why attempt 1 can commit after our timeout.** `callRpcBounded` races its own timer and calls
`ctrl.abort()` `[VERIFIED: lib/serve-rpc.ts:32-34]`; aborting the fetch does not roll back a
transaction PostgREST has already executed. This branch **already relies on that fact** in the
opposite direction — `serve-doc.ts:87-88`: *"TIMEOUT. The transaction is NOT rolled back, so what may
exist now is an EMPTY PAID LEASE"* — and backlog #28 is built entirely on it. The reserve path
reasons correctly about a committed-after-timeout RPC; the settle path, three lines of the same file
later, does not.

**The fix's own comment enumerates the causes and omits this one** `[VERIFIED: serve-doc.ts:190-202]`:
*"when the token is stale, duplicated, forged, or the lease was reclaimed while this attempt was
still running."* Missing: *or my own previous attempt already settled it*. The comment reasons about
`settle_serve_model`'s callers in general and not about `settleBounded`'s own second iteration.

**Standing shapes, both of them.** #1 — `false` now conflates *"the DB refused"* with *"I cannot tell"*
and with *"I already did it"*; round-1 H3 removed that conflation between `ok` and `data` and
reintroduced it one level up, in the return value. #2 — *what does this guard do when the caller is
merely SECOND?* The second iteration **is** the second caller, and the code answers it with a
rejection where a reconcile is available.

**The same defect, milder, on the keep path.** `serve-doc.ts:144-146` logs *"keep-settle did not
apply; the charge stands, the token was not cleared"* whenever `settleBounded` returns false —
including case (b), a bare timeout, where the settle may well have applied. Same assertion of an
unknown.

**Money.** The ledger is correct in case (c); nothing is over- or under-charged. The damage is to the
**instrument**: round-1 graded H3 High precisely because *"the refund mechanism can stop working
entirely in production and emit zero signal"*, and the deliverable of the fix was the signal. A
`console.error` that cries wolf on the retry path — the only path it monitors — is a signal an
operator learns to discount, which returns the system to the round-1 posture by a different route.
Symmetric defect, same grade.

**What caller reaches it.** Any owner whose generation fails with a positively-not-metered class-A
failure (429/503 before `gemini.ts:274` latches `metered`) while the settle RPC's first round trip
exceeds 5 s — i.e. a Gemini outage coinciding with Postgres latency, which are correlated by load.

**Fix.** Do not let one boolean carry three states. Minimal, no new mechanism:

```ts
for (let i = 0; i < attempts; i++) {
  const out = await callRpcBounded<boolean | null>(…);
  if (out.ok) {
    if (out.data === true) return true;
    if (i > 0) {
      // We already sent this token once and never learned the answer. `false` here means EITHER a
      // reclaim OR our own first attempt having committed — indistinguishable, so claim neither.
      console.warn('[serve-model] settle refused on RETRY — our own first attempt may have applied it');
      return true;                    // or a third outcome; do NOT claim the refund was lost
    }
    console.warn(`[serve-model] settle(released=${released}) REFUSED by the database …`);
    return false;
  }
  …
}
```
Returning a three-valued outcome (`applied` / `refused` / `indeterminate`) and logging `REFUND NOT
APPLIED` **only** on `refused` is the honest shape, and mirrors `RpcOutcome`'s own rule
`[VERIFIED: lib/serve-rpc.ts:16-18]`: *"a caller must not be able to collapse 'timed out' into
'returned an error' — they have different money consequences."* That rule was applied one function
down and not to this function's own return value.

---

## Medium

### M-R2-1 — after M1's retune, the migration floor's only anti-drift instrument lives outside CI, and the unit gate that IS in CI cannot see the drift that matters

`SERVE_FLOOR_SECONDS` is 161 `[VERIFIED: lib/serve-budget.ts:90 → 140_400 + 20_000 → ceil(160.4)]`,
and 0024's three literals are pinned to it by
`tests/integration/serve-config-invariant.test.ts:180-192` — **an integration test**, which
`docs/dev-process.md` lists under *"Not yet in CI: `test:integration` … Run these locally before
asking for a merge."*

The unit suite, which **is** in CI, pins only relations plus one ceiling:
`expect(SERVE_FLOOR_SECONDS).toBeLessThanOrEqual(180)` `[VERIFIED: tests/lib/serve-budget.test.ts:58-60]`.
Nothing in CI ties `SERVE_FLOOR_SECONDS` to the number the database enforces.

**Failure scenario.** An operator lowers `lease_ttl_seconds` to 161 — now legal, and the migration
advertises 161 as the floor. Later, `SERVE_ATTEMPT_TIMEOUT_MS` is retuned 50 s → 55 s:
`SERVE_FLOOR_SECONDS` becomes 171, the CI ceiling still passes (171 ≤ 180), 0024 still says 161, the
DB still permits a 161 s lease, and the work no longer fits it — the reclaim clause admits a second
paid producer. **6¢ → 12¢.** The only gate is a suite CI does not run.

M2's fix made the pin *complete* (three literals, measured below) without making it *reachable* by
the gate set that actually blocks a merge. Not introduced by the fix — but M1 moved the number, which
is the event that makes drift live, and the branch is the first thing to depend on the pin.

**What caller reaches it.** Any owner on an installation whose lease was tuned to the floor.

**Fix.** Add the floor↔migration assertion to the **unit** suite: the test only reads
`supabase/migrations/0024_lease_covers_serve.sql` off disk and needs no database
`[VERIFIED: serve-config-invariant.test.ts:181]`. Move it (or duplicate it) into
`tests/lib/serve-budget.test.ts` and it runs in CI on every push.

---

## Low

### L-R2-1 — the L2 fix's own comment claims a case the regex does not cover; L2 is half-fixed, and the record says fixed

`[VERIFIED: supabase/migrations/0024_lease_covers_serve.sql:26-28]`:

> A substring match on `'%lease_ttl_seconds%'` also drops constraints this migration has no business
> touching — an operator's upper bound (`lease_ttl_seconds <= 3600`), **or a multi-column CHECK whose
> other half is unrelated** — and nothing recreates them.

**MEASURED against the live Postgres** (`pg_get_constraintdef`-normalised text, not source text):

```
select 'CHECK ((lease_ttl_seconds >= 1))'                                   ~* 'lease_ttl_seconds[[:space:]]*>=';  -- t
select 'CHECK ((lease_ttl_seconds <= 3600))'                                ~* 'lease_ttl_seconds[[:space:]]*>=';  -- f
select 'CHECK (((lease_ttl_seconds >= 1) AND (max_serve_attempts >= 1)))'   ~* 'lease_ttl_seconds[[:space:]]*>=';  -- t
```

The upper bound now survives — that half of L2 is genuinely fixed. The **multi-column CHECK is still
dropped whole**, taking `max_serve_attempts >= 1` with it, and nothing recreates it. That was round-1
Claude's L2 example verbatim, and the adjudication recorded L2 as *"CONFIRMED — fixed"*.

Latent today: the live catalog has no multi-column CHECK naming `lease_ttl_seconds`
`[VERIFIED: pg_constraint on guardrail_config, 11 rows, this round]`, and `raise warning` fires at
`count > 1` `[VERIFIED: 0024:33-35]`, so it would not be silent. **Fix:** correct the comment to
claim only what is true, or drop by matching the whole constraint definition against the exact
lower-bound shape.

### L-R2-2 — spec §6's deploy runbook and the approved spec still say 156

`docs/superpowers/specs/2026-08-10-serve-path-deadline-design.md` states 156 in seven places
including the anti-drift rule at `:593` (*"The migration's literal `156` must equal
`SERVE_FLOOR_SECONDS`"*) and the operator-facing precondition at `:600,:606` (*"If any environment is
below 156, raise it first"*). `docs/superpowers/plans/2026-08-10-serve-path-bounding.md:1322` repeats
it as an unticked deploy checkbox. `python3 scripts/check-docs.py` reports **OK** — the doc gate does
not relate spec numbers to code.

Harmless operationally (0024's fix-up raises rows to 161 before `ADD CONSTRAINT`
`[VERIFIED: 0024:53-59]`), so an operator following the stale step still deploys successfully. The
cost is that the approved artifact — the human gate — now documents a floor the code contradicts, and
the next reader has no way to know which is current.

### L-R2-3 — the reserve timeout's call-site value is guarded by Jest's own per-test timeout, not by an assertion

**MEASURED:** `SERVE_RESERVE_RPC_TIMEOUT_MS` → `60_000` at `serve-doc.ts:83` turns
*'a reserve TIMEOUT returns busy and makes no Gemini call'* red — but red because the test exceeded
Jest's default 5000 ms, not because anything asserted the value. `serve-doc-mapping.test.ts` mocks
the constant to 20 ms `[VERIFIED: :20-24]`, so the call site's literal is what actually runs. Any
mutated value **below** ~4.5 s stays green. This is standing shape #4 — a negative test passing for
the wrong reason — and it is why call site #4 in H-R2-1's table reads "no". Same fix as H-R2-1.

---

## Round-1 fixes: genuinely fixed, or reworded?

| id | verdict | how established this round |
|---|---|---|
| **H1** budget VALUE unasserted | **GENUINELY FIXED — for the one call site it names.** Not a tautology, not vacuous | Re-ran round-1's exact mutation (`SERVE_BUDGET` → `{attempts:3, attemptTimeoutMs:60_000, countTokensTimeoutMs:10_000}`): **RED** at `serve-doc-mapping.test.ts:198`, `Expected attempts 2 / Received 3`. **Tautology attack failed:** the file mocks `@/lib/serve-budget` but spreads `jest.requireActual`, so `SERVE_BUDGET` is the real object and only the two RPC timeouts are shrunk `[VERIFIED: :20-24]` — the mutation still goes red. **Vacuity attack failed:** `mock.calls[0][2]` throws a TypeError if the wrapper is never called, so the test errors rather than passing. Import guard: `\bgenerateMagazineModel\b` **does** discriminate `generateMagazineModelForServe` — proven by the guard staying green while `serve-doc.ts:9,127` reference the wrapper twice; swapping `writeModelEnvelopeWithin` → `writeModelEnvelope` turns it **RED**. **BUT — the third way the brief asked about exists: H-R2-1** |
| **H2** residual traded for a missing log | **GENUINELY FIXED.** Strongest of the six | Three mutations, three reds on the one intended test: drop `elapsed …ms` → RED (`/elapsed \d+ms/`); drop `${MODEL_KEY(base)}` → RED (`models/a-title.json`); delete the whole `console.warn` → RED. **Fires on the real path:** same function, timer created unconditionally, called from `serve-doc.ts:133`. **Cannot be outrun:** `console.warn` is synchronous and precedes `reject()` inside the same callback `[VERIFIED: model-store.ts:85-89]`. **No spurious log on success:** `clearTimeout` in `finally` `[VERIFIED: :99-101]`. Leakage is the document base name in a server log — the content the spec explicitly ordered |
| **H3** DB-refused settle read as settled | **THE STATED DEFECT IS FIXED; THE FIX INTRODUCED H-R2-2** | `out.data === true` is **empirically correct**: `reservation-release.test.ts` asserts `.toBe(true)`/`.toBe(false)` against the live database and ran green this round (37 tests) — postgrest returns real JS booleans for this scalar RPC, not `"true"`, not a row array. `settle_serve_model` cannot return SQL NULL: every path is an explicit `return true`/`return false` `[VERIFIED: 0020:277-298]`. The "deterministic refusal → do not retry" claim is **true for attempt 1** and **false for attempt 2** — see H-R2-2, measured |
| **M1** sum counted one settle, path runs two | **GENUINELY FIXED.** Every term re-derived at HEAD | `5_000 + 10_000 + 2×50_000 + 400 + 15_000 + 2×5_000 = 140_400`; `+20_000` → `161`. Terms re-verified against the code that applies them: reserve `:83`; countTokens via `budget.countTokensTimeoutMs` → `assertMagazineInputWithinCap`; attempts via `budget.attempts - 1` as generateJson **retries** `[VERIFIED: gemini.ts:568]` → 2 attempts; backoff `400 × 2⁰` over 1 gap; put `:133`; settle × `SERVE_SETTLE_ATTEMPTS`. `settleBounded`'s `attempts` **is** tied to the constant `[VERIFIED: serve-doc.ts:178]`. 161 ≤ 180 with 19 s headroom, asserted in CI. Only the docs still assume 156 (L-R2-2). Caveat: M-R2-1 |
| **M2** pin covered 1 of 3 literals | **GENUINELY FIXED.** All three literals AND the population are load-bearing | Three mutations, three reds: delete the fix-up → population assertion RED (`Expected -2 / Received +0`); retune only the `check` → RED naming `"where":"check"`; retune only the `set` → RED naming `"where":"set"`. The regexes do not over-match the file's own prose: `lease_ttl_seconds <= 3600` at `:27` fails `<\s*(\d+)`, and `lease_ttl_seconds[[:space:]]*>=` at `:32,:39` fails `>=\s*(\d+)\s*\)` — verified by the population landing on exactly `['check','set','where']` |
| **L2** sweep dropped by substring | **PARTIALLY FIXED — see L-R2-1** | **The half the adjudication cared about holds, verified on a freshly-migrated database:** after the local stack was reset and re-migrated 0001→0024 mid-session, `pg_constraint` on `guardrail_config` holds **exactly one** `lease_ttl` check — `CHECK ((lease_ttl_seconds >= 161))` — so 0012's `>= 1` **was** swept by the new regex against Postgres's normalised text. The operator's upper bound now survives (measured `f`). The multi-column case does **not** (measured `t`), contradicting the fix's own comment |

---

## What I attacked and why it held

1. **The H1 assertion as a tautology** (the brief's sharpest question). The mapping file mocks
   `@/lib/serve-budget`. It does **not** neutralise the assertion: the mock spreads
   `jest.requireActual` and overrides only `SERVE_RESERVE_RPC_TIMEOUT_MS` / `SERVE_SETTLE_RPC_TIMEOUT_MS`,
   neither of which feeds `SERVE_BUDGET` `[VERIFIED: lib/serve-budget.ts:103-107]`. Measured red.
2. **A different caller of `resolveMagazineModel`.** There is one production caller,
   `serve-summary-core.ts:105`; the route reaches it through `resolveAndParse` and nothing else calls
   `reserve_serve_model`. So the import guard's single-file scope is not obviously too narrow *today*.
3. **`generateMagazineModel` reached by alias or namespace.** Both are caught: `import { x as y }`
   and `store.generateMagazineModel` each leave the banned identifier on a non-comment line, and
   `\b` matches after `.`. And a swap to a *different* generation path additionally errors the H1
   assertion (`mock.calls[0]` undefined). The residual hole is a **new** unbounded sibling added to
   `model-store.ts` (e.g. `writeModelEnvelopeFast`), which the word-boundary regex would not match
   and no other test covers — speculative, so recorded here rather than filed.
4. **`SERVE_BOUNDED_MS`'s completeness.** Every blob read on the lease path re-checked at HEAD:
   `readFreshMagazineModel` `:61` and `tryGet` `:75` run **before** the reserve; the `in_flight`
   re-read `:100` and `readTitleStableModel` `:107` run on branches where `release_token` is null and
   no lease is held. No unbounded call sits inside the window the sum claims to cover. Round-1's
   finding 7 re-verified, not inherited.
5. **`settle_serve_model` returning NULL.** Ruled out by reading every path of `0020:277-298` — each
   terminates in an explicit `return true` or `return false`; there is no fall-through, so the
   `boolean | null` type is defensive rather than reachable, and `=== true` cannot misread a real
   settle. Confirmed empirically by the integration suite's `.toBe(true)`.
6. **Whether the M2 regexes over-match the migration's own prose.** They do not — the population
   assertion lands on exactly three entries, which is itself the proof.
7. **Whether the L2 regex misses 0012 on a fresh database.** It does not — measured on a database
   that had just been re-migrated from scratch this session (see the process note below), where
   exactly one lease-TTL constraint survives.
8. **Mutations run this round — 11, all restored, `git status --short` clean:**

| mutation | expected | result |
|---|---|---|
| `SERVE_BUDGET` → `{3, 60_000, 10_000}` at `serve-doc.ts:130` | H1 assertion red | **RED ✓** |
| `writeModelEnvelopeWithin` → `writeModelEnvelope` | import guard red | **RED ✓** |
| **`SERVE_PUT_TIMEOUT_MS` → `120_000` at `:133`** | **anything at all** | **GREEN — H-R2-1** |
| `SERVE_RESERVE_RPC_TIMEOUT_MS` → `60_000` at `:83` | an assertion | RED, but by Jest timeout — L-R2-3 |
| settle attempt 1 hangs + attempt 2 `data:false` (probe) | no false alarm | **`REFUND NOT APPLIED` — H-R2-2** |
| drop `elapsed …ms` from the put log | model-store red | **RED ✓** |
| drop `${MODEL_KEY(base)}` from the put log | model-store red | **RED ✓** |
| delete the whole `console.warn` in the put timer | model-store red | **RED ✓** |
| delete 0024's data fix-up | population assertion red | **RED ✓** |
| retune only 0024's `check` literal | pin red naming `check` | **RED ✓** |
| retune only 0024's `set` literal | pin red naming `set` | **RED ✓** |

---

## Process note — the shared stack was reset under me mid-review, and it is worth recording

My first `npm run test:integration` failed in `globalSetup` with
`relation "storage.buckets" does not exist` while applying **0007**. Investigating, the shared
database held **6** applied migrations and **3** public tables; ninety seconds later, without any
action from me, it held **24** and **12**, and another agent's integration traffic was live in the
storage container's log throughout. A concurrent reset was in flight and my run landed inside it.

The round-1 adjudication had already recorded the sibling symptom (*"that reset had pulled a new
edge-runtime image and was still restarting containers"*), and this repo's memory carries
*"an instrument that edits the repo corrupts its peers"*. Round 2 gave each reviewer its **own git
worktree** — which fixed the file-level hazard — while the **database stayed shared**, and
`tests/integration/global-setup.ts` runs `supabase migration up` on every invocation. Worktree
isolation does not isolate the stack. It cost me one bad run and could as easily have produced an
unattributable red I charged to the branch.

Also worth a line: a fresh worktree has no `.env.test.local`, so the integration suite refuses to run
until it is copied from the main checkout. Not a defect, but it belongs in the round-N brief.

**No finding here is charged to the branch on the strength of a run made during that window.** Every
gate result and every mutation above was produced after the stack settled at 24 migrations, and the
full unit suite and the `serve` integration suites were re-run green at HEAD immediately before this
document was written.

---

## Verdict

**NOT CONVERGED** — H-R2-1 and H-R2-2.

Neither is a rewording of a round-1 finding and neither existed before `2098ebf`: **both were
introduced by round-1's own fixes**, at the rate the brief predicted. H-R2-1 is the more serious —
it restores the same 6¢→12¢ double charge round-1 H1 restored, through the adjacent argument at the
adjacent call site, with `tsc` at exit 0 and 2647 unit tests green. The lesson round 1 wrote down
was applied to the instance it was learned on and not to the class, which is the failure mode this
repo has now measured three times.

Both fixes are small and local — assert three more values at the boundary; stop letting one boolean
carry three states. Neither is new design, so round 3 should verify these two and hunt what they
introduce, not restart the sweep.
