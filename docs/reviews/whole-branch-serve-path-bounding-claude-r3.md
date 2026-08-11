# Whole-branch review #46 — serve-path bounding — ROUND 3 (Claude, isolated worktree)

Base `master` = `1a7c076` · HEAD = `4872948` · reviewed in a dedicated worktree, shared Supabase
stack **read only** (`begin; … rollback;` for the one schema experiment; no reset, no push).

**Gate status measured at HEAD, before any mutation:**

| gate | result |
|---|---|
| `npx tsc --noEmit` | exit 0 |
| `npm test` | **263 suites / 2653 tests, all green** |
| `npm run test:integration -- "settle-rpc-shape\|serve-config-invariant\|serve-doc-materialize\|serve-model-unreadable"` | 4 suites / 22 tests green |
| `npm run test:integration -- "html-download\|pdf-cloud\|share-route\|serve"` | 11 suites / 99 tests green |
| `git status --short` after every mutation | clean |

---

## Findings

### H-R3-1 (High) — the settle-outcome signal cannot be acted on: `indeterminate` names a table that records no settle, and none of the four money alarms carries an identifier

**Claim.** Round 2 made the settle outcome three-valued so an ambiguous refund would be *reported
rather than mis-alarmed*, and told the operator what to do about it. The instruction points at
`ledger_audit`, which by construction contains no record of a settle — and the message carries no
owner, doc key, day or token, so there is nothing to look up in any table.

**Code, quoted at HEAD.**

`lib/html-doc/serve-doc.ts:163-173`
```ts
    if (releaseToken) {
      const outcome = await settleBounded(supabaseClient, releaseToken, released);
      if (released && outcome === 'refused') {
        console.error('[serve-model] REFUND NOT APPLIED — the owner was charged for a failed generation');
      } else if (released && outcome === 'indeterminate') {
        console.warn(
          '[serve-model] refund outcome UNKNOWN — a settle attempt went unanswered and may have '
          + 'committed; reconcile against ledger_audit rather than assuming either way',
        );
      }
    }
```

`supabase/migrations/0020_reservation_release.sql:269-297` — the *entire* body of
`settle_serve_model`. Every `ledger_audit` write it can perform:
```sql
  update serve_model_charge
     set reserved_cents = 0, release_token = null
   where owner_id = v_owner and release_token = p_token and reserved_cents >= v_cfg.magazine_est_cents
   returning day into v_day;
  if not found then return false; end if;          -- stale/duplicate/forged token → no-op (idempotent)
  if p_released then
    update serve_owner_budget set spent_cents = spent_cents - v_cfg.magazine_est_cents
     where owner_id = v_owner and day = v_day and spent_cents >= v_cfg.magazine_est_cents;
    if not found then
      insert into ledger_audit(day, kind, expected_amt, note, at)
        values (v_day, 'release_underflow', ...);
    end if;
    ...
```
`[VERIFIED: supabase/migrations/0020_reservation_release.sql:281,287,294]` — the only inserts are
`release_underflow`, i.e. the *decrement failed* case. A refund that applied cleanly writes **no
row**. A settle that never applied writes **no row**.

`[VERIFIED: live catalog]` `\d public.ledger_audit` → `(id, day, kind, expected_amt, note, at)`;
`\d public.serve_model_charge` → `(owner_id, doc_key, day, lease_expires_at, attempt_count,
reserved_cents, release_token)`. Neither carries a settled-at or a settle log.
`grep -n release_underflow supabase/migrations/0020_reservation_release.sql` → **every** `ledger_audit`
insert in the repo is that one kind.

