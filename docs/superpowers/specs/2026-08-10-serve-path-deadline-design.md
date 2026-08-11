# Bounding the Serve Path — Design Spec

**Status:** **v6** — rounds 5 and 6 applied to the v4 redesign. v1–v3 are superseded, not amended.
**Proceeding to Phase 2 (writing-plans)**, where the plan carries its own dual adversarial review to
convergence (`dev-process.md:82`). See §7.5 for why that, and not a seventh spec round.
**Task:** #46 · **Prod issue:** yes — the unbounded awaits are live today

**Review trail**

| Round | Doc | Result |
|---|---|---|
| 1 | [codex r1](../../reviews/spec-serve-deadline-codex-r1.md) | NOT CONVERGED — 6 findings, all accepted |
| 2 | [codex r2](../../reviews/spec-serve-deadline-codex-r2.md) | NOT CONVERGED — 8 findings, **6 caused by round 1's fixes** |
| 3 | [codex r3](../../reviews/spec-serve-deadline-codex-r3.md) | NOT CONVERGED — 7 findings, **7 caused by round 2's fixes** |
| 4 | [design review](../../reviews/spec-serve-deadline-design-review-r4.md) | **VERDICT: REDESIGN** |
| 5 | [codex v4 r5](../../reviews/spec-serve-deadline-codex-v4-r5.md) | NOT CONVERGED — 7 findings on the redesign, **none a regression from a prior fix** |
| 6 | [codex v5 r6](../../reviews/spec-serve-deadline-codex-v5-r6.md) | NOT CONVERGED — 5 findings, all from v5's fixes; 4 are prose overstating the design, 1 is a scope decision |

Rounds 2 and 3 tripped the escalation rule in [`review-method.md:45-47`](../../review-method.md) —
*findings caused by the previous round's fixes in two consecutive rounds → stop fixing, redesign.*
21 of 21 findings were confirmed against the code. **The defects were real and the shape was wrong**;
those are not in tension, and that is exactly what the rule exists to detect.

**Round 5 is the first round that did not re-trigger it.** Its findings are term-level — omitted
budget terms, an overstated seam, an understated risk — and every one is repaired *inside* the shape
without adding a mechanism. §2.1's table is unchanged from v4. That is what a converging design looks
like, and it is the distinction the escalation rule exists to draw.

---

## 0. The idea in plain terms

**The serve path can take longer than the lease it holds.**

A user requests a magazine rendering. The app takes a 180-second lease, is charged 6¢, calls Gemini,
writes the result, settles. Two of those calls have no time bound at all, and the bounded ones add up
to more than 180 seconds. When the lease expires under a still-running request,
`reserve_serve_model`'s reclaim clause admits a **second paid producer** — two charges, one document.

**The fix: make the work provably shorter than the lease, and stop the lease from being configured
below the work.** No coordination, because there is nothing to coordinate with — §2.2.

---

## 1. What is measured, not asserted

Quoted from the tree at `1a7c076`. Verified in review rounds 1–2 and unchanged by the redesign.

### 1.1 Two unbounded awaits, on a user-facing GET

`lib/gemini.ts:72-88` — `assertMagazineInputWithinCap` takes **no signal parameter**, and its
`countTokens` at `:82-84` is a bare await. `lib/html-doc/model-store.ts:51` — `blobStore.put` is the
same shape. Both run inside the lease-holding section of `lib/html-doc/serve-doc.ts` (`:112`, `:117`),
reached from a user-facing HTTP GET.

### 1.2 The bounded part already overruns the lease

| source | value |
|---|---|
| `supabase/migrations/0012_serve_model_charge.sql:22` | `lease_ttl_seconds int not null default 180` |
| `lib/gemini.ts:94` | `REQUEST_TIMEOUT_MS = 60_000`, applied per attempt at `:259` |
| `lib/gemini-cost.ts:22` | `GENERATE_JSON_RETRIES = 2` → 3 attempts (`:256`) |
| `lib/gemini.ts:267` | backoff `400 * 2**attempt` → 400 ms + 800 ms |

**181,200 ms against a 180,000 ms lease.** Two of those numbers are TypeScript constants and one is a
Postgres column. Nothing in the repo relates them, so nothing could have caught the product.

### 1.3 A refund does not undo an attempt

`supabase/migrations/0020_reservation_release.sql:269-298` — `settle_serve_model` adjusts the ledgers
and **never touches `attempt_count`**, which is bounded by `max_serve_attempts` (default 5,
`0012:21`). A reserve-then-abort returns the money and burns the attempt; five brick the document for
the UTC day while the ledger balances.

---

## 2. Coherence — filled in BEFORE review this time

Required by [`process-checklists.md:171-196`](../../process-checklists.md) for any spec that adds a
mechanism. **It was skipped for v1–v3, and skipping it is the direct cause of the three wasted
rounds** — the duplicate below was visible from the first draft for the cost of writing the table.

### 2.1 Concern → mechanism

