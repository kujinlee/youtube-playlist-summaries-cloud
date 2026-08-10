# One Deadline Per Lease — Bounding the Serve Path — Design Spec

**Status:** v2 — round 1 findings applied (2 Blocking, 1 High, 3 Medium, all confirmed).
**Round 2 is mandatory** — the gate is a full round with no new Blocking/High, which has not happened.
**Review trail:** round 1 [codex](../../reviews/spec-serve-deadline-codex-r1.md) (NOT CONVERGED)
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

### 3.1 The RPC issues the budget and enforces the requirement

Migration `0024`, `create or replace` on `reserve_serve_model`:

- **new argument** `p_required_seconds int`
- **checked before the claim and before the charge**: if `lease_ttl_seconds < p_required_seconds`,
  return status `lease_too_short` — no claim, no charge, no `attempt_count` increment
- **also checked before the claim**: if `p_required_seconds < min_required_seconds` (new
  `guardrail_config` column), return status `required_understated` — likewise no claim, no charge,
  no attempt

**Why the second check exists (round-1 B2).** `reserve_serve_model` is granted to `authenticated,
anon` (`0020:264`). A declared requirement the DB accepts on trust is not a gate: any caller — a
hostile client, or our own app carrying a wrong constant — can pass `p_required_seconds := 1` and be
handed a lease that cannot cover the work, which is precisely the condition this spec exists to
prevent. The DB cannot know the app's timing, but it *can* refuse a declaration below a configured
floor, which is enough to make under-declaration unrepresentable rather than merely discouraged.

**Two statuses, two meanings, deliberately not merged.** `lease_too_short` means *the lease is
misconfigured for an honest requirement*; `required_understated` means *the caller's requirement is
not credible*. Collapsing them into one sentinel would produce a value meaning two things, which
`scripts/check-sentinel-meanings.py` exists to reject. Both surface as 503 (§4), but they are
different operational failures and must be separately diagnosable.
- **return becomes** `table(status text, release_token uuid, budget_seconds int)` where
  `budget_seconds` is `floor(extract(epoch from (lease_expires_at - now())))::int` — **floored**, so
  the rounding error always shortens the budget rather than lending the app time the lease does not
  have

**A duration, never a timestamp.** `budget_seconds` is computed entirely inside the DB's clock domain.
An absolute `timestamptz` would have to be compared against the app server's clock, so any Fly↔Supabase
skew would silently inflate or deflate the budget — zero in every test, nonzero in production.

**Why the check lives in the RPC and not the app.** The app cannot check before the irreversible step,
because the charge happens *inside* the reserve. A lease that cannot cover the work must not be
*granted*; granting it and apologising afterwards leaves the residue in `attempt_count` (§1.3). The app
is the only party that knows how long its own retry loop runs, so it asserts the requirement; the DB is
the only party that knows the TTL, so it enforces it. Neither hardcodes the other's number.

### 3.2 The `Deadline` value

Created once, immediately after a `reserved` status, from `budget_seconds`.

**The timer starts BEFORE the RPC is issued, not after it returns (round-1 B1).** The app captures
`t0 = performance.now()` *before* calling `reserve_serve_model`, and the deadline is `t0 +
budget_seconds`.

The naive version — starting the timer on the RPC's return — is broken. The lease begins at the DB's
`now()`, which happens *during* the call; the response then spends network time, PostgREST time and JS
scheduling time before the app starts counting. That gap is unaccounted, so the app's deadline lands
*after* `lease_expires_at`, a second producer can reclaim, and the double-charge this spec exists to
prevent reappears. The §3.1 floor only absorbs sub-second rounding, never transport latency.

Starting at `t0` makes the relationship provable rather than probable: `t0 ≤ lease_start` always,
because the request had not yet been sent, so `t0 + budget ≤ lease_expires_at` regardless of how slow
the round-trip was. The latency is charged against **our** budget, which is the side that can afford
to lose it.

- expiry held on a **monotonic** clock (`performance.now()`), not wall time, so an NTP step
  mid-request cannot move it
- `remainingMs()` — the budget left
- a signal combining the caller's with the budget:
  `AbortSignal.any([requestSignal, AbortSignal.timeout(remainingMs())])`. Node 22, already pinned by
  `.github/workflows/ci.yml`

### 3.3 Every call under the lease spends from it

| call | today | under the deadline |
|---|---|---|
| `countTokens` (`gemini.ts:82`) | bare await | bounded by `remaining − RESERVED_TAIL` |
| each `generateContent` (`gemini.ts:259`) | fixed 60s | `min(REQUEST_TIMEOUT_MS, remaining − RESERVED_TAIL)` |
| next retry (`gemini.ts:256`) | unconditional | started only if `remaining − RESERVED_TAIL ≥ MIN_VIABLE_ATTEMPT_MS` |
| `blobStore.put` (`model-store.ts:51`) | bare await | bounded by remaining, funded by `RESERVED_TAIL` |

**`RESERVED_TAIL` is the budget held back for the work that must happen *after* the last Gemini
attempt** — the model upload and the `settle_serve_model` call. Without it, a generation that finishes
at the last instant leaves nothing to persist or settle with, and the lease expires holding a paid
model that was never written (round-1 M2).