**Failure scenario.** Owner serves a doc. Reserve succeeds (6¢ held on `serve_owner_budget` +
`spend_ledger`). Gemini returns 429 → `classifyGeminiFailure` → `'release'`
`[VERIFIED: lib/gemini-failure.ts:100-104]`, `billing.metered` false (no body ever arrived,
`gemini.ts:274`), release gate **open in production** — `const RELEASE_VERIFIED = true;`
`[VERIFIED: lib/gemini-failure.ts:41]`, opened 2026-07-19. So `released === true`. The first settle
round trip exceeds `SERVE_SETTLE_RPC_TIMEOUT_MS`; the retry returns the idempotent `false`;
`settleBounded` correctly returns `'indeterminate'`. The operator sees:

> `[serve-model] refund outcome UNKNOWN — … reconcile against ledger_audit rather than assuming either way`

They query `ledger_audit`. It is empty for that day, which is equally consistent with *the refund
applied* and with *nothing settled at all*. The one row it could contain (`release_underflow`)
resolves only a third sub-case. The reconciliation named cannot distinguish the two states the
warning exists to flag.

The state that *would* answer it is `serve_model_charge` — `release_token IS NULL AND
reserved_cents = 0` means our settle landed — and that table is keyed `(owner_id, doc_key, day)`
`[VERIFIED: live catalog, serve_model_charge_owner_id_doc_key_day_key]`. **The log line contains
none of those three.** Nor do the siblings: `:166` `REFUND NOT APPLIED — the owner was charged`
(which owner? which doc? 6¢ or 150¢?), `:147` `keep-settle ${outcome}`, `:90` `reserve timed out —
possible empty paid lease`. `[VERIFIED: grep -n 'console\.(error|warn)' lib/html-doc/serve-doc.ts →
90, 147, 166, 168, 238, 245]` — not one carries `principal`, `base`, `videoId`, `playlistId` or the
token.

**What caller reaches it.** `resolveMagazineModel`'s catch path — the production caller is
`serve-summary-core.ts`. Reachable today: the release gate is open, so `released === true` is a live
state, not a flag-disabled one.

**Money.** 6¢ per occurrence, permanently undeterminable. Same unit as the accepted backlog #28
residual — but #28 was accepted *knowing* the money was stranded; this one is accepted on the
premise that it is recoverable, and it is not.

**Shape — and this is why it is a High and not a Medium.** It is round-1 **H2** exactly: *a residual
accepted because it would be observable, where the observability does not deliver the fact.* H2 was
graded High and confirmed. The `indeterminate` half of this was introduced by the round-2 fix; the
missing-identifier half is original and survived two prior rounds.

**Proposed fix.** Two options; the second is the one I would take.

- *Minimum.* Put `owner`, `base`/`doc_key`, `day` and the token in all four messages, and name
  `serve_model_charge`, not `ledger_audit`. Cheap, and only conclusive inside the ~161s lease
  window (after expiry a later reserve overwrites `release_token`, `0020:251-254`).
- *Durable, and it dissolves the recurring finding.* Have `settle_serve_model` write a `ledger_audit`
  row on **every** settle — `kind = 'serve_settle'`, `note = token || ':' || released`. Then
  `indeterminate` stops being an unfalsifiable log and becomes a *resolvable* state: one read answers
  it, and a future retry could answer it in code. See the escalation section — this is the whole of
  the redesign I am recommending.

---

### M-R3-1 (Medium) — the `anAttemptMayHaveCommitted` latch on `reason: 'error'` is not load-bearing (MEASURED)

**Claim.** The round-2 fix sets the latch for **both** `timeout` and `error`
(`lib/html-doc/serve-doc.ts:244`, `anAttemptMayHaveCommitted = true;` placed after the `if (out.ok)`
block, so it fires on either `!ok` reason). The brief asks whether `error` is really a
may-have-committed case. It is defensible — a PostgREST `error` also covers a transport failure
*after* the server committed — but **no test holds it there.**

**Measurement.** Mutation: `anAttemptMayHaveCommitted = true;` →
`if (out.reason === 'timeout') anAttemptMayHaveCommitted = true;`. `tsc` exit 0, and
`serve-bounded-import-guard | serve-doc-mapping | serve-budget | gemini-serve-budget` →
**4 suites / 34 tests, all green** (baseline is the same 34). Restored; `git status --short` clean.