| Concern | Mechanism | Evidence |
|---|---|---|
| Prevent a second paid producer for one `(owner, doc_key, day)` | the **existing** `serve_model_charge` lease — **unchanged by this spec** | `0012:7-13`, `0020:217-235` |
| Bound each external call | a per-call timeout | §3.1 |
| Guarantee the bounded work fits inside any configured lease | a **CHECK constraint** on `lease_ttl_seconds` | §3.3 |
| Decide whether a failed generation is refundable | the **existing** `classifyGeminiFailure` + `billing.metered` — **unchanged** | `gemini-failure.ts:76-86`, `serve-doc.ts:130-132` |

One mechanism per concern, one concern per mechanism.

**What v3 had here, for contrast:** three mechanisms for "the work fits the lease", three for "refund
correctness", two for "the declaration is credible". The design review's table
(`design-review-r4.md:53-54`) put the duplicate in two adjacent rows.

### 2.2 What already does this?

**Which existing mechanism serves "prevent a second paid producer", and why is it insufficient?**

`serve_model_charge` serves it, and it is **not** insufficient. `[VERIFIED: 0012:7-13]` one row per
`(owner_id, doc_key, day)`; `[VERIFIED: 0020:217-223]` reclaim only after `lease_expires_at < now()`;
`[VERIFIED: 0020:226-235]` a live lease returns `in_flight` so no second producer starts.

`docs/adr/0007-artifacts-are-an-append-only-log.md:129` already names it *"a third coordination
vocabulary"* — flagged as a smell one week before this spec. v3 proposed a **fourth**, for the concern
the third owns.

The lease fails in exactly one way: **when the work outlasts it.** That is not a coordination gap. It
is an inequality, and §3 fixes the inequality.

**Who are the writers?** One class. `[VERIFIED: design-review-r4.md:31-47]` HTML
(`app/api/html/[id]/route.ts`) and PDF (`app/api/pdf/[id]/route.ts`) are *entrypoints* through the same
`serve-summary-core.ts:105`, carrying the same `auth.uid()`. Local generation never reserves
(`generate.ts:40-50`); cloud sync copies bytes and does not produce (`sync-run.ts:437-465`).

**With one writer class there is nothing to negotiate**, which is why v3's cross-authority protocol had
no counterparty and spent six mechanisms keeping two numbers in agreement.

---

## 3. Design

### 3.0 Why there is no runtime deadline — and what that costs

v3 needed a `Deadline` object, a monotonic `t0`, a DB→app budget channel and unit conversions because
the budget was **dynamic** — discovered per request from the database.

It does not need to be. If every call carries a fixed timeout, the worst case is a **static sum
computed at build time**. A constant cannot be stale, cannot be measured against the wrong clock, and
cannot arrive late. Transport latency, seconds-vs-milliseconds, the viability check and the floor
column were all defects in machinery that existed *only* to move that number around; deleting the
machinery deletes the class.

**What is genuinely given up (round-5 Low).** A runtime deadline bounds *unmodelled* overhead — work
nobody thought to put in the sum. A static sum does not: **an omission stays invisible until
production.** Round 5 proved the point by finding two omissions (the reserve and settle RPCs) in v4's
sum.

The compensating control is §3.2's split: every term in the sum is now enforced by an actual timeout,
and everything unenforceable is quarantined into one named margin. A term that is merely *added* is
the failure mode — v4 had one (`SETTLE_SLACK_MS`) and it was a Blocking.

### 3.1 Bound every call — including the Supabase ones

**v4 claimed "bound each external call" while leaving both RPCs unbounded (round-5 M2). They are
external calls; they are bounded here.**

| call | today | v5 |
|---|---|---|
| `reserve_serve_model` RPC (`serve-doc.ts:74`) | bare await | `RESERVE_RPC_TIMEOUT_MS` |
| `countTokens` (`gemini.ts:82`) | bare await | `COUNT_TOKENS_TIMEOUT_MS` |
| `generateContent` (`gemini.ts:259`) | `REQUEST_TIMEOUT_MS` (60 s) | `SERVE_ATTEMPT_TIMEOUT_MS` (50 s), serve path only |
| attempts (`gemini.ts:256`) | 3 | **2**, serve path only |
| `blobStore.put` (`model-store.ts:51`) | bare await | `PUT_TIMEOUT_MS`, caller-side race |
| `settle_serve_model` RPC (`serve-doc.ts:126`, `:133`) | bare await | `SETTLE_RPC_TIMEOUT_MS` |

**The Supabase client supports this.** `[VERIFIED: @supabase/postgrest-js 2.109.0 —
dist/index.d.mts:5246-5254 and :1408]` `rpc()` returns a `PostgrestFilterBuilder` carrying
`abortSignal(signal: AbortSignal): this`; the package's own example is
`abortSignal(AbortSignal.timeout(1000))`. Version pinned in the tag because a capability claim without
one is a premise that silently expires. `[VERIFIED: lib/supabase/server.ts:10-20]` sets no timeout
today, which is why both RPCs are currently unbounded.

**What a bounded RPC does and does not do.**