**The retry-start rule and the per-attempt timeout were contradictory in v1 (round-1 M1).** v1 said
"start a retry only if `remaining ≥ one attempt`" *and* "each attempt gets `min(60s, remaining)`" —
which together skip a viable short attempt. Concretely: two 60s timeouts plus 1.2s backoff leaves
~58.8s under a 180s lease, and v1 would decline a third attempt that had 58s to work with.

v2 resolves it in favour of trying: the gate is `MIN_VIABLE_ATTEMPT_MS` — the shortest attempt worth
paying for — not a full `REQUEST_TIMEOUT_MS`. A short attempt that fails costs the same as not
attempting (the deadline was going to expire anyway); a short attempt that succeeds saves the user a
whole re-reserve and another 6¢. The asymmetry favours attempting.

**The SDK already supports this on every call site.**
`node_modules/@google/generative-ai/dist/generative-ai.d.ts:778` —
`countTokens(request, requestOptions?: SingleRequestOptions)`, and `SingleRequestOptions` (`:1297`)
extends `RequestOptions` with `signal?: AbortSignal`. So the preflight takes the signal and timeout
directly; no wrapper is needed for it. Only the `blobStore.put` (§3.4) needs a caller-side race.

`assertMagazineInputWithinCap` gains the signal parameter it never had. `generateMagazineModel` already
carries `opts.signal` (`gemini.ts:502`) and already threads it into `generateContent` — the preflight is
the one call on that path that skips plumbing which already exists around it.

### 3.4 `BlobStore.put` is NOT widened

A deadline is wall-clock, enforced by the caller, so `writeModelEnvelope` races the put against
`remainingMs()`. The seam keeps its four-argument `put` and the three adapters are untouched.

**A put that lands after we stop waiting is benign.** That blob is an upsert cache
(`model-store.ts:38-44`), so a late write self-heals and the next view serves it free. It is never a
correctness input to a money decision — the money decision reads `tryGet` (`serve-doc.ts:71`).

**A put that never lands is NOT benign, and v1 was wrong to imply otherwise (round-1 M2).** If the
race times out and the upload then fails, we have paid Gemini, kept the charge, settled the token, and
written nothing. The next view finds no model, reserves, and charges again — a real repeat charge,
bounded only by `max_serve_attempts`. `SupabaseBlobStore.put` is `upload(upsert:true)` with no
cancellation and no post-timeout verification, so "the write is still in flight" and "the write died"
are indistinguishable from here.

This is mitigated, not eliminated, and the mitigation is budgetary rather than a seam change:
`RESERVED_TAIL` (§3.3) funds the upload out of budget that no Gemini attempt is allowed to consume, so
reaching the put with insufficient time requires the *whole lease* to have been exceeded rather than
merely the generation. A put timeout is therefore a lease-sizing failure, and is logged as one.

**Widening the seam would not fix this.** An `AbortSignal` on `put` would cancel our wait exactly as
the race does; it would not make a failed upload succeed. The residual risk is inherent to writing
after paying, and the honest mitigation is to make the write's budget non-negotiable.

### 3.5 The requirement is derived, not chosen

One exported constant — `SERVE_REQUIRED_MS` = countTokens budget + `MIN_VIABLE_ATTEMPT_MS` +
`RESERVED_TAIL` — computed from the constants already in `lib/gemini-cost.ts` and `lib/gemini.ts`, not
re-typed. It is the number the app passes as `p_required_seconds`, and it is **one attempt plus the
tail**, not the full retry loop (§2.1).

It has to satisfy two bounds simultaneously, which is what makes it derived rather than picked:

- `SERVE_REQUIRED_MS ≤ lease_ttl_seconds` shipped default — or production refuses every serve
- `SERVE_REQUIRED_MS ≥ min_required_seconds` (§3.1) — or the DB rejects our own declaration as
  understated

A test asserts both, so the §1.2 class of defect (numbers
that are individually fine and jointly wrong) fails the suite rather than production.

---

## 4. Error handling

**Deadline expiry is an abort**, landing in the existing catch at `serve-doc.ts:129`.

**v1 claimed the money rule needs no change. That was wrong twice, and round 1 caught the second one.**
v2 adds exactly one thing: a second latch.

### 4.1 Why one latch cannot answer the question

With today's single `billing.metered`, a deadline abort keeps the charge unconditionally. Traced:

| step | what happens on a deadline abort |
|---|---|
| `gemini-failure.ts:77` | `ourSignal?.aborted` is **false** — the deadline aborts the *composed* signal, not the caller's |
| `gemini-failure.ts:78-84` | the cause chain looks for `NonRetryableError` / `GeminiHttpError`; a `DOMException` `AbortError` is neither |
| `gemini-failure.ts:85` | falls through to `'keep'` |
| `serve-doc.ts:130-132` | `released` is false → `settle_serve_model(p_released := false)` → charge kept |

That is **correct for a deadline inside `generateContent`** and **wrong for a deadline inside the
`countTokens` preflight**, and the difference is the whole point.