**Consequence if it drifts.** Attempt 1 fails deterministically (`settle_serve_model:
unauthenticated`, a PGRST schema-cache miss after a signature change, an RLS denial — none of which
commit anything), attempt 2 answers a genuine `false`. Today: `indeterminate`, warn. Under the
mutation: `refused`, and `REFUND NOT APPLIED` fires — which for that input is the *correct* alarm.
Both readings are arguable; the point is that the branch's chosen reading is unpinned, and round 1's
own lesson was that an unpinned decision is one edit from being reverted.

**Caller.** Same as H-R3-1. **Fix.** One test in `serve-doc-mapping.test.ts`: attempt 1 returns a
postgrest `{ data: null, error: {...} }`, attempt 2 returns `false`, assert `refund outcome UNKNOWN`
and *not* `REFUND NOT APPLIED`.

---

### M-R3-2 (Medium) — a failed KEEP settle on the THROW path is silent, while the identical event on the success path is logged

**Claim.** `lib/html-doc/serve-doc.ts:163-173`: both branches are guarded by `released &&`. When
`released === false` — the **common** catch case (metered failure, or any non-429/503 class, or an
`ourSignal` abort → `'keep'`, `lib/gemini-failure.ts:96`) — a `refused` or `indeterminate` settle
produces **no output at all**. Compare the success path, `:144-149`, which logs
`keep-settle ${outcome}` for exactly the same event and calls it "an infrastructure signal worth
seeing".

**Consequence.** `serve_model_charge` keeps a live `release_token` and `reserved_cents = 6` until
lease expiry, invisibly. Not money loss (a later reserve `set`s, not `+=`s, `0020:251-254`) — but it
is the same infrastructure signal, suppressed on the path where failures actually cluster.

**Attribution.** Round 1 introduced the asymmetry (`… && released` at the end of the old
conditional); round 2 restructured this exact block into three branches and preserved it. **Fix:**
an `else if (outcome !== 'applied')` logging `keep-settle ${outcome}` on the catch path too.

---

### L-R3-1 (Low) — the "no numeric literals" rule cannot see exponential or hex literals

`tests/lib/html-doc/serve-bounded-import-guard.test.ts:101`
```ts
    const literals = [...code.matchAll(/(?<![\w.])(\d[\d_]*)(?![\w])/g)]
```
`12e4` never matches (`\d[\d_]*` takes `12`, then `(?![\w])` fails on `e`; backtracking fails the
same way). `0x1D4C0` never matches (`0` then `x` is `\w`; `1` is preceded by `x`, blocked by the
lookbehind). `1.5` matches only as `1` and is filtered out.

**Measured.** Mutation: `writeModelEnvelopeWithin(SERVE_PUT_TIMEOUT_MS,` →
`writeModelEnvelopeWithin(12e4,` — the literal rule stayed **green**; the failure came from rule 2
(`mustContain: ['SERVE_PUT_TIMEOUT_MS']`). So the belt worked and the braces did not. Rule 1's job
is to cover code rule 2's table does not yet name, which is precisely where the hole bites.

**Fix.** `/(?<![\w.$])(0x[0-9a-f]+|\d[\d_]*(?:\.\d+)?(?:e[+-]?\d+)?)/gi`.

---

### L-R3-2 (Low) — the class guard pins syntactic call sites, not executed invocations

`callArgs` counts textual call sites (`…:107-116`). Wrapping the put in a loop keeps the count at 1,
keeps `SERVE_PUT_TIMEOUT_MS` as the argument, and adds no forbidden literal:

```ts
for (let i = 0; i < SERVE_SETTLE_ATTEMPTS; i++) await writeModelEnvelopeWithin(SERVE_PUT_TIMEOUT_MS, …
```