- *Reserve:* a timeout means we stop waiting. It does **not** roll back the transaction — the lease may
  have been granted and charged. So on a reserve timeout the app **abandons without producing**: no
  Gemini call, no write.

  **v5 called this "safe because single-flight is preserved". That is the wrong description
  (round-6 M1).** What exists after a reserve timeout is an **empty paid lease**: 6¢ charged, an
  `attempt_count` burned, and *no producer at all*. Concretely — the user sees `busy`; retries before
  expiry see `in_flight` and are refused although nobody is generating; retries after expiry can burn
  another 6¢ and another attempt. Bounded by `max_serve_attempts` and the daily cap, not by anything
  in this design. Logged loudly; a recurring reserve timeout is an infrastructure alarm, and this
  state is why.

- *Settle:* a timeout means we stop waiting; the statement may still commit. It is **not** a
  cancellation, and the spec must not imply one. Its purpose is solely to stop a hung settle from
  running past the lease — but see §4.1, because on the **release** path that is not free.

**The Gemini SDK supports the preflight bound.** `[VERIFIED: generative-ai.d.ts:778]`
`countTokens(request, requestOptions?: SingleRequestOptions)` and `[VERIFIED: :1297-1306]`
`SingleRequestOptions extends RequestOptions` with `signal?: AbortSignal`.

**The retry/timeout reduction needs a real option — v4's "one-argument change" was wrong (round-5
H1).** `generateJson` takes `retries` `[VERIFIED: gemini.ts:251]`, but `generateMagazineModel` has no
such parameter `[VERIFIED: gemini.ts:499-505]`, and `html-doc/generate.ts:40` calls it on the **local**
path. Changing `gemini.ts:549` from `undefined` to `1` would silently reduce local generation's
retries too.

**v5 proposed an OPTIONAL `opts.serve?`. That repeats a failure this project has already written down
(round-6 H1).** `process-checklists.md:64-68`: *"Make the new member **required, not optional**: an
optional one does not propagate, and callers keep silently inheriting the ambiguous original."*

The concrete failure it permits: the serve caller keeps passing `{ caps, signal, billing }`, TypeScript
accepts it, the direct unit tests that pass `opts.serve` go green — and **production serves with 3
attempts at 60 s while the CHECK floor assumes 2 at 50 s.** The floor would then be wrong in the one
configuration nobody tested, which is the entire failure this spec exists to prevent.

**So the serve boundary gets its own entry point, where omission cannot compile:**

```ts
// lib/gemini.ts — the serve path calls THIS, never generateMagazineModel directly
export function generateMagazineModelForServe(
  sections, language,
  budget: ServeBudget,          // REQUIRED — no default, no `?`
  opts?: { caps?: CloudGeminiCaps; signal?: AbortSignal; billing?: BillingLatch },
): Promise<MagazineModel>
```

`generateJson` gains an optional `timeoutMs` defaulting to `REQUEST_TIMEOUT_MS` — optional is correct
*there*, because that default is the existing behaviour for every existing caller and the serve path
reaches it only through the wrapper above, which cannot omit the budget.

A wrapper rather than a required parameter on `generateMagazineModel` itself, because the latter would
force `html-doc/generate.ts:40` (the local path) to pass a serve budget it has no business knowing
about. **The boundary that must not be crossed silently gets its own name.**

### 3.2 The worst case: enforced terms, and one quarantined margin

```
BOUNDED — every term is a timeout the code actually applies
  RESERVE_RPC_TIMEOUT_MS                       5_000
  COUNT_TOKENS_TIMEOUT_MS                     10_000
  SERVE_ATTEMPTS * SERVE_ATTEMPT_TIMEOUT_MS  100_000   (2 * 50_000)
  SERVE_BACKOFF_TOTAL_MS                         400   (one gap between two attempts)
  PUT_TIMEOUT_MS                              15_000
  SETTLE_RPC_TIMEOUT_MS                        5_000
                                             -------
  SERVE_BOUNDED_MS                           135_400

UNBOUNDABLE — cannot be timed out, so it is margin, not budget
  SERVE_MARGIN_MS                             20_000

  SERVE_FLOOR_MS      = 135_400 + 20_000  =  155_400
  SERVE_FLOOR_SECONDS = ceil(155_400/1000) =     156
```

**The split is the point.** `SERVE_BOUNDED_MS` is a promise the code keeps: each term corresponds to a
timeout that fires. `SERVE_MARGIN_MS` is an *assumption* covering what no timeout can bound — JS
scheduling, GC pauses, `JSON.parse`, Zod validation, `mdHash`, prompt construction, client
construction, TLS setup. It is labelled an assumption everywhere it appears.

v4 blurred these into one addition and shipped `SETTLE_SLACK_MS` — a guess with a budget's name — which
round 5 made a Blocking. **A term that is only added is not a bound.**

**The floor is not the worst case (round-5 M1).** v4 set the floor equal to its sum, leaving 600 ms at
the legal minimum: any operator choosing the floor converted millisecond variance into duplicate paid
producers. Here the floor *includes* the 20 s margin by construction, so the minimum legal
configuration still carries 20 s of unmodelled-overhead headroom.