`countTokens` is free, and it runs *before* any paid call. A deadline firing there charges 6¢ for
genuinely zero spend — a pure over-count, and one that now fires on a *designed* path rather than a
rare disconnect.

**But do not reach for `!billing.metered` to fix it.** `gemini.ts:260` sets `metered = true` only
*after* `generateContent` returns ("body received = Google billed"). So `metered === false` covers two
different worlds: *no paid call was ever issued*, and *a paid call is in flight and Google is already
billing*. Refunding on the second is an **under-count**, which this codebase treats as the bug while an
over-count is merely expensive (`serve-doc.ts:107-110`).

### 4.2 The fix: a latch set BEFORE the call

Add `billing.attempted`, set immediately **before** `model.generateContent(...)` at `gemini.ts:259` —
the mirror of `metered` at `:260`.

| latch | set | proves |
|---|---|---|
| `attempted` | before the call | a paid call **was issued** |
| `metered` | after the body returns | a paid call **completed** |

The refund condition becomes `!billing.attempted` — *no paid call was ever issued* — which is provable
from our side alone and cannot be confused with an in-flight call. A deadline in the preflight refunds;
a deadline anywhere at or after the first `generateContent` keeps the charge.

**The general shape, since this project keeps meeting it:** `metered` proves billing *happened*;
`attempted` proves billing was *possible*. A refund needs the **absence of possibility**, and the
codebase only ever had the first of the two — so every refund decision was being made with a quantity
that could not express the question.

### 4.3 The vendor confirms the keep side, and bounds the refund side

`node_modules/@google/generative-ai/dist/generative-ai.d.ts:1302-1304`, on
`SingleRequestOptions.signal`:

> NOTE: AbortSignal is a client-only operation. Using it to cancel an operation will not cancel the
> request in the service. **You will still be charged usage for any applicable operations.**

This is the reason `attempted` — and not `metered` — is the correct latch. Aborting an **issued** call
does not stop Google billing it, so a refund there would book a credit for money genuinely spent: the
under-count in its purest form. Aborting before any call is issued bills nothing, so a refund there is
simply accurate.

The vendor note also establishes that **cancellation is not a cost-control mechanism.** The deadline
exists to protect the *lease*, never to save money on a call already in flight. Anything in the
implementation that treats an abort as avoiding a charge is wrong on the vendor's own documentation.

Client disconnect stays distinguishable from budget expiry because the caller's original signal
survives inside the `AbortSignal.any` composition, and `classifyGeminiFailure(err, signal)`
(`serve-doc.ts:131`) still receives it. Both classify as `'keep'`; the distinction is for logging and
for the `attempt_count` story, not for the money.

### 4.4 The two refusal statuses

`lease_too_short` and `required_understated` (§3.1) both → **503 plus a loud log, each naming itself**.
Neither is a user condition; both are operator-visible failures with different remedies (raise
`lease_ttl_seconds` vs. fix the caller's declared requirement). Neither falls back to the stale
rendering that `owner_over_budget` uses (`serve-doc.ts:87-93`) — a misconfiguration should be visible,
not papered over.

---

## 5. Testing

**Unit** — deadline arithmetic under a mocked monotonic clock, including `t0` captured before the RPC
(§3.2) so a slow round-trip shortens the app budget rather than overrunning the lease; a retry started
when `remaining − RESERVED_TAIL ≥ MIN_VIABLE_ATTEMPT_MS` and declined below it (both directions — a
one-sided test passes on a guard that always says no); each bounded call aborting at the budget rather
than hanging.

**Money — three cases, because one latch could not tell them apart (§4).**

| deadline fires | `attempted` | expected |
|---|---|---|
| during `countTokens` preflight | false | **refund** — `p_released := true` |
| during an in-flight `generateContent`, before `metered` latches | true | **keep** |
| after the body returns, during the upload | true | **keep** |

Row 2 is the one that matters: it is the state the natural-looking `!billing.metered` fix reads as
refundable, and it must settle with `p_released := false`. Nothing asserts it today. Assert the error
*identity*, not merely that settling happened — a negative test that accepts "any failure" passes on a
typo, which this project has measured before.

**Integration (live Supabase)**

- `lease_too_short` moves **no money AND burns no attempt**, asserted as both. Asserting only the money
  would pass against the exact defect in §1.3, because the refund path is what hides the attempt burn.
- `required_understated` — same pair of assertions, via a direct RPC call with
  `p_required_seconds := 1`, i.e. the hostile-caller path, not just the honest one.

**The call site, not only the RPC (round-1 M3).** The two tests above prove the *guard* works when
given a bad number. They cannot prove production sends a good one — a test calling the RPC with a
hand-written `p_required_seconds` proves nothing about what `serve-doc.ts` passes. So: an assertion
that the production call site passes `SERVE_REQUIRED_MS` itself, and that `SERVE_REQUIRED_MS` satisfies
both bounds in §3.5. Without this, the whole gate can be green while the app under-declares.

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

## 8. Out of scope

The BlobStore **object-age** seam remains task #44 (blob-addressing only). This spec covers the two
unbounded awaits and the deadline that governs them — nothing about generation addressing.