**Measured.** `tsc` exit 0; the import guard stayed **green**; the red came from a behaviour test —
`serve-doc-mapping.test.ts` › *"reserved → generateMagazineModel IS called, model upserted"*. So the
sum's per-call multiplicities are protected by luck, not by the guard that claims to assert the
class. Note `settleBounded` already **is** such a loop, and stays correct only because it reuses the
same `SERVE_SETTLE_ATTEMPTS` the sum multiplies by (`serve-budget.ts:80`, `serve-doc.ts:210`).

**Fix.** No code change needed today — a sentence in the guard header stating that per-call
*multiplicity* is the behaviour tests' job, and an assertion that `settleBounded`'s loop bound is
`SERVE_SETTLE_ATTEMPTS` itself.

---

### L-R3-3 (Low) — `out.data === null` is reported as a database refusal

`lib/html-doc/serve-doc.ts:220-242`: `callRpcBounded<boolean | null>` deliberately types `null`
("postgrest types data as null on its failure branch … the same absent-vs-failed conflation this
function exists to remove"), and then every non-`true` value falls into the branch that warns
`REFUSED by the database — token stale, duplicated, or the lease was reclaimed`. `null` is *no
answer*, not a refusal — the same conflation one value over. I could not reach it against the live
client (the new integration pin measures only `true` and `false`, and both are correct), so: Low.
**Fix:** `if (out.data === false) { …refused }` and let anything else fall through to
`'indeterminate'`.

---

## What I attacked and why it held

Listed because a CONVERGED (or a short finding list) with no attack surface is not usable as a gate.

1. **Is `SERVE_COUNT_TOKENS_TIMEOUT_MS` a real bound, or a second `SETTLE_SLACK_MS`?** This was my
   best candidate for a Blocking: `serve-budget.ts:14-17` says a term that is only *added* is not a
   bound, and the tests only assert the option is **passed**, never that it is **honored**. Traced
   the installed SDK: `GenerativeModel.countTokens` merges the options
   (`node_modules/@google/generative-ai/dist/index.js:1410-1421`) → `countTokens(...)` (`:1293`) →
   `makeModelRequest` → `constructModelRequest` → `buildFetchOptions`, which does
   `setTimeout(() => controller.abort(), requestOptions.timeout)` and `fetchOptions.signal =
   controller.signal` (`:441-454`). It is a real bound on the same code path `generateContent` uses.
   **Held.**
2. **Does the sum equal the enforced work?** Enumerated every network call reachable while the paid
   lease is held: reserve RPC 5s · countTokens 10s · ≤2 × generateContent 50s (`gemini.ts:273`) ·
   one 400ms backoff gap — `baseDelayMs * 2 ** attempt` guarded by `if (attempt < retries)`
   (`gemini.ts:279-281`), so exactly one gap at `attempts = 2` · blob put 15s · ≤2 × settle RPC 5s.
   = **140.4s**, matching `SERVE_BOUNDED_MS`; +20s margin → 161. **No sixth call.** The two reads
   before the reserve (`readFreshMagazineModel`, `blobStore.tryGet`) are outside the lease. **Held.**
3. **The "different file" hole in the class guard** — bounded calls made from `lib/gemini.ts` rather
   than `serve-doc.ts`. All four budget fields are pinned *by value* in
   `tests/lib/gemini-serve-budget.test.ts`, and the local path is pinned separately at 3 × 60s.
   Mutation `budget ? budget.attemptTimeoutMs : undefined` → `undefined` went **red**. **Held.**
4. **Constant swap between the two RPCs** (every argument is still "a constant"): giving the settle
   site `SERVE_RESERVE_RPC_TIMEOUT_MS` went **red** on rule 2. **Held.**
5. **The constraint sweep, against the live catalog** — not source SQL. In `begin; … rollback;` I
   added four constraints and ran the round-2 sweep verbatim. Dropped: `>= 30` and our own `>= 161`.
   **Spared, each with its own warning:** `((lease_ttl_seconds >= 1) AND (max_serve_attempts >= 1))`,
   `((lease_ttl_seconds >= 1) OR (lease_ttl_seconds IS NULL))`, `(lease_ttl_seconds <= 3600)`.
   Also `show standard_conforming_strings` → `on`, so `\y` reaches the regex engine intact.
   **L-R2-1 held.** (Sparing an `OR` form is safe: ours is added alongside and the stricter wins.)
6. **The NULL hole in the floor** — a `CHECK (col >= 161)` passes on NULL and
   `where col < 161` skips NULL. `lease_ttl_seconds` is `NOT NULL DEFAULT 180`
   `[VERIFIED: information_schema.columns]`. **Not reachable. Held.**
7. **The put-timeout refund hazard** — could a slow-but-successful put be refunded? No:
   `writeModelEnvelopeWithin` only runs after generation succeeded, and success latches
   `billing.metered = true` at `gemini.ts:274`, so `released` is false. **Held.**
8. **Floor drift** — `SERVE_MARGIN_MS` 20_000 → 21_000 and the migration's `set` literal 161 → 162
   each went **red** on the relocated unit pin. **M-R2-1 held.**
9. **`process.cwd()` under the unit config** — both the new pin and the pre-existing import guard use
   it; `npm test` and `jest.integration.config.ts` both run from the repo root. Held for every
   invocation I could produce. I did not test an IDE runner with a different cwd; noting it rather
   than claiming it.
10. **L-R2-2 stale `156`** — `grep -n '\b156\b'` over the spec, the plan, `lib/`, `tests/` and
    `supabase/`: zero hits (two unrelated `:156` line references in `cloud-sync`). **Held.**
11. **Is the H-R2-2 fix load-bearing at all?** Deleting `if (anAttemptMayHaveCommitted) return
    'indeterminate';` → **red**. Setting `attempts` to 1 unconditionally → **red** (2 tests).
    **Held.**

All mutations restored; `git status --short` clean.

---

## Round-2 fixes: genuinely fixed, or reworded?

| id | verdict | evidence |
|---|---|---|
| **H-R2-1** class guard for the budget arguments | **Genuinely fixed** — with two holes | The value, the swap and the population are all really asserted (mutations 1, 2, 4 red). It is a class assertion, not four instance assertions. But it is a class over *arguments at textual call sites*: it cannot see exponential/hex literals (L-R3-1) and cannot see invocation multiplicity (L-R3-2). Both measured, both Low |
| **H-R2-2** three-valued `SettleOutcome` | **Genuinely fixed as a type; NOT fixed as a signal** | The taxonomy is right and load-bearing (deleting the `indeterminate` branch goes red). The `false`-means-three-things conflation is really gone. But the *deliverable* of H3 was a trustworthy, actionable signal, and the third value's action is a reconciliation the schema cannot support and a message with no identifier — **H-R3-1**. The latch's `error` half is unpinned — **M-R3-1**. The `null` case is still read as a refusal — **L-R3-3** |
| **M-R2-1** floor pin moved to the unit suite | **Genuinely fixed** | It now runs under `npm test` (CI). Fails for the right reasons: mutations 5 and 6 each red, and the population assertion still fires if a literal is deleted. Comment-stripping is correct — it measures SQL, not prose |
| **L-R2-1** sweep spares compound constraints | **Genuinely fixed** | Measured against the live catalog's normalised `pg_get_constraintdef`, in a rolled-back transaction: AND / OR / upper-bound all spared **and warned**, simple lower bounds dropped. `\y` is intact under `standard_conforming_strings = on` |
| **L-R2-2** 156 → 161 | **Genuinely fixed** | Zero stale occurrences anywhere that matters |
| **L-R2-3** reserve mutation red only via Jest's clock | **Genuinely dissolved** | Confirmed: the mutation now fails on rule 2's assertion, not on a 5s timeout |

---

## Escalation verdict

`review-method.md`: *"If a component produces findings caused by the PREVIOUS round's fixes in two
consecutive rounds, it escalates from FIX to REDESIGN."*

**The trigger has fired — and the component it fired on is not the one the branch is named after.**

Answering the question directly: **this is a converging defect stream on the bounding mechanism, and
a wrong shape on the settle-outcome signal.** Those are two different components that happen to live
in one file, and grading them together is what would produce the wrong decision here.

**The bounding mechanism has never produced a finding.** Not in round 1, not in round 2, not in
round 3. The static sum, the required-positional-parameter boundaries, the migration floor and the
live constraint have absorbed every mutation three reviewers have aimed at them — I ran nine more
this round and every one that mattered went red. Round 1's H1 and round 2's H-R2-1 were both
findings about the **instrument** (no test asserted the call site; then, the test asserted one site).
That is a converging stream by any reading: instance → class, and the class assertion holds against
the two shapes round 1 would have missed. The residual holes I found in it are Low and cosmetic.

**The settle-outcome signal has produced a High in all three rounds, and the reason is structural.**

- Round 1 H3: a boolean read transport success as "settled".
- Round 2 H-R2-2: the fix's `false` then meant three things, and the alarm fired on the wrong one.
- Round 3 H-R3-1: the fix's third value points the operator at a fact that **does not exist
  anywhere**.

Each round refined the *vocabulary of the report*: one bit → three values → three values plus
guidance. **No round added the missing thing, which is not a vocabulary at all.** There is no durable
record of whether a settle applied. `settle_serve_model` mutates two counters and returns a scalar;
`ledger_audit` records only the underflow exception; `serve_model_charge` is overwritten by the next
reserve. So the client is being asked to *infer* a durable money fact from a transient observation it
provably cannot make, and every round has answered that by describing the uncertainty more precisely.
That is why the same finding keeps reappearing one level up: **the taxonomy was never the defect.**

Note the sibling: this project already has the `two-mechanisms-for-one-concern` and
`gates-detect-defects-not-design` lessons, and the second one applies exactly. "Is this correct?" is
local and always patchable — three rounds have patched it correctly three times.

### The redesign, stated concretely — it is one migration, not a branch rewrite

Make the settle answer **durable**, so it can be read rather than inferred:

```sql
-- inside settle_serve_model, after the `update … returning day into v_day` succeeds:
insert into ledger_audit(day, kind, expected_amt, note, at)
  values (v_day, 'serve_settle', case when p_released then v_cfg.magazine_est_cents else 0 end,
          p_token::text || ':' || p_released::text, now());
```

What that buys, immediately:

- `indeterminate` becomes **resolvable**: one indexed read on `note` answers "did my token settle?".
  The operator instruction becomes true, and could later become code — a third attempt that *reads*
  instead of guessing.
- `REFUND NOT APPLIED` becomes attributable when the identifiers are added alongside (H-R3-1's
  minimum fix), which the same edit should carry.
- The three-valued type stops needing to carry operator guidance in prose, so the thing that has
  been rewritten three times stops being the load-bearing artifact.
- **It dissolves the recurrence rather than patching its next instance** — which is the test this
  project's own escalation rule exists to force.

### My recommendation, and the honest counter-argument

**Escalate the SIGNAL, not the branch.** Round 4 should be a design pass on one question — *how does
anyone learn whether a settle applied?* — scoped to `settle_serve_model` and the four log lines in
`serve-doc.ts`. Not a redesign of serve-path bounding, which is the part that works.

The counter-argument, stated plainly because it is not weak: three consecutive rounds of Highs in one
component **is** the situation the rule was written for, and a reviewer proposing a narrower
escalation than the rule specifies is doing exactly what the rule was written to prevent. If the
coordinator reads my scoping as softening, take the rule at face value and run the full design
review — I would not argue against it. What I *would* argue is that the redesign it lands on will be
the migration above, and that the bounding constants, the required-parameter boundaries and the lease
floor should come out of it unchanged.

---

**NOT CONVERGED** — 1 High (H-R3-1), 2 Medium, 3 Low.