| constant | status | basis, and what would revise it |
|---|---|---|
| `REQUEST_TIMEOUT_MS` | **exists** — `gemini.ts:94` | unchanged; still 60 s off the serve path |
| `SERVE_ATTEMPT_TIMEOUT_MS = 50_000` | **new** | 60 s does not fit two attempts plus the enforced terms. Revise with observed magazine latency |
| `SERVE_ATTEMPTS = 2` | **new** | §3.5 |
| `COUNT_TOKENS_TIMEOUT_MS = 10_000` | **new, provisional** | never measured. Revise from p99 once timeout logs exist |
| `PUT_TIMEOUT_MS = 15_000` | **new, provisional** | one small-JSON upload. Revise from p99 |
| `RESERVE_RPC_TIMEOUT_MS = 5_000` | **new, provisional** | one round trip to Postgres. Revise from p99 |
| `SETTLE_RPC_TIMEOUT_MS = 5_000` | **new, provisional** | as above |
| `SERVE_MARGIN_MS = 20_000` | **new, an assumption** | ~13 % of the bounded budget for unmodelled local work. **Revise upward on any observed lease expiry that the bounded terms cannot explain** |

All live in `lib/serve-budget.ts`, so the sum has one home and the migration literal has one thing to
be pinned against.

### 3.3 The constraint is the whole agreement

```sql
-- migration 0024
alter table guardrail_config drop constraint <lease_ttl_check>;   -- read the generated name first
alter table guardrail_config add  constraint guardrail_config_lease_ttl_covers_serve
  check (lease_ttl_seconds >= 156);                               -- = SERVE_FLOOR_SECONDS
```

Today `[VERIFIED: 0012:22]` `check (lease_ttl_seconds >= 1)` — a one-second lease is legal, which is
exactly why v3 believed adequacy could only be discovered per request. Raise the floor and the
inequality holds **once, at configuration time, for every request forever**.

`[unverified]` the existing constraint's generated name — it is inline and unnamed in `0012:22`. Read
it from `pg_constraint` during implementation rather than guessing.

**What the constraint can and cannot prove (round-5 B1).** v4 claimed the floor established the
inequality. It did not, because the reserve RPC's *response transit* was omitted from the sum and is
unbounded: the lease begins when the DB commits, and a stalled response can exceed **any** floor.

The floor is sound **only because §3.1 bounds the reserve call.** With that bound, the time between
lease start and the app's first action is at most `RESERVE_RPC_TIMEOUT_MS`, which is a term in the sum.
The constraint and the client timeout are one mechanism in two places, not two mechanisms: **neither
is sufficient alone, and the spec is wrong wherever it implies the constraint alone suffices.**

### 3.4 What is deliberately NOT changed

| | why |
|---|---|
| `reserve_serve_model` / `settle_serve_model` signatures | nothing is declared; the constraint plus the client timeouts hold the invariant |
| `BillingLatch` | `attempted` existed only to classify deadline aborts, which are no longer a designed path |
| the refund rule | **v3 silently revoked the 429/503 refund** (round-3 B1). `classifyGeminiFailure` + `!metered` stays exactly as shipped |
| `guardrail_config` columns | no floor column, no drift gate to defend it |
| `BlobStore.put`'s signature | a timeout is caller-side; the three adapters are untouched |

### 3.5 The two real trades

**Attempts 3 → 2, and 60 s → 50 s per attempt, on the serve path only.** The current third attempt is
what pushes the worst case past the lease, and an overrun costs a second 6¢ charge plus an
`attempt_count` burn — worse for the same user than a clean failure they can retry.
`max_serve_attempts` (default 5) still governs retries across requests. Local generation is unaffected
(§3.1).

**A late `put` can overwrite a newer model (round-5 H2).** v4 called an abandoned upload "benign". That
is true against nothing, and false against a **later producer**: A's `put` times out, B reserves and
writes a fresh model, then A's original upload completes with `upsert:true` and overwrites B.

The caller-side race cancels our *wait*, never the upload — the same vendor asymmetry as an aborted
Gemini call, one layer out.

**v5 claimed this was bounded to one extra generation. That claim was false (round-6 B1), and the
correction matters more than the original error.**

`[VERIFIED: lib/html-doc/read-model.ts:20-24]`

```ts
export function isFresh(envelope, titles): boolean {
  return sameTitles(envelope, titles) && envelope.generatorVersion === GENERATOR_VERSION;
}
```

**`sourceMdHash` is not read here.** `[VERIFIED: grep]` its only readers are on the sync path
(`lib/cloud-sync/companion.ts:97-139`). `companion.ts:43` states the asymmetry outright — the serve
freshness check uses *"generatorVersion, never sourceMdHash"*.

v5 asserted the hash was compared, and labelled the assertion *traced*. It traced `sourceSections` and
inferred the rest from the field's existence in the envelope schema. **A field being written is not
evidence that anything reads it** — the refutation was sitting in a comment in the repo.

