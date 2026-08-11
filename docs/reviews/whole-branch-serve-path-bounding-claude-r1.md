# Whole-branch adversarial review — #46 serve-path bounding — Claude, ROUND 1

Branch `fix/serve-path-deadline`, `1a7c076..b9dab35`. First review this code has had of any kind.

**Verdict: NOT CONVERGED** — 3 High, 3 Medium, 3 Low.

Gates run this round: `npx tsc --noEmit` exit 0 · `npx jest` 262 suites / 2638 tests (×5 runs, see
the note at the end about one red) · `npm run test:integration` on the 7 affected suites, green ·
`scripts/check-docs.py` OK · 5 mutation checks, all restored · `git status --short` clean apart from
two peer reviewers' untracked docs.

---

## High

### H1 — the serve call site's budget VALUE is unasserted; the pre-fix configuration compiles and every gate stays green

**Claim.** `lib/html-doc/serve-doc.ts:129` can be changed to the exact configuration this branch
exists to remove, and nothing anywhere goes red.

**MEASURED.** Replacing

```ts
      SERVE_BUDGET,                                   // REQUIRED — cannot be omitted
```

with `{ attempts: 3, attemptTimeoutMs: 60_000, countTokensTimeoutMs: 10_000 }`:

| gate | result under the mutant |
|---|---|
| `npx tsc --noEmit` | exit 0 |
| `npx jest tests/lib` | 184 suites / **1786 passed**, 0 failed |
| `npm run test:integration` (7 serve suites) | 7 suites / **75 passed**, 0 failed |

**Why every test misses it.** `[VERIFIED: tests/lib/gemini-serve-budget.test.ts:61-64]` calls
`generateMagazineModelForServe([...], 'en', SERVE_BUDGET, { caps: TEST_CAPS })` **directly** — it
proves the wrapper honours whatever budget it is handed, never that `serve-doc.ts` hands it
`SERVE_BUDGET`. And every file that exercises `resolveMagazineModel` mocks `@/lib/gemini` with a
delegate that **discards the budget argument**:

```ts
// tests/lib/html-doc/serve-doc-mapping.test.ts:34-35 (identical in serve-doc-materialize.test.ts,
// serve-model-unreadable.test.ts)
generateMagazineModelForServe: jest.fn((sections: unknown, language: unknown, _budget: unknown, opts: unknown) =>
  (generateMagazineModel as unknown as (a: unknown, b: unknown, c: unknown) => unknown)(sections, language, opts)),
```

`html-download.test.ts`, `pdf-cloud.test.ts` and `share-route.test.ts` go further —
`jest.fn(() => generateMagazineModel())` ignores all four arguments.

**What caller reaches the state.** Every authenticated owner serving an uncached document, via
`app/api/html/[id]/route.ts:84` → `serve-summary-core.ts:104` → `resolveMagazineModel`.

**Money.** With 3×60s the enforced work is `5 + 10 + 180 + 1.2 + 15 + 5 = 216.2s` against a lease
whose floor `migration 0024` fixes at 156s (default 180s). The lease expires mid-generation, the
reclaim clause in `reserve_serve_model` `[VERIFIED: 0020_reservation_release.sql:219-223]` admits a
second paid producer: 6¢ → 12¢, two charges, one document. That is the branch's entire thesis,
silently restored.

**Premise tags.** All `[VERIFIED]` at HEAD this round; the two mutation runs above are measurements,
not readings.

**This is standing shape #6** — the promise "the serve path runs 2 attempts at 50s" is a *negative
property over a call site*, and nobody counted. It is also a test the spec explicitly ordered and
that was never written: `docs/superpowers/specs/2026-08-10-serve-path-deadline-design.md` §5 —
*"assert the serve route reaches the wrapper … A grep-style import guard is appropriate — the repo
already uses one at `tests/lib/share/import-guard.test.ts`."* That file exists; no serve equivalent
does (`grep -rln "import-guard" tests/` → one hit).

**Fix.** Two lines, both cheap:
1. In `serve-doc-mapping.test.ts`, have the delegate capture argument 3 and assert
   `expect(seenBudget).toEqual(SERVE_BUDGET)` on the `'reserved'` materialize case.
2. Add the specified import guard: `lib/html-doc/serve-doc.ts` must not import
   `generateMagazineModel`, only `generateMagazineModelForServe`.

