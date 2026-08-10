# One Deadline Per Lease — Bounding the Serve Path — Design Spec

**Status:** v1 — drafted 2026-08-10, not yet reviewed. Gate is dual adversarial review to convergence.
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

- expiry held on a **monotonic** clock (`performance.now() + budget_ms`), not wall time, so an NTP step
  mid-request cannot move it
- `remainingMs()` — the budget left
- a signal combining the caller's with the budget:
  `AbortSignal.any([requestSignal, AbortSignal.timeout(remainingMs())])`. Node 22, already pinned by
  `.github/workflows/ci.yml`

### 3.3 Every call under the lease spends from it

| call | today | under the deadline |
|---|---|---|
| `countTokens` (`gemini.ts:82`) | bare await | bounded by remaining |
| each `generateContent` (`gemini.ts:259`) | fixed 60s | `min(REQUEST_TIMEOUT_MS, remaining)` |
| next retry (`gemini.ts:256`) | unconditional | started only if `remaining ≥ one attempt` |
| `blobStore.put` (`model-store.ts:51`) | bare await | bounded by remaining |

`assertMagazineInputWithinCap` gains the signal parameter it never had. `generateMagazineModel` already
carries `opts.signal` (`gemini.ts:502`) and already threads it into `generateContent` — the preflight is
the one call on that path that skips plumbing which already exists around it.

### 3.4 `BlobStore.put` is NOT widened

A deadline is wall-clock, enforced by the caller, so `writeModelEnvelope` races the put against
`remainingMs()`. The seam keeps its four-argument `put` and the three adapters are untouched.

**The put may still land after we stop waiting.** This is benign and deliberate: that blob is an upsert
cache (`model-store.ts:38-44`), so a late write self-heals and the next view serves it free. It is
never a correctness input to a money decision — the money decision reads `tryGet` (`serve-doc.ts:71`).

### 3.5 The requirement is derived, not chosen

One exported constant — countTokens budget + one `generateContent` + the put + a settle margin —
computed from the constants already in `lib/gemini-cost.ts` and `lib/gemini.ts`, not re-typed. A test
asserts it fits under the shipped `lease_ttl_seconds` default, so the §1.2 class of defect (numbers
that are individually fine and jointly wrong) fails the suite rather than production.

---

## 4. Error handling

**Deadline expiry is an abort**, landing in the existing catch at `serve-doc.ts:129`.

The money rule needs **no change**. The `billing.metered` latch already distinguishes the two cases:

| when the deadline fires | metered | outcome |
|---|---|---|
| during `countTokens` (preflight) | false | refund — positively-not-metered class-A |
| during the upload (post-Gemini) | true | keep the charge |

Client disconnect stays distinguishable from budget expiry because the caller's original signal
survives inside the `AbortSignal.any` composition, and `classifyGeminiFailure(err, signal)`
(`serve-doc.ts:131`) still receives it.

`lease_too_short` → **503 plus a loud log**. It is always a misconfiguration, never a user condition.
It deliberately does **not** fall back to the stale rendering that `owner_over_budget` uses
(`serve-doc.ts:87-93`) — a misconfiguration should be visible, not papered over.

---

## 5. Testing

**Unit** — deadline arithmetic under a mocked monotonic clock; the retry loop declining to start an
attempt it cannot fund; each of the three bounded calls aborting at the budget rather than hanging;
the derived-requirement constant fitting under the shipped TTL default.

**Integration (live Supabase)** — `lease_too_short` moves **no money AND burns no attempt**, asserted
as both. Asserting only the money would pass against the exact defect described in §1.3, because the
refund path is what hides the attempt burn.

**Schema gates** — `scripts/check-schema-gates.sh`, plus a mutation proving the new pre-charge guard is
load-bearing (a mutation that removes the `lease_ttl_seconds < p_required_seconds` check must turn the
integration assertion red).

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

## 8. Out of scope

The BlobStore **object-age** seam remains task #44 (blob-addressing only). This spec covers the two
unbounded awaits and the deadline that governs them — nothing about generation addressing.