**The real consequence.** If A's late upload overwrites B's newer model and the section **titles** are
unchanged — the common case, since editing prose rarely changes headings — `isFresh` returns true and
the stale model is served **indefinitely**, until titles change or `GENERATOR_VERSION` bumps. That is
silent, user-visible stale content, not a bounded extra charge.

### 3.5.1 Decision: the residual is ACCEPTED, and it is not this task's to fix

Three options were live. Recorded because a residual accepted without alternatives is indistinguishable
from one nobody noticed.

| option | why not chosen |
|---|---|
| Make `isFresh` compare `sourceMdHash` | Closes it, but changes serve-path **caching**, not timeouts. `companion.ts:43` indicates ignoring the hash is deliberate: it stops a prose-only MD edit forcing a paid regeneration. Flipping that is a **money** decision needing its own reasoning, not a rider on a timeout fix |
| Leave `put` unbounded | That is the live production defect this task exists to fix |
| **Accept, document, and route the fix** | ✅ chosen |

**Where the real fix lives:** making a write unable to clobber a newer one is *content addressing*, which
is already owned by **backlog #25 / task #39** (render addressing). This spec must not invent a fourth
coordination mechanism for it — inventing one is precisely how v1–v3 burned three rounds.

**Preconditions for the residual to bite:** A's `put` must exceed `PUT_TIMEOUT_MS` (15 s for one small
JSON — already pathological), *then* succeed later, *and* B must write in that interval, *and* the
titles must be unchanged. Rare. Not impossible, and no longer described as bounded.

**Detection, since prevention is out of scope:** a `put` timeout is logged with elapsed time and the
target key, so the window in which this is possible is visible in production rather than inferred. If
those logs ever appear, that is the trigger to promote the addressing work rather than to tune
`PUT_TIMEOUT_MS`.

---

### 3.6 Diagrams

### Budget: the worst case against the lease

```mermaid
gantt
    title Serve budget — 135.4s enforced + 20s margin = floor 156s, inside a 180s lease
    dateFormat X
    axisFormat %ss

    section Lease
    lease_ttl_seconds = 180 (CHECK floor 156)   :active, 0, 180

    section Enforced by a timeout
    reserve RPC (5s)                :a0, 0, 5
    countTokens (10s)               :a1, 5, 15
    generateContent attempt 1 (50s) :a2, 15, 65
    backoff (0.4s)                  :a3, 65, 65
    generateContent attempt 2 (50s) :a4, 65, 115
    blobStore.put (15s)             :a5, 115, 130
    settle RPC (5s)                 :a6, 130, 135

    section Assumption, not a bound
    SERVE_MARGIN_MS (20s)           :crit, 135, 155

    section Spare
    headroom at the default (24.6s) :done, 155, 180
```

The whole design is this picture, and the section labels carry the round-5 lesson: everything above
the margin is a promise the code keeps, the margin is an **assumption** about work no timeout can
bound, and §3.3 makes the total true for every configuration the database will accept.

v4's version of this chart had no `reserve RPC` bar, no `settle RPC` bar, and a 600 ms gap between the
work and the lease. Two of those omissions were Blocking findings — **the diagram would have shown
them if it had been drawn from the await list rather than from the prose.**

### The serve path

```mermaid
sequenceDiagram
    autonumber
    actor U as HTTP GET (owner)
    participant S as serve-doc.ts
    participant DB as Postgres
    participant G as Gemini
    participant B as BlobStore

    U->>S: GET summary
    S->>B: tryGet(model)
    alt cached and fresh
        B-->>S: bytes
        S-->>U: 200 — no RPC, no charge
    else absent or drifted
        S->>DB: reserve_serve_model() [timeout 5s]
        Note over DB: lease starts HERE, at commit —<br/>the return trip is already spent
        DB-->>S: reserved + release_token
        Note over S,DB: signature unchanged from today —<br/>no requirement, no budget returned
        S->>G: countTokens [timeout 10s]
        G-->>S: totalTokens
        S->>G: generateContent [timeout 50s, up to 2 attempts]
        G-->>S: model
        S->>B: put(model) [timeout 15s]
        B-->>S: ok
        S->>DB: settle_serve_model(token, released := false) [timeout 5s]
        S-->>U: 200
    end
```

No `alt` blocks before the work begins. That absence is the redesign.

The `lease starts HERE` note is round-5 B1 in one line: the lease begins when the DB commits, so the
response's return trip is already spent when the app receives it. That is why the reserve call carries
a timeout — without it the term is unbounded, and **no CHECK floor can prove an inequality containing
an unbounded term.**

### Money: which failures refund

```mermaid
stateDiagram-v2
    [*] --> Reserved: reserve_serve_model() — 6¢ charged
    Reserved --> Generating: countTokens ok
    Generating --> Persisting: generateContent ok
    Persisting --> KeptOk: settle(released := false)

    Generating --> Refunded: 429 / 503 / NonRetryableError<br/>and NOT metered
    Generating --> Kept: any timeout, or metered
    Persisting --> Kept: put timeout

    KeptOk --> [*]
    Kept --> [*]
    Refunded --> [*]

    note right of Refunded
        UNCHANGED from production today.
        classifyGeminiFailure + !billing.metered.
        v3 would have removed this path.
    end note
```