---

### H2 — the late-write residual was accepted **on condition of a log that does not exist**

**Claim.** `lib/html-doc/model-store.ts:65-88` emits no log on a put timeout, so the detection the
spec traded the residual away for is absent.

**The trade, in the spec's own words** (§3.5.1, *"Detection, since prevention is out of scope"*):

> a `put` timeout is logged with elapsed time and the target key, so the window in which this is
> possible is visible in production rather than inferred. If those logs ever appear, that is the
> trigger to promote the addressing work rather than to tune `PUT_TIMEOUT_MS`.

**What the code actually does** `[VERIFIED: lib/html-doc/model-store.ts:74-79]`:

```ts
  const expiry = new Promise<never>((_resolve, reject) => {
    timer = setTimeout(
      () => reject(new DOMException(`model put exceeded ${timeoutMs}ms`, 'TimeoutError')),
      timeoutMs,
    );
  });
```

No `console` call, no key, no elapsed. The rejection travels `serve-doc.ts:143` → `:149 throw err`
→ `serve-summary-core.ts` → the route's generic 500 handler.

**Failure scenario.** Owner A's put exceeds 15s and lands late; B regenerates and writes; A's late
put overwrites B. `isFresh` ignores `sourceMdHash` — **pinned as a characterisation test on this very
branch** `[VERIFIED: tests/lib/html-doc/read-model.test.ts:37-47]` — so with unchanged section
titles (the common case for a prose-only edit) the stale model is served **indefinitely**. The spec
calls this *"silent, user-visible stale content, not a bounded extra charge"* and accepted it
because it would be *visible*. It is not visible.

**What caller reaches the state.** Any owner serving a document whose model upload exceeds
`SERVE_PUT_TIMEOUT_MS`, i.e. exactly the population the residual is about.

**This is standing shape #7** — a rule preserved verbatim (the residual is accepted) that stopped
working because the mechanism carrying it (the log) was never built.

**Fix.** One line before the reject:
`console.warn('[model-store] put exceeded %dms for %s', timeoutMs, MODEL_KEY(base))`, with the
elapsed time from a `Date.now()` captured before the race. Assert it in the existing
`model-store.test.ts` timeout case so it cannot be dropped again.

---

### H3 — `settleBounded` reports success for a settle the database explicitly refused

**Claim.** `lib/html-doc/serve-doc.ts:176` treats *"the RPC returned"* as *"the settle happened"*,
and the returned boolean is discarded by both callers.

```ts
// lib/html-doc/serve-doc.ts:176
    if (out.ok) return true;
```

```sql
-- supabase/migrations/0020_reservation_release.sql:277-281
  update serve_model_charge
     set reserved_cents = 0, release_token = null
   where owner_id = v_owner and release_token = p_token and reserved_cents >= v_cfg.magazine_est_cents
   returning day into v_day;
  if not found then return false; end if;          -- stale/duplicate/forged token → no-op (idempotent)
```

`callRpcBounded` sets `ok:true` whenever there was no transport error `[VERIFIED:
lib/serve-rpc.ts:52-53]`, so `{ ok:true, data:false }` — *"I did nothing"* — is read as settled.
Three consequences, compounding:

1. **The retry that exists for exactly this case never fires.** `attempts = released ? 2 : 1`
   `[VERIFIED: serve-doc.ts:168]` only reruns on `!out.ok`.
2. **Nothing is logged.** `console.warn` at `:177` is only on the `!ok` branch. `ledger_audit`
   `[VERIFIED: 0020:285-296]` is written *inside* `settle_serve_model`, so a settle that returns
   `false` before reaching the release block records nothing anywhere.
3. **Both call sites discard the return value** — `serve-doc.ts:141` and `:148` are
   `if (releaseToken) await settleBounded(...)`. The docblock's promise at `:161-162`
   (*"the caller must never CLAIM a refund it could not apply"*) has no caller enforcing it.

**What caller reaches the state.** An owner whose lease was reclaimed while the attempt was still
running — the residual window this branch narrows but does not close — so `release_token` no longer
matches; or any deployment where `magazine_est_cents` is raised between reserve and settle, which
breaks the `reserved_cents >= v_cfg.magazine_est_cents` predicate.

