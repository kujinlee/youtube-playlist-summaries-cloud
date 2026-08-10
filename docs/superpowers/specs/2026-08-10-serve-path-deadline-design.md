# One Deadline Per Lease — Bounding the Serve Path — Design Spec

**Status:** v3 — rounds 1 and 2 applied (14 findings, all confirmed). **Round 3 is mandatory** — the
gate is a full round with no new Blocking/High, which has not happened.
**Review trail:** round 1 [codex](../../reviews/spec-serve-deadline-codex-r1.md) (NOT CONVERGED, 6) ·
round 2 [codex](../../reviews/spec-serve-deadline-codex-r2.md) (NOT CONVERGED, 8 — **six marked
`[v2-REGRESSION]`**, i.e. introduced by round 1's own fixes)
**Task:** #46 (split from #44/T5) · **Prod issue:** yes — the unbounded awaits are live today
**Feeds:** ADR-0007 round-16 Codex B1 (the grace-period sizing this unblocks)

---

## 0. The idea in plain terms

**The serve path holds a 180-second lease and has no idea how long it is allowed to take.**

A user requests a magazine rendering. The app reserves a lease, gets charged 6¢, calls Gemini, writes
the result, and settles. Two of those calls have no time bound at all, and the one that *does* have a
bound was given it independently of the lease — so its worst case is longer than the lease it runs
under.

When the lease expires underneath a request that is still running, `reserve_serve_model`'s reclaim
clause admits a **second paid producer** for the same slot. Two charges, one document.

**The fix: the lease issues a deadline, and every call underneath spends from it.** The lease already
knows when it expires. It just never told anyone.

---

## 1. What is measured, not asserted

Every claim below is quoted from the tree at `1a7c076`.

### 1.1 Two unbounded awaits, on a user-facing GET

`lib/gemini.ts:72-88` — `assertMagazineInputWithinCap` takes **no signal parameter**, and its
`countTokens` at `:82-84` is a bare await:

```ts
const { totalTokens } = await model.countTokens({
  generateContentRequest: { contents: [{ role: 'user', parts: [{ text: prompt }] }], generationConfig },
});
```

`lib/html-doc/model-store.ts:51` — same shape on the write side:

```ts
await blobStore.put(principal, MODEL_KEY(base), serialize(envelope), 'application/json');
```

Both run inside the lease-holding section of `lib/html-doc/serve-doc.ts` (`:112` and `:117`), reached
from a user-facing HTTP GET.

### 1.2 The bounded part already overruns the lease

The lease: `supabase/migrations/0012_serve_model_charge.sql:22` —
`lease_ttl_seconds int not null default 180 check (lease_ttl_seconds >= 1)`.

The covered operation, on the magazine path:

| source | value |
|---|---|
| `lib/gemini.ts:94` | `REQUEST_TIMEOUT_MS = 60_000`, applied per attempt at `:259` |
| `lib/gemini-cost.ts:22` | `GENERATE_JSON_RETRIES = 2` → 3 attempts (`:256`) |
| `lib/gemini.ts:267` | backoff `400 * 2**attempt` → 400ms + 800ms |

Worst case **181,200 ms against a 180,000 ms lease** — an overrun *before* either unbounded call is
counted.

Nothing relates these numbers. Two are module constants in TypeScript, one is a configurable column in
Postgres. Each was chosen sensibly in isolation; the product crosses the line, and no mechanism in the
repo can see the product.

### 1.3 A refund does not undo an attempt

`supabase/migrations/0020_reservation_release.sql:269-298` — `settle_serve_model` decrements
`serve_owner_budget` and `spend_ledger`. It **never touches `attempt_count`**.

`serve_model_charge.attempt_count` is bounded by `max_serve_attempts` (default 5,
`0012:21`); on exhaustion the doc returns `attempts_exhausted` for the rest of the UTC day.

So a reserve-then-abort returns the money and burns the attempt. Five of them brick the document — and
because the ledger balances, **nothing looks wrong**.

### 1.4 The lease's expiry is written but never returned

`supabase/migrations/0020_reservation_release.sql:188` —
`returns table(status text, release_token uuid)`. The expiry is written at `:217-222` and never
surfaced. The app holds a lease whose deadline it has no way to observe.

---

## 2. The decision that sets the shape

Task #46 could be scoped as *"add two missing timeouts"*. It is deliberately **not**.

Adding two independently-chosen numbers to three existing independently-chosen numbers leaves the
defect intact in a new form. The scope is: **the lease-holding critical section gets one deadline, and
that deadline is derived from the lease.** A change to `lease_ttl_seconds` must not be able to silently
invalidate the app's timing.

### 2.1 Why retries become opportunistic

Under B (§3.1), the app declares a requirement the DB enforces. The naive requirement is the retry
loop's full worst case — 181.2s from §1.2 — which exceeds the shipped default of 180 and would make
`reserve_serve_model` refuse **every serve request in production** on deploy. Correctly fail-closed, on
a premise that was already false.

A bigger lease is the wrong answer. Instead, **a shared deadline makes retries opportunistic**: the
loop starts another attempt only if the remaining budget can fund one. The declared requirement is
therefore *one attempt plus settling*, not *all attempts*.

This **dissolves** the §1.2 overrun rather than patching it. There is no longer a worst case computed
from a retry count — the deadline *is* the worst case.

---

## 3. Design

### 3.0 Units, stated once (round-2 B2)

v2 wrote `performance.now() + budget_seconds` and passed a constant named `SERVE_REQUIRED_MS` into an
argument named `p_required_seconds`. Both are unit errors, and each ships a broken gate in a different
direction: milliseconds into a seconds column declares a ~70,000-second requirement and returns
`lease_too_short` forever; seconds onto a millisecond clock yields a 180 ms deadline that aborts
instantly.

**Every quantity in this spec carries its unit in its name, and conversions happen at exactly two
points.**

| quantity | unit | where |
|---|---|---|
| `lease_ttl_seconds`, `min_required_seconds`, `p_required_seconds`, `budget_seconds` | **seconds** | SQL — matches the existing columns (`0012:20-22`) |
| `REQUEST_TIMEOUT_MS`, `RESERVED_TAIL_MS`, `MIN_VIABLE_ATTEMPT_MS`, `COUNT_TOKENS_BUDGET_MS`, `SERVE_REQUIRED_MS` | **milliseconds** | TypeScript — matches `gemini.ts:94` |
| `performance.now()` | milliseconds | TypeScript |

The two conversions, and their rounding directions — both chosen so the error is always
self-penalising:

- **App → DB:** `SERVE_REQUIRED_SECONDS = Math.ceil(SERVE_REQUIRED_MS / 1000)`. **Ceil**, so we never
  declare less time than we need.
- **DB → app:** `budget_ms = budget_seconds * 1000`, where `budget_seconds` was already floored in SQL
  (§3.1). **Floor**, so we never claim more budget than the lease has.

A test asserts both conversions and both rounding directions. A unit bug here is silent in exactly the
way §1.2's overrun was silent.

### 3.1 The RPC issues the budget and enforces the requirement

Migration `0024`, `create or replace` on `reserve_serve_model`:

- **new argument** `p_required_seconds int`
- **checked before the claim and before the charge**: if `lease_ttl_seconds < p_required_seconds`,
  return status `lease_too_short` — no claim, no charge, no `attempt_count` increment
- **also checked before the claim**: if `p_required_seconds < min_required_seconds`, return status
  `required_understated` — likewise no claim, no charge, no attempt
- **return becomes** `table(status text, release_token uuid, budget_seconds int)` where
  `budget_seconds` is `floor(extract(epoch from (lease_expires_at - now())))::int` — **floored**, so
  the rounding error always shortens the budget rather than lending the app time the lease does not
  have

**Why the requirement check exists (round-1 B2).** `reserve_serve_model` is granted to `authenticated,
anon` (`0020:264`). A declared requirement the DB accepts on trust is not a gate: any caller — a
hostile client, or our own app carrying a wrong constant — can pass `p_required_seconds := 1` and be
handed a lease that cannot cover the work, which is precisely the condition this spec exists to
prevent. The DB cannot know the app's timing, but it *can* refuse a declaration below a configured
floor, which makes under-declaration unrepresentable rather than merely discouraged.

**Two statuses, two meanings, deliberately not merged.** `lease_too_short` means *the lease is
misconfigured for an honest requirement*; `required_understated` means *the caller's requirement is
not credible*. Collapsing them into one sentinel would produce a value meaning two things, which
`scripts/check-sentinel-meanings.py` exists to reject. Both surface as 503 (§4.4), but they are
different operational failures with different remedies.

#### `min_required_seconds` — the default, and the drift that would follow (round-2 H1)

v2 introduced this column without a default, which is not a detail: it is the whole gate.

```sql
alter table guardrail_config
  add column min_required_seconds int not null default 85 check (min_required_seconds >= 1);
```

**85 is not chosen. It is `SERVE_REQUIRED_SECONDS` written down**, i.e.
`ceil((COUNT_TOKENS_BUDGET_MS + REQUEST_TIMEOUT_MS + RESERVED_TAIL_MS) / 1000)` =
`ceil((10_000 + 60_000 + 15_000) / 1000)` = 85 (§3.5).

That duplication is unavoidable — a migration literal cannot import a TypeScript constant — so it is
**gated rather than trusted**: a test asserts `min_required_seconds` in the shipped schema equals
`SERVE_REQUIRED_SECONDS` computed from the app constants. If someone tunes `REQUEST_TIMEOUT_MS` and
not the migration, the suite goes red rather than production returning `required_understated` on every
fresh materialisation. This is the same anti-drift shape as the existing cost-guard test that pins the
resolved model against the priced model (`gemini.ts:90-93`).

**Two ordering constraints the migration must satisfy**, both asserted:

1. `min_required_seconds ≤ lease_ttl_seconds` **in the shipped defaults** (85 ≤ 180). A floor above the
   TTL means every reserve returns `lease_too_short` — the gate refusing itself.
2. **On an already-deployed database with a customised `lease_ttl_seconds`**, adding this floor can
   make an installation that worked yesterday refuse service today. That is correct behaviour — such
   an installation *was* running an uncoverable lease — but it must be a deliberate, logged 503
   naming the two numbers, not a silent outage. The migration therefore also emits a `ledger_audit`
   row when it detects `lease_ttl_seconds < 85` at apply time, so the condition is visible before the
   first user hits it.

### 3.2 The `Deadline` value

**The timer starts BEFORE the RPC is issued (round-1 B1), and the budget is re-checked after it
returns (round-2 B1).**

The app captures `t0Ms = performance.now()` *before* calling `reserve_serve_model`; the deadline is
`t0Ms + budget_seconds * 1000`.

**Why not start on return.** The lease begins at the DB's `now()`, which happens *during* the call;
the response then spends network, PostgREST and scheduling time before the app could start counting.
That gap is unaccounted, so the app's deadline lands *after* `lease_expires_at`, a second producer can
reclaim, and the double-charge this spec exists to prevent reappears. Starting at `t0Ms` makes the
relationship provable: `t0Ms ≤ lease_start` always, because the request had not yet been sent, so the
app deadline is at or before `lease_expires_at` regardless of round-trip latency.

**What that costs, and the check that pays for it (round-2 B1).** The proof is sound but it converts
*pre-lease* latency into *post-reserve* budget loss. If the RPC sits behind connection pooling for
170 s, the DB grants a fresh 180 s lease while the app has ~10 s left on its own clock — then aborts,
having charged 6¢ and burned an attempt. Five of those exhaust `max_serve_attempts` and brick the
document for the day.

So the deadline is not merely computed, it is **checked for viability before anything is spent**:

> After the RPC returns and before the first Gemini call, if
> `deadline − performance.now() < SERVE_REQUIRED_MS`, abandon: settle with `p_released := true`, log
> the measured round-trip, and return `busy`.

This is the **only refund path in the design** (§4.2), and it is reachable and provable: nothing has
been issued, so nothing can have been billed. It does not recover the burned `attempt_count` — that
was spent inside the RPC and `settle_serve_model` cannot undo it (§1.3) — but it stops us paying
Gemini for work that provably cannot finish, and the log makes the pathological latency diagnosable
instead of appearing as a mysterious `attempts_exhausted`.

Remaining properties:

- expiry held on a **monotonic** clock (`performance.now()`), not wall time, so an NTP step mid-request
  cannot move it
- `remainingMs()` — the budget left
- a signal combining the caller's with the budget:
  `AbortSignal.any([requestSignal, AbortSignal.timeout(remainingMs())])`. Node 22, already pinned by
  `.github/workflows/ci.yml`

### 3.3 Every call under the lease spends from it

| call | today | under the deadline |
|---|---|---|
| `countTokens` (`gemini.ts:82`) | bare await | bounded by `min(COUNT_TOKENS_BUDGET_MS, remaining − RESERVED_TAIL_MS)` |
| each `generateContent` (`gemini.ts:259`) | fixed 60 s | `min(REQUEST_TIMEOUT_MS, remaining − RESERVED_TAIL_MS)` |
| next retry (`gemini.ts:256`) | unconditional | started only if `remaining − RESERVED_TAIL_MS ≥ MIN_VIABLE_ATTEMPT_MS` |
| `blobStore.put` (`model-store.ts:51`) | bare await | bounded by remaining, funded by `RESERVED_TAIL_MS` |

**`RESERVED_TAIL_MS` is budget held back for the work that must happen *after* the last Gemini
attempt** — the model upload and the `settle_serve_model` call. Without it, a generation finishing at
the last instant leaves nothing to persist or settle with, and the lease expires holding a paid model
that was never written.

**The retry-start rule and the per-attempt timeout were contradictory in v1 (round-1 M1).** v1 said
"start a retry only if `remaining ≥ one attempt`" *and* "each attempt gets `min(60s, remaining)`" —
together those decline a viable short attempt. Concretely: two 60 s timeouts plus 1.2 s backoff leaves
~58.8 s under a 180 s lease, and v1 would refuse a third attempt that had 58 s to work with.

Resolved in favour of trying: the retry gate is `MIN_VIABLE_ATTEMPT_MS` — the shortest attempt worth
paying for — not a full `REQUEST_TIMEOUT_MS`. A short attempt that fails costs what not attempting
costs (the deadline was expiring anyway); a short attempt that succeeds saves the user a re-reserve
and another 6¢.

**`MIN_VIABLE_ATTEMPT_MS` governs RETRIES ONLY. It is not what we declare (round-2 H2).** v2 derived
the declared requirement from it, which made "one attempt plus settling" mean "one *shortest-worth-
trying* attempt plus settling" — so a 20 s lease could pass the gate while the first attempt got ~5 s.
The declaration must describe a **full** attempt, and does (§3.5). The two constants answer different
questions:

| constant | question |
|---|---|
| `REQUEST_TIMEOUT_MS` | how long may one attempt run? — and what we **declare** |
| `MIN_VIABLE_ATTEMPT_MS` | is there enough left to bother with **another** attempt? |

**The SDK supports the bound at every call site.**
`node_modules/@google/generative-ai/dist/generative-ai.d.ts:778` —
`countTokens(request, requestOptions?: SingleRequestOptions)`, and `SingleRequestOptions` (`:1297`)
extends `RequestOptions` with `signal?: AbortSignal`. Only `blobStore.put` (§3.4) needs a caller-side
race.

`assertMagazineInputWithinCap` gains the signal parameter it never had. `generateMagazineModel` already
carries `opts.signal` (`gemini.ts:502`) and threads it into `generateContent` — the preflight is the
one call on that path that skips plumbing already present around it.

### 3.4 `BlobStore.put` is NOT widened

A deadline is wall-clock, enforced by the caller, so `writeModelEnvelope` races the put against
`remainingMs()`. The seam keeps its four-argument `put`; the three adapters are untouched.

**A put that lands after we stop waiting is benign.** That blob is an upsert cache
(`model-store.ts:38-44`), so a late write self-heals and the next view serves it free. It is never a
correctness input to a money decision — that decision reads `tryGet` (`serve-doc.ts:71`).

**A put that never lands is NOT benign, and v1 was wrong to imply otherwise (round-1 M2).** If the race
times out and the upload then fails, we have paid Gemini, kept the charge, settled the token, and
written nothing. The next view finds no model, reserves, and charges again — a real repeat charge,
bounded only by `max_serve_attempts`. `SupabaseBlobStore.put` is `upload(upsert:true)` with no
cancellation and no post-timeout verification, so "still in flight" and "died" are indistinguishable
from here.

**`RESERVED_TAIL_MS` reduces this risk; it does not prove it away (round-2 M1).** v2 claimed a put
timeout implies the whole lease was exceeded. That is false: the tail can simply be undersized, or
pre-lease latency (§3.2) can have eaten the budget before the lease began. The honest statement is
narrower — the tail ensures no *Gemini attempt* is permitted to consume the write's budget, which
removes the most common cause of a starved write without removing the failure mode.

A put timeout is therefore logged with the measured tail and the measured remaining budget, so an
undersized `RESERVED_TAIL_MS` is diagnosable from production rather than inferred.

**Widening the seam would not fix this.** An `AbortSignal` on `put` cancels our wait exactly as the
race does; it does not make a failed upload succeed. The residual risk is inherent to writing after
paying.

### 3.5 The requirement is derived, not chosen

```
SERVE_REQUIRED_MS      = COUNT_TOKENS_BUDGET_MS + REQUEST_TIMEOUT_MS + RESERVED_TAIL_MS
                       = 10_000 + 60_000 + 15_000 = 85_000
SERVE_REQUIRED_SECONDS = ceil(SERVE_REQUIRED_MS / 1000) = 85
```

Built from constants already in `lib/gemini.ts` and `lib/gemini-cost.ts`, not re-typed. This is the
number the app passes as `p_required_seconds`, and it describes **one full attempt plus the tail** —
`REQUEST_TIMEOUT_MS`, not `MIN_VIABLE_ATTEMPT_MS` (round-2 H2). It is deliberately *not* the whole
retry loop (§2.1).

Three bounds must hold simultaneously, which is what makes it derived rather than picked. All three
are asserted:

- `SERVE_REQUIRED_SECONDS ≤ lease_ttl_seconds` shipped default (85 ≤ 180) — or production refuses
  every serve
- `SERVE_REQUIRED_SECONDS ≥ min_required_seconds` — or the DB rejects our own declaration
- `min_required_seconds == SERVE_REQUIRED_SECONDS` in the shipped schema (§3.1) — the anti-drift gate

so the §1.2 class of defect — numbers that are individually fine and jointly wrong — fails the suite
rather than production.

---

## 4. Error handling

**v1 claimed the money rule needs no change. That was wrong twice.** v2 fixed one and mis-scoped the
other. v3 states the rule in one line, then justifies it:

> **Refund if and only if no Gemini call of any kind was issued. Otherwise keep the charge.**

### 4.1 Why the existing latch cannot express that

With today's single `billing.metered`, a deadline abort keeps the charge unconditionally. Traced:

| step | what happens on a deadline abort |
|---|---|
| `gemini-failure.ts:77` | `ourSignal?.aborted` is **false** — the deadline aborts the *composed* signal, not the caller's |
| `gemini-failure.ts:78-84` | the cause chain looks for `NonRetryableError` / `GeminiHttpError`; a `DOMException` `AbortError` is neither |
| `gemini-failure.ts:85` | falls through to `'keep'` |
| `serve-doc.ts:130-132` | `released` is false → `settle_serve_model(p_released := false)` → charge kept |

`gemini.ts:260` sets `metered = true` only *after* `generateContent` returns ("body received = Google
billed"). So `metered === false` covers two different worlds: *no paid call was ever issued*, and *a
paid call is in flight and Google is already billing*. Refunding on the second is an **under-count**,
which this codebase treats as the bug while an over-count is merely expensive
(`serve-doc.ts:107-110`).

### 4.2 The latch, and why it is set before `countTokens` too

Add `billing.attempted`, set immediately **before** the first Gemini call — including the `countTokens`
preflight, not only `generateContent`.

| latch | set | proves |
|---|---|---|
| `attempted` | before any Gemini call is issued | billing **was possible** |
| `metered` | after a body returns | billing **completed** |

**Why the preflight counts (round-2 B3).** v2 refunded a deadline that fired during `countTokens`, on
the premise that `countTokens` is free. **We have no proof of that.** The SDK says only that aborted
operations may still be charged (`generative-ai.d.ts:1297-1305`); Google's billing documentation prices
input, output and cached tokens without stating that `countTokens` is exempt. A refund rule resting on
an unverified vendor-pricing premise is exactly the "rule proved about the wrong quantity" shape this
project keeps hitting — and the direction of the error is an under-count.

So `countTokens` is treated as billable until proven otherwise, and the refund rule reduces to *did we
issue anything at all?*

**This makes the design smaller, not larger.** The only reachable refund state is the §3.2 viability
check: the budget was already too small when the RPC returned, so we abandoned before issuing anything.
That state is provable from our side alone, needs no vendor premise, and cannot be confused with an
in-flight call.

**The general shape:** `metered` proves billing *happened*; `attempted` proves billing was *possible*.
A refund needs the **absence of possibility**, and the codebase only ever had the first of the two —
so every refund decision was being made with a quantity that could not express the question.

### 4.2.1 `BillingLatch` is shared — the field is REQUIRED, and absence is never a refund

`BillingLatch` (`lib/job-queue/billing-latch.ts:7`) currently holds only `metered` and is constructed
across the serve, worker, dig, summary and transcript paths (`worker-runner.ts:35`,
`serve-doc.ts:110`, and others).

**`attempted` is added as a required field, not optional (round-2 H3).** Optional would compile
everywhere and be wrong: `!billing.attempted` reads true when the field is merely *absent*, so a path
that never set it would look like "no call was issued" and refund. That is fail-open on money, and it
is the codebase's oldest root cause wearing new clothes — the Stage 3 "absent vs failed-to-read"
conflation, where `null` meant both "no bytes" and "could not read", and which produced a Blocking,
three Highs and a live 6¢→12¢ double charge.

Required means the compiler names every construction site instead of leaving them to be remembered.

**And the rule is affirmative, belt and braces:** a refund requires `billing.attempted === false` from
a latch that was actually supplied. No latch → **keep**. There is no path on which a missing latch
produces a credit.

### 4.3 What the vendor note does and does not license

`generative-ai.d.ts:1302-1304`, on `SingleRequestOptions.signal`:

> NOTE: AbortSignal is a client-only operation. Using it to cancel an operation will not cancel the
> request in the service. **You will still be charged usage for any applicable operations.**

This is why aborting an **issued** call must never refund: cancellation stops us waiting, not Google
billing, so a refund there books a credit for money genuinely spent.

It also establishes that **cancellation is not a cost-control mechanism.** The deadline protects the
*lease*; it never saves money on a call in flight. Anything in the implementation that treats an abort
as avoiding a charge is wrong on the vendor's own documentation.

Client disconnect stays distinguishable from budget expiry because the caller's original signal
survives inside the `AbortSignal.any` composition, and `classifyGeminiFailure(err, signal)`
(`serve-doc.ts:131`) still receives it. Both keep the charge; the distinction is for logging, not money.

### 4.4 The two refusal statuses

`lease_too_short` and `required_understated` (§3.1) both → **503 plus a loud log, each naming itself
and both numbers**. Neither is a user condition; both are operator-visible failures with different
remedies (raise `lease_ttl_seconds` vs. fix the caller's declared requirement). Neither falls back to
the stale rendering that `owner_over_budget` uses (`serve-doc.ts:87-93`) — a misconfiguration should be
visible, not papered over.
---

## 5. Testing

**Units (round-2 B2)** — the conversions in §3.0, both directions and both rounding directions:
`SERVE_REQUIRED_SECONDS === ceil(SERVE_REQUIRED_MS / 1000)`, `budget_ms === budget_seconds * 1000`.
Plus a guard that the value handed to `p_required_seconds` is in **seconds** and the value added to
`performance.now()` is in **milliseconds** — a unit bug here is silent in exactly the way §1.2's
overrun was silent, and it is the single most likely implementation slip in this spec.

**Unit** — deadline arithmetic under a mocked monotonic clock, including `t0Ms` captured before the RPC
(§3.2) so a slow round-trip shortens the app budget rather than overrunning the lease; a retry started
when `remaining − RESERVED_TAIL_MS ≥ MIN_VIABLE_ATTEMPT_MS` **and** declined below it — both
directions, since a one-sided test passes on a guard that always says no; each bounded call aborting at
the budget rather than hanging.

**The viability check (§3.2)** — with a mocked RPC that returns a full `budget_seconds` after a
simulated 170 s round-trip, the path must abandon **before** any Gemini call, settle with
`p_released := true`, and return `busy`. Assert *no Gemini call was issued*, not merely that the result
was `busy`: a path that called Gemini and then failed also returns `busy`.

**Money — the rule is one line, so test the line (§4).**

> Refund iff no Gemini call of any kind was issued.

| deadline fires | `attempted` | expected |
|---|---|---|
| before any Gemini call — the §3.2 viability check | false | **refund** — `p_released := true` |
| during the `countTokens` preflight | true | **keep** |
| during an in-flight `generateContent`, before `metered` latches | true | **keep** |
| after the body returns, during the upload | true | **keep** |

Row 3 is the one that matters: it is the state the natural-looking `!billing.metered` fix reads as
refundable, and it must settle with `p_released := false`. Row 2 is the one v2 got wrong by assuming
`countTokens` is free (§4.2). Nothing asserts any of these today.

Assert the error *identity*, not merely that settling happened — a negative test that accepts "any
failure" passes on a typo, which this project has measured before.

**Fail-closed on a missing latch (§4.2.1)** — a call path that supplies no `BillingLatch` must
**keep** the charge. Assert it directly; this is the fail-open direction, and "required field" protects
compile-time construction, not a caller that passes `undefined`.

**Integration (live Supabase)**

- `lease_too_short` moves **no money AND burns no attempt**, asserted as both. Asserting only the money
  would pass against the exact defect in §1.3, because the refund path is what hides the attempt burn.
- `required_understated` — same pair of assertions, via a direct RPC call with
  `p_required_seconds := 1`, i.e. the hostile-caller path, not just the honest one.

**Anti-drift on the migration literal (§3.1)** — `min_required_seconds` in the shipped schema must
equal `SERVE_REQUIRED_SECONDS` computed from the app constants. A migration literal cannot import a
TypeScript constant, so this assertion is the only thing standing between a tuned `REQUEST_TIMEOUT_MS`
and every fresh materialisation returning `required_understated`.

**The call site, and a mutation that proves the assertion can fail (round-1 M3, round-2 M2).** The
tests above prove the *guard* works when handed a bad number; they cannot prove production sends a good
one. So: assert the production call site passes `SERVE_REQUIRED_SECONDS`.

That assertion is **tautological on its own** — implementation and test import the same constant, so
both move together and stay green while the constant is wrongly derived or wrongly converted. It is
therefore paired with two mutations that must turn it red:

1. change the call site to pass a literal `1` → red
2. change the app→DB conversion to divide by 1000 twice (or omit the division) → red

Without those, this test asserts that a constant equals itself.

**Schema gates** — `scripts/check-schema-gates.sh`, plus a mutation per guard: removing
`lease_ttl_seconds < p_required_seconds` must turn the `lease_too_short` assertion red, and removing
`p_required_seconds < min_required_seconds` must turn the `required_understated` assertion red.
**Two guards, two mutations** — one mutation covering both would report coverage it does not have,
which is the failure `scripts/check-guard-coverage.py` exists to catch.

---


## 6. Deploy ordering

The migration changes the RPC's **signature**, so ordering is: function first, then app.

Postgres overloads on argument list, so the two-argument `reserve_serve_model(uuid, text)` *could*
co-exist with the three-argument form during rollout. **It will not.** Migration 0024 drops the
two-argument overload in the same transaction that creates the three-argument one.

**Why accept the window rather than the overload.** A surviving two-argument form is a callable path
that reserves and charges *without* the requirement check — the gate this spec exists to add, present
in the schema and bypassable by an older caller. That is a fail-open path of exactly the class this
project keeps rediscovering, and "we will delete it next deploy" is how it becomes permanent.

The cost is a window between migration and app rollout in which the old app calls a signature that no
longer exists. That surfaces as a serve-path error, which is transient and retryable, and touches only
magazine *materialisation* — cached models still serve, since the `readFreshMagazineModel` fast path
(`serve-doc.ts:55`) returns before any RPC call. No money moves in the window: a failed RPC reserves
nothing.

---

## 7. Decided without asking, recorded so review can reopen

1. The per-attempt timeout becomes `min(REQUEST_TIMEOUT_MS, remaining)` rather than a new constant —
   one fewer independently-chosen number.
2. `lease_too_short` returns 503 rather than the stale-rendering fallback (§4).
3. `BlobStore.put` keeps its signature (§3.4).
4. Migration 0024 **drops** the two-argument overload rather than keeping it for a deploy (§6) — a
   bypassable copy of the gate is worse than a short retryable window.
5. `budget_seconds` is floored, so rounding can only shorten the budget (§3.1).

**Added in v2, from round 1:**

6. `min_required_seconds` + the `required_understated` status (§3.1) — a caller-declared requirement
   the DB accepts on trust is not a gate.
7. The timer starts at `t0`, before the RPC (§3.2) — makes `app deadline ≤ lease expiry` provable
   rather than probable.
8. The `billing.attempted` latch (§4.2) — `metered` cannot distinguish "never issued" from "in flight",
   and the refund decision needs exactly that distinction.
9. `RESERVED_TAIL` + `MIN_VIABLE_ATTEMPT_MS` (§3.3) — resolves v1's contradiction between the
   retry-start rule and the per-attempt timeout, and funds the post-generation write.

## 7a. Round-1 findings and disposition

| # | Finding | Disposition |
|---|---|---|
| B1 | `budget_seconds` stale before the app's timer starts | **Accepted** — §3.2, timer starts at `t0` |
| B2 | `p_required_seconds` caller-controlled → gate bypassable | **Accepted** — §3.1 floor + new status |
| H1 | "the money rule needs no change" is false | **Accepted, reframed** — §4.2 `attempted` latch |
| M1 | retry-start rule contradicts per-attempt timeout | **Accepted** — §3.3 |
| M2 | abandoned `put` not benign on all adapters | **Accepted** — §3.4 rewritten; risk stated, not dismissed |
| M3 | `lease_too_short` test proves only the explicit branch | **Accepted** — §5 call-site assertion |

**On H1, the reviewer and the author reached the same finding from opposite directions.** Round 1 said
keeping the charge on a pre-meter abort is the defect; the draft argued keeping is correct because the
vendor bills aborted calls anyway. Both are right about *different windows* — free preflight vs.
in-flight paid call — and neither position is expressible with a single latch. The disagreement was the
signal that the quantity, not the threshold, was wrong (§4.2).

## 7b. Round-2 findings and disposition

**Six of the eight were marked `[v2-REGRESSION]` — introduced by round 1's own fixes.** That is the
pattern this project has measured repeatedly and the reason a fix round is never the last round.

| # | Finding | Disposition |
|---|---|---|
| B1 | `t0`-before-RPC converts pre-lease queue time into post-reserve budget loss | **Accepted** — §3.2 viability check; `t0` kept, because the alternative overruns the lease |
| B2 | seconds/ms confusion across §3.1/§3.2/§3.5 | **Accepted** — §3.0, units in every name, two conversions, both rounding directions asserted |
| B3 | "`countTokens` is free" is an unproven vendor-pricing premise | **Accepted** — §4.2, `attempted` set before the preflight too |
| H1 | `min_required_seconds` had no default or drift rule | **Accepted** — §3.1, default 85 + anti-drift assertion + two ordering constraints |
| H2 | declared requirement derived from `MIN_VIABLE_ATTEMPT_MS`, not a full attempt | **Accepted** — §3.5, declares `REQUEST_TIMEOUT_MS`; `MIN_VIABLE` governs retries only |
| H3 | `BillingLatch` shape change unspecified for existing callers | **Accepted** — §4.2.1, required field + affirmative-false rule |
| M1 | `RESERVED_TAIL` overstated what it proves | **Accepted** — §3.4 narrowed to what it actually removes |
| M2 | call-site assertion tautological without mutation | **Accepted** — §5, two mutations that must turn it red |

**B1 and B3 collapsed into one another, and that is the round's real result.** B3 says an unproven
"`countTokens` is free" cannot carry a refund rule. B1 says a queued RPC can leave a budget too small
to use. Treating the preflight as billable makes the only refundable state *"we never started"* — which
is precisely the state B1's viability check creates. Two findings, one mechanism, and the design got
smaller: the refund rule is now one line that needs no vendor premise at all.

**What round 2 did NOT do, and round 3 must.** Every finding above was accepted. A round in which the
reviewer is right about everything is not evidence that the next round will be quiet — round 1 was also
fully accepted, and its fixes produced six regressions. v3 introduces a viability check, a new refund
condition, a required interface field, a migration literal and two conversions. All five are new
surface.

## 8. Out of scope

The BlobStore **object-age** seam remains task #44 (blob-addressing only). This spec covers the two
unbounded awaits and the deadline that governs them — nothing about generation addressing.