---

---

## 4. Error handling

**Nothing about the money rule changes.** `classifyGeminiFailure(err, signal)`
`[VERIFIED: gemini-failure.ts:76-86]` plus `!billing.metered` at `serve-doc.ts:130-132` decides refunds
exactly as shipped: 429/503 and `NonRetryableError` refund when not metered; everything else keeps.

A **timeout** is an `AbortError`: `ourSignal?.aborted` is false (the timeout aborts a different
signal), the cause chain matches neither `NonRetryableError` nor `GeminiHttpError`, so it falls to
`'keep'` at `:85`. The charge is kept, which is correct — `[VERIFIED: generative-ai.d.ts:1302-1304]`

> NOTE: AbortSignal is a client-only operation. Using it to cancel an operation will not cancel the
> request in the service. **You will still be charged usage for any applicable operations.**

Cancellation is **not a cost-control mechanism**. It protects the lease, never the bill.

**Reserve timeout** → abandon without producing (§3.1), surface `busy` (transient, retryable — the same
meaning it already carries at `serve-doc.ts:84`), and log. No Gemini call has been made and no
`release_token` is in hand, so there is nothing to settle.

### 4.1 The settle timeout is NOT free on the release path (round-6 B2)

**v5 said "the refund rule is unchanged". Delete that claim — it is true of the rule and false of the
outcome.**

The rule at `serve-doc.ts:130-132` is untouched. But bounding the RPC that *executes* it changes what
happens:

| settle | on timeout | consequence |
|---|---|---|
| `p_released := false` (kept) | statement commits or the row is reclaimed at expiry | benign — money was already correctly kept |
| **`p_released := true` (refund)** | **if the statement never commits, the refund never happens** | `spend_ledger.reserved_cents` and `serve_owner_budget.spent_cents` stay +6¢, `release_token` stays set |

Concretely: reserve succeeds, Gemini throws a **not-metered 503**, `released = true`, the settle times
out and does not commit. The user keeps a charge that the system decided to refund, and the caller has
lost the token, so nothing retries it.

**Direction, which decides how serious this is.** An unapplied refund is an **over-count** — the
ledger holds more than was spent. This codebase's standing rule (`serve-doc.ts:107-110`) is that
over-count is safe and under-count is the bug. So this is real money and not a correctness violation,
which is why it is mitigated rather than made impossible:

> **On the release path only, the settle is retried once** within `SETTLE_RPC_TIMEOUT_MS`, which
> `SERVE_MARGIN_MS` covers. On the kept path there is nothing to retry — the charge is already correct.

**The residual is stated, not dismissed:** if both attempts fail, the refund is lost and no reaper
reconciles it. `ledger_audit` (`0020:12-19`) records release *underflow* at settle time and cannot
record a settle that never arrived.

`★` The general shape, since this is its second appearance in this spec: **a rule can be preserved
verbatim and still stop working when you bound the mechanism that carries it out.** v3 revoked this
same refund by rewriting the rule; v5 revoked it by bounding its transport. "Unchanged" must be a claim
about the outcome, or it is not a claim at all.

### 4.2 Settle timeout, kept path

The work is done and the model is written; only our acknowledgement was lost. Log and return the
successful result. The reservation clears when the statement commits, or the lease expires and the row
is reclaimed — the existing behaviour for any lost settle.

---

## 5. Testing

**The sum, term by term.** `SERVE_BOUNDED_MS` equals the sum of its six terms; `SERVE_FLOOR_MS` equals
`SERVE_BOUNDED_MS + SERVE_MARGIN_MS`; `SERVE_FLOOR_SECONDS <= 180`, the shipped `lease_ttl_seconds`
default. Write this first and watch it fail against today's constants (181,200 > 180,000) — the
assertion that would have caught §1.2.

**Every bounded term is actually bounded.** One test per row of §3.1's table: reserve, `countTokens`,
`generateContent` and settle each abort at their timeout rather than hanging. **This is the test that
distinguishes v5 from v4** — v4's `SETTLE_SLACK_MS` would have passed a sum test and failed this one.
Assert the error *identity*, not that "something failed".

**`put` is the exception, and the test must say so (round-6 M2).** `[VERIFIED:
lib/storage/supabase/supabase-blob-store.ts:22-24]` maps to Supabase Storage `upload(..., {upsert:
true})` with **no signal**. So the test asserts the **caller's race resolves** at `PUT_TIMEOUT_MS` — it
cannot assert the upload was cancelled, because it is not. Writing it the other way would be a test
asserting a behaviour the stack does not have, and the difference is exactly what makes §3.5's residual
possible.

**The margin is not a bound, and the tests must not imply it is.** There is no test for
`SERVE_MARGIN_MS`; it is an assumption. What *is* asserted is that it appears only in `SERVE_FLOOR_MS`
and never as a timeout argument.

**Serve-only-ness (round-5 H1, round-6 H1).** `generateMagazineModel` — the un-wrapped entry point —
still uses `GENERATE_JSON_RETRIES` and `REQUEST_TIMEOUT_MS`, asserted against the local caller
(`html-doc/generate.ts:40`). `generateMagazineModelForServe` uses 2 attempts at 50 s.