**Money.** The direction is over-count (a refund not applied), which is the *safe* direction by this
repo's standing rule — that is why this is High and not Blocking. What is not safe is that the
refund mechanism can stop working entirely in production and emit **zero** signal. This is standing
shape #1 (`ok` conflating *applied* and *refused*) landing on the money path the branch was warned
about.

**Fix.**
```ts
    if (out.ok) {
      if (out.data === true) return true;
      console.warn(`[serve-model] settle(released=${released}) refused by the database — token stale or reclaimed`);
      return false;                       // a refused settle is not a settle
    }
```
and log at both call sites when `settleBounded` returns false, so a lost refund is distinguishable
from a lost keep at the point where the distinction has a cost.

---

## Medium

### M1 — the budget's settle term is one attempt; the release path runs two

`lib/serve-budget.ts:47,56-62` adds `SERVE_SETTLE_RPC_TIMEOUT_MS` **once**; `serve-doc.ts:168` runs
it **twice** when `released`. So the sum's claim — *"every term is a timeout the code actually
applies"* — is true term-by-term but the worst case exceeds it by 5s on one path.

**It is currently safe, and I traced exactly why**, because the reason is the finding:
`released` requires `!billing.metered` `[VERIFIED: serve-doc.ts:145-147]`; `billing.metered` is set
the instant `generateContent` returns `[VERIFIED: gemini.ts:274]`; and `writeModelEnvelopeWithin`
only runs after `generateMagazineModelForServe` resolves `[VERIFIED: serve-doc.ts:126-140]`.
Therefore `released ⟹ generateJson never returned ⟹ the 15s put never ran`, and the extra 5s is
covered three times over. Worst release path: `5 + 10 + 100.4 + 10 = 125.4s < 135.4s`.

That chain is written down nowhere. The spec explicitly contemplates revising `RELEASE_STATUSES`;
the day a refundable *post-meter* class is added, the sum under-counts silently. Shape #7 again.

**Fix (recommended).** `+ 2 * SERVE_SETTLE_RPC_TIMEOUT_MS`. `SERVE_FLOOR_SECONDS` goes 156 → 161,
still inside the 180 default and inside the 24.6s headroom the spec's own gantt draws. If instead
the coupling is kept, state it as a comment in `serve-budget.ts` **and** assert it.

### M2 — the anti-drift pin covers one of the migration's three `156` literals

`[VERIFIED: tests/integration/serve-config-invariant.test.ts:175]`
`const m = sql.match(/lease_ttl_seconds\s*>=\s*(\d+)\s*\)/);` matches only the CHECK at `0024:50`.
The data fix-up at `0024:44-46` is unpinned:

```sql
update guardrail_config
   set lease_ttl_seconds = 156
 where lease_ttl_seconds < 156;
```

Raise `SERVE_MARGIN_MS`, edit only the line the failing test points at, and the migration becomes
**unrunnable** on any database sitting between the old and new floor — `ADD CONSTRAINT` validates
existing rows. That is precisely the deploy-blocker execution discovered (plan status block, item 2),
reintroduced one retune later.

MEASURED: `SERVE_MARGIN_MS` 20_000 → 21_000 turns the pin red — but red *pointing at the CHECK*.
Restored.

**Fix.** Pin every occurrence: assert the file contains no three-digit literal other than
`SERVE_FLOOR_SECONDS`, or match the `set`/`where` literals individually.

### M3 — the reserve timeout is a SEQUENCE guard answered with a raw rejection, and it is a money leak this branch introduces

`serve-doc.ts:84-91`. **Guard classification: SEQUENCE** (*who got here first / is this in flight*),
enforcement: raw rejection (`return { status: 'busy' }`) after money may already have been spent.
`review-method.md`'s rule for that cell is *reconcile, never a raw rejection*.

The state is honestly named in the code (`'[serve-model] reserve timed out — possible empty paid
lease'`) and in spec §3.1, so I am not re-litigating the decision. What belongs on the record is the
**delta this branch creates**: before it, a slow reserve blocked and eventually returned an honest
token; after it, any reserve exceeding 5s permanently strands 6¢ in `spend_ledger.reserved_cents`
**and** `serve_owner_budget.spent_cents` with no token and therefore no reachable settle, plus one of
`max_serve_attempts`. Five such timeouts in a day on one document → `attempts_exhausted` → that
document returns 503 for the rest of the day.