**And assert the serve route reaches the wrapper**, not `generateMagazineModel` directly. The required
`budget` parameter makes omission a compile error, so this test guards the remaining hole: someone
calling the un-wrapped function from the serve path on purpose. A grep-style import guard is
appropriate — the repo already uses one at `tests/lib/share/import-guard.test.ts`.

**The attempt count.** At most 2 `generateContent` calls on the serve path. Mutate the option away and
this must go red, or it asserts nothing.

**The refund DECISION is unchanged, so pin it.** 429 while not metered still calls settle with
`p_released := true`. v3 would have broken this by rewriting the rule and nothing would have noticed.

Assert the **decision** and the **outcome** separately, because §4.1 is precisely the case where they
diverge: v5 preserved the decision and broke the outcome by bounding the RPC that carries it. A test
asserting only "settle was called with released=true" passes while the refund never lands.

**Late-`put` overwrite — assert the RESIDUAL, not a fix (round-6 B1).** v5 wanted a test proving drift
detection regenerates. That test would fail, because `isFresh` does not read `sourceMdHash`
(§3.5). The accepted residual (§3.5.1) is instead pinned by a **characterisation test**: an envelope
whose `sourceMdHash` differs but whose titles match IS served as fresh.

That test documents the known gap and, more usefully, **goes red the day someone makes `isFresh`
hash-aware** — at which point whoever does it finds this spec's reasoning attached to the failure
rather than having to rediscover it. A residual with no test is indistinguishable from an oversight.

**Refund survives a settle timeout (round-6 B2).** On the release path, a first settle that times out
must be retried once. Assert the retry happens *and* that a double failure leaves the charge kept —
an over-count, the safe direction — rather than silently reporting success.

**Schema.** `scripts/check-schema-gates.sh`, plus a mutation on the constraint: lower the floor back to
1 and an integration test inserting `lease_ttl_seconds = 30` must stop failing. An unmutated guard is
undemonstrated.

**Anti-drift.** The migration's literal `156` must equal `SERVE_FLOOR_SECONDS` from
`lib/serve-budget.ts`. A migration literal cannot import a TypeScript constant, so this assertion is
the only thing between a tuned constant and a floor that no longer covers the work.

---
## 6. Deploy ordering

The constraint must not be applied while a deployed installation has `lease_ttl_seconds < 156`, or the
migration fails on a live database.

1. Read the current value in each environment. `[unverified]` — production's configured
   `lease_ttl_seconds` has not been checked against the live database in this session, and the memory
   note on out-of-band changes says the doc is not evidence. **Check before applying.**
2. If any environment is below 156, raise it first, in its own step.
3. Then apply 0024, then deploy the app.

App and schema are **not** coupled this time: the app change is safe with or without the constraint,
and the constraint is safe with or without the app. That independence is a direct consequence of
deleting the protocol — v3 required function-before-app ordering plus a column-before-function
constraint within the migration.

---

## 7. The trail

### 7.1 Rounds 1–3: what was found, and why it was the wrong question

21 findings, all confirmed against the code. They are preserved in
`docs/reviews/spec-serve-deadline-codex-r{1,2,3}.md` and are worth reading as a record of how a wrong
shape emits real defects indefinitely.

The pattern, from [`review-method.md:40-43`](../../review-method.md): *adversarial review answers "is
this correct?", a local question, and a local question can always be answered yes by patching.* Three
rounds of correct answers to the local question.

Highlights worth carrying forward:

- **r3 B1 — v3 silently revoked the existing 429/503 refund.** A fix for a money finding introduced a
  money regression against deliberately-designed production behaviour. v4 changes nothing here (§3.4).
- **r2 B3 + r3 H3 — "`countTokens` is free" and "built from existing constants" were both unverified
  claims presented as facts.** §3.2 now labels every new constant as new.
- **r2 B2 — seconds versus milliseconds**, in a spec whose subject was numbers that don't agree.
- **The instrument that would have caught all of it** was the §2 coherence table, skipped before
  approval. It takes ten minutes and shows one concern with three mechanisms.

### 7.2 Round 4: the design review

`docs/reviews/spec-serve-deadline-design-review-r4.md` — **VERDICT: REDESIGN**, reached independently
from the same evidence: one concern with two mechanisms (`:53-54`), one writer class (`:31-47`),
ADR-0007 already naming `serve_model_charge` a third coordination vocabulary (`:17`).

It recommended shape (b) and named the one thing (b) gives up (`:80`) — that Postgres would not reject
an operator who lowers `lease_ttl_seconds` below the app's bound. **§3.3 closes that hole in one line**,
which the review did not propose. The verdict is adopted; its accepted loss is not.

### 7.3 Round 5: the redesign's first adversarial round

`docs/reviews/spec-serve-deadline-codex-v4-r5.md` — NOT CONVERGED, 7 findings, all confirmed.