`SERVE_RESERVE_RPC_TIMEOUT_MS` is labelled *"PROVISIONAL — revise from observed p99"*
`[VERIFIED: lib/serve-budget.ts:28-29]` and has never been measured. On a pooled Supabase connection
a 5s wait is not exotic.

**What would make it reconcile without a new mechanism.** `settle_serve_model` matches only on
`(owner_id, release_token)` `[VERIFIED: 0020:277-280]`. A settle reachable by
`(owner_id, doc_key, day)` when the token was never received converts this rejecter into a
reconciler using the table that already exists. Possibly not this slice's work — but it is the whole
difference between *named* and *handled*.

---

## Low

### L1 — `supabase/migrations/` guards are invisible to this project's own guard-classification ratchet

I ran `python3 scripts/check-guard-coverage.py`: 10 problems, every one naming `video_artifacts` or
`video_generations`; **nothing for `guardrail_config`**. So the new
`guardrail_config_lease_ttl_covers_serve` CHECK was never enumerated by the SHAPE/SEQUENCE ratchet
the process describes as covering *"every constraint, unique index, FK and trigger, read from
pg_catalog"*. Not a defect of this branch — a scope gap in a gate this branch is measured by.
I classified it by hand instead: **SHAPE** (a config value's well-formedness), reject is correct, and
mutation-verified (below). Confirms the brief's known-red judgment; I do not think it is wrong.

### L2 — `0024`'s constraint sweep drops by substring match

`[VERIFIED: supabase/migrations/0024_lease_covers_serve.sql:27-33]` drops every check constraint
whose definition `ilike '%lease_ttl_seconds%'`. A future multi-column CHECK
(`check (lease_ttl_seconds >= 1 and max_serve_attempts >= 1)`) would be dropped whole, silently
losing the unrelated half. Today there is exactly one match, so this is latent; the `raise warning`
on `count > 1` is a notice, not a guard. Otherwise the migration is idempotent and re-runnable —
verified by hand: the loop removes its own constraint, the fix-up is a no-op on a second run, and
`'guardrail_config'::regclass` fails loud if the table is absent.

### L3 — `fakeRpcBuilder` does not model postgrest's abort behaviour; the premise is documented, not tested

`[VERIFIED: tests/support/fake-rpc.ts:16]` `abortSignal(_s: AbortSignal) { return builder; }` — the
signal is discarded, so no test exercises the shape `lib/serve-rpc.ts:6-13` rests its whole design
on. I verified that premise directly against the installed client instead, and it holds at HEAD:
`[VERIFIED: node_modules/@supabase/postgrest-js/dist/index.cjs:328]`
`if (!this.shouldThrowOnError) res = res.catch((fetchError) => {` — an aborted fetch is caught and
**returned**, never thrown — and `:347` is the `AbortError`/`ABORT_ERR` special-case inside that
catch. Version `2.109.0`, matching the spec's pin. Harmless in practice because `callRpcBounded`
never inspects the error; recorded so the next round knows the fake is not evidence.

---

## What I attacked and why it held

1. **The refund rule (the thing two spec versions broke).** A not-metered 429/503 still refunds:
   `generateContent` throws `GoogleGenerativeAIFetchError(status 503)` *before* `gemini.ts:274` sets
   `metered`; `generateMagazineModel` re-wraps at `:587` with `{ cause: err }`;
   `classifyGeminiFailure` walks the cause chain `[VERIFIED: gemini-failure.ts:78-84]` and returns
   `'release'`; `serve-doc.ts:145-147` yields `released=true`, `settleBounded(token, true)`,
   `attempts = 2`. The integration money pin passes with zero edits to its assertions.
2. **`released ⟹ the put never ran`** — see M1. The single settle term in the sum is safe today; the
   proof is the finding.
3. **Hidden RPC retries — the sharpest thing I went looking for.** `postgrest-js` 2.109.0 ships an
   internal retry loop `[VERIFIED: dist/index.cjs:290-323]`, `DEFAULT_MAX_RETRIES = 3`, honouring
   `Retry-After`. If `rpc()` were retryable, **one `reserve_serve_model` call could charge up to four
   times** — the second-paid-producer class, from inside the client. It is not:
   `RETRYABLE_METHODS = ['GET','HEAD','OPTIONS']` `[VERIFIED: :25-29]` and `rpc()` issues POST
   `[VERIFIED: :3834]`. The retry sleep also takes our signal (`:311 sleep(delay, _this.signal)`), so
   even a retryable variant would stay inside the 5s bound.
4. **`countTokens`' new `timeout` is genuinely enforced, not merely added.**
   `[VERIFIED: @google/generative-ai/dist/index.js:1410-1421]` merges `SingleRequestOptions` over
   `_requestOptions` with the caller winning, and `buildFetchOptions` `[VERIFIED: :441-455]` does
   `setTimeout(() => controller.abort(), requestOptions.timeout)` and attaches the controller to the
   fetch. The model is constructed with no `requestOptions` `[VERIFIED: gemini.ts:542]`, so nothing
   overrides it. This was the Blocking class an earlier draft had; it is not present.
5. **The local generation path is untouched.** `[VERIFIED: lib/html-doc/generate.ts:40-43]` passes
   neither `opts.caps` nor `budget`, so the preflight is skipped and `generateJson` falls to
   `GENERATE_JSON_RETRIES` / `REQUEST_TIMEOUT_MS`. Pinned by `gemini-serve-budget.test.ts:90-101`.
   `sync-run.ts:464` still uses the unbounded `writeModelEnvelope` — correct, it holds no lease.
6. **Late resolution after a timeout does nothing harmful.** `callRpcBounded`'s `attempt` IIFE folds
   throws into `{ kind: 'threw' }` `[VERIFIED: lib/serve-rpc.ts:39-45]`, so a builder settling after
   the race cannot produce an unhandled rejection, and its value is discarded.
7. **Every blob read on the lease path.** `readFreshMagazineModel` (`serve-doc.ts:60`) and
   `tryGet` (`:74`) run **before** the reserve; the `in_flight` re-read (`:99`) and
   `readTitleStableModel` (`:106`) run on branches where no lease is held. No unbounded call sits
   inside the lease window, so the sum is complete for the window it claims to cover.
8. **Mutation checks — 5 run, 5 load-bearing, all restored** (`git status --short` clean):

| mutation | expected red | result |
|---|---|---|
| drop `ctrl.abort()` in `callRpcBounded` | `serve-rpc.test.ts:41` | RED ✓ |
| collapse `Promise.race` in `writeModelEnvelopeWithin` | `model-store.test.ts` | RED ✓ |
| `attempts = released ? 2 : 1` → `1` | `serve-doc-mapping.test.ts:203` | RED ✓ |
| drop the DB constraint (live Postgres) | `serve-config-invariant.test.ts` "refuses a lease shorter" | RED ✓ |
| `SERVE_MARGIN_MS` 20_000 → 21_000 | the migration-literal pin | RED ✓ (see M2) |
| **`SERVE_BUDGET` → 3×60s at `serve-doc.ts:129`** | **anything at all** | **GREEN — H1** |

---

## A red run I am **not** charging to this branch

My first full `npm test` reported `1 failed, 2637 passed`:
`serve-doc-mapping.test.ts:203` *"retries the settle ONCE"*, `Expected: 2 / Received: 1`. Five
subsequent full runs were 2638/2638.

The failure is byte-identical to what my own M2 mutation produces (`attempts = 1`), and a concurrent
Codex reviewer was writing into this worktree during that run
(`docs/reviews/whole-branch-serve-path-bounding-codex-r1.md` appeared mid-session). This project has
already measured that hazard — *"an instrument that edits the repo corrupts its peers; two concurrent
reviewers got 23/44 vs 44/44 on the same commit"*. So I am recording it, not reporting it. It does
mean concurrent adversarial reviewers on one worktree will keep producing unattributable reds;
worktree isolation per reviewer would end that class.

---

## Verdict

**NOT CONVERGED** — H1, H2 and H3 are new and none is a rewording. H1 in particular restores the
exact 6¢→12¢ double charge this branch exists to prevent while every gate stays green, which is the
strongest possible statement that the gate set does not yet cover the branch's own thesis.

Per `review-method.md`, H1's fix is a test-only change and H2/H3 are a few lines each — none is a new
design — so the next round should verify these three are *genuinely* fixed and hunt what the fixes
introduce, not restart the sweep.