| # | Finding | Disposition |
|---|---|---|
| B1 | the sum omits the reserve RPC wait, so the CHECK floor proves nothing | **Accepted** — §3.1 bounds the reserve call; §3.3 now states the floor is sound *only* with that bound |
| B2 | `SETTLE_SLACK_MS` is not an enforced bound but is treated as one | **Accepted** — §3.2's enforced/assumption split; settle is bounded |
| H1 | the retry reduction is not serve-path-only | **Accepted** — §3.1 adds an explicit option; v4's "one-argument change" claim was wrong |
| H2 | a late `put` can overwrite a **newer** model | **Accepted** — §3.5 states it, traces the bound (drift → regeneration), stops calling it benign |
| M1 | 600 ms margin at the floor is non-survivable | **Accepted** — the floor now *includes* a 20 s margin by construction |
| M2 | "bound every call" was false for the Supabase calls | **Accepted** — §3.1 |
| Low | v4 lost v3's live remaining-time guard without saying so | **Accepted** — §3.0 |

**None of these is a regression from a previous round's fix**, which is the first time that has been
true in this spec's history. The escalation rule (`review-method.md:45-47`) counts *"findings caused by
the previous round's fixes"* — round 5's are first-pass findings on a new artifact, and §2.1's
concern→mechanism table is byte-identical to v4's. The design absorbed seven findings without growing
a mechanism.

**The two Blocking findings share one root, and it is worth naming.** v4 wrote a budget from the
*prose* — the calls it had been thinking about — rather than from the **await list**. Enumerating every
`await` between the charge and the settle, which round 5's audit did mechanically, found two the prose
never mentioned. A static budget is exactly as good as the enumeration behind it, and the enumeration
is a mechanical act that was skipped.

**What would have caught it earlier:** drawing the Gantt chart from the await list rather than from the
design's narrative. The chart in §3.6 now has a bar per enforced term, so a missing term is a visible
gap rather than a silent omission in an addition.

### 7.4 Round 6: the redesign's second round

`docs/reviews/spec-serve-deadline-codex-v5-r6.md` — NOT CONVERGED, 5 findings, all confirmed, all
introduced by v5's fixes.

| # | Finding | Disposition |
|---|---|---|
| B1 | late-`put` still unbounded — `isFresh` ignores `sourceMdHash` | **Accepted; residual ACCEPTED by decision** — §3.5.1, fix routed to backlog #25 / task #39 |
| B2 | bounding the settle silently revokes the refund on the release path | **Accepted** — §4.1, one retry, residual stated, "unchanged" claim deleted |
| H1 | `opts.serve?` repeats the optional-boundary failure | **Accepted** — §3.1, a required-parameter wrapper instead |
| M1 | reserve timeout leaves an *empty paid lease*, not single-flight | **Accepted** — §3.1, the state is now described exactly |
| M2 | the `put` abort test cannot be written truthfully | **Accepted** — §5, it asserts the caller's race |

**Four of the five are prose that overstated what the design does.** The design did not change: §2.1's
concern→mechanism table is byte-identical to v4 and v5. B1 is the only one requiring a decision, and
the decision was to accept a residual rather than add a mechanism.

**Two findings are the same lesson at different layers, and both are mine.** B1: I checked that
`sourceMdHash` was *written* and inferred that it was *read*. B2: I checked that the refund *rule* was
unchanged and inferred that the refund still *happened*. In both cases the artifact existed and the
consumer did not — and in both cases the refutation was already in the repo, in
`read-model.ts:20-24` and in `companion.ts:43`.

> **The rule this spec earns:** *a claim about behaviour must cite the code that PERFORMS it, never the
> code that prepares it.* A written field, a preserved rule, a declared constant — none of them do
> anything. Cite the reader, the executor, the consumer.

### 7.5 Why Phase 2 rather than a seventh round

Round 6's findings are questions about **what the code does**, asked of a document with no code:
whether an optional parameter propagates, whether a test can be written truthfully, what a timeout does
to one specific RPC. Review answers those by argument; the compiler and the suite answer them by
execution, immediately and without a round trip.

The evidence that the *shape* has converged, which is the thing spec review is actually for:

| | rounds 1–3 | rounds 5–6 |
|---|---|---|
| findings asking for a **new mechanism** | 6 | **0** |
| changes to §2.1's concern→mechanism table | rewritten each round | **none since v4** |
| findings that are prose vs. design | mixed | 4 of 5 prose |

**This is not skipping a gate.** `dev-process.md:82` — Phase 2 plans carry their own dual adversarial
review to convergence. The artifact under review changes from prose to enumerated behaviours and named
tests, which is a strictly harder thing to be wrong in: H1's failure mode (the option not passed) is a
compile error there, and M2's (an unwritable test) is discovered by trying to write it.

**The honest risk:** B1 was a design-level defect found in round 6, so spec review had not stopped
paying entirely. It was found by *reading code* — which is what a plan does more of than a review does.

## 8. Out of scope

The BlobStore **object-age** seam remains task #44. Cloud-sync, generation and dig paths are untouched:
this spec changes the serve path's timeouts and one CHECK constraint.
