# Conditional Write on `persist_summary` — Design Spec

**Status:** v1 DRAFT — gates unrun (`grill-with-docs`, dual adversarial review to convergence)
**Backlog:** #17 (durable fix; the partial mitigation shipped 2026-08-04 as PR #45)
**Task:** #19
**Supersedes nothing.** Feeds the migration described in
[`2026-08-03-stable-blob-addressing-design.md`](2026-08-03-stable-blob-addressing-design.md) §5.1.

---

## 0. The idea in plain terms

**A worker writes to an address that someone else moved while it wasn't looking.**

The worker decides *where* a summary will be stored at the start of the job, then spends minutes
generating it. Sync can move that address in the meantime. Nobody checks, so the late write lands at
the old address and the row ends up half-right — pointing at one place while its paid dig files sit
in another.

**The fix is one sentence: don't write unless the serial you read is still the serial.**

That is a **conditional write** (compare-and-swap, "CAS"), and it is the same rule as `git push`
refusing a non-fast-forward: *if the thing moved since you looked, your write is stale — go re-read
and try again.* It costs one extra condition on an `UPDATE`. The condition itself — "the serial is
still the one I read" — is the **serial guard**.

> **Terminology — this is NOT lease fencing.** "Fencing" is already taken in this codebase
> (`0008_jobs_queue.sql:94`, `0009:55`) and means the standard thing: a lease-token check that stops
> a stale lease-holder from acting. That mechanism **cannot** solve this problem, because the worker's
> lease never expires here — it stays valid the whole time, and what goes stale is the *serial*, which
> no lease knows about. Backlog #17 is titled "fence the worker persist"; the title names the wrong
> mechanism and is kept only because it is referenced from commits, memory and the roadmap.

### The address has two moving parts — this guards ONE of them

Be precise about what is protected, because the shorthand "the address moved" hides a real gap:

```
base = pad(serialNumber) + '_' + slugify(title)
        └──── guarded ────┘      └── NOT guarded ──┘
```

A serial guard sees the serial move. It does **not** see the *slug* move. And the slug can move on its
own: re-summarizing a video whose YouTube title changed keeps the same serial and produces a new base,
which orphans every dig blob under `dig/<old-base>/` — the same paid content, the same damage, reached
without any concurrency at all.

That is **out of scope here and filed as backlog #20**, because it is not a race: it needs no second
writer and no window, so it needs a different fix. It is named here so that no reader concludes from
this spec that base addressing is now fully protected. It is not. This closes the concurrent half.

Nothing validates the slug half today. `checkSerialInvariant` (`lib/serial-invariant.ts:54`) looks like
it would, but it derives its expectation with `applySerial(value, serial)` — which copies the slug out
of the very value being checked, so the slug comparison can never fail.

### Sources and the sink

The most useful way to hold this design is **sources versus the sink**.

| | | |
|---|---|---|
| **Sources** | The places that **move** an address | A3 relocation, `copyAdditiveVideo`, whatever gets added next |
| **Sink** | The one place a stale write **lands** | `persist_summary` |

There are several sources and there will be more. There is exactly one sink.

**So guard the sink, not the sources.** Guarding sources means N guards that must each be written,
each be correct, and each be remembered by whoever adds source N+1. Guarding the sink means one guard
that is automatically right about sources nobody has thought of yet.

This is the correction to backlog #17, which assumed the fix had to be applied along the whole sync
write path. It doesn't — and that single insight is most of why this slice is small.

---

## 1. The problem

A worker generating a summary pins its blob address **minutes before** it writes. If sync relocates
that video's base inside the window, the stale write still lands, and the row ends up carrying two
halves of an identity that disagree — with **paid dig content** stranded at the address nobody points
at any more.

The interleaving was confirmed in round 5 of `fix/serial-coherence-sync` (2026-08-03):

| Step | Actor | Effect |
|---|---|---|
| 1 | worker | `reserveVideoSlot` → serial `7`; pins `baseName = 007_alpha` (`summary-handler.ts:95-96`) |
| 2 | worker | transcription + Gemini — **minutes** |
| 3 | sync | A3 relocates: serial `7` → `3`, copies paid digs to `dig/003_alpha/`, deletes `dig/007_alpha/*` |
| 4 | worker | `persistSummary(…, video, 'committed')` (`summary-handler.ts:177`) |
| 5 | — | row = `serialNumber 3` **beside** `summaryMd 007_alpha.md`; digs stranded at `dig/003_alpha/` |

Step 5 is not a cosmetic inconsistency. `serialNumber` is what every subsequent reader derives the
base from, so the paid digs at `dig/003_alpha/` are unreachable from a row advertising `007_alpha.md`,
and the MD blob at `007_alpha.md` is unreferenced by the serial. Recovering the digs costs fresh
Gemini spend for content already paid for.

### 1.1 Why the row ends up incoherent

**The address has two halves, and they come from two different places.** One is trusted to the row,
the other to the job — so when they disagree, nothing notices.

`persist_summary` (`0021_cloud_sync_signals.sql:99-153`) sources them from **different writers**, and
the asymmetry is deliberate on both sides:

- **`serialNumber` comes from the row.** The whitelist at layer (3) (`:121-134`) does not list it, so
  layer (2) — `|| (v.data - 'artifacts')` — restores the row's own value. This is by design: it is what
  stops a stale job payload reverting operational state a concurrent writer changed.
- **`summaryMd` comes from the payload.** Line `:133` resolves
  `coalesce(p_video->>'summaryMd', v.data->>'summaryMd')` — **payload wins**. Also by design: writing
  that key is the entire purpose of the job.

Neither rule is wrong alone. The defect is that nothing asserts the payload's key and the row's serial
describe the *same* base.

### 1.2 What the shipped mitigation does and does not close

PR #45 (`reconcile-serial.ts:240-251`) makes A3 refuse to relocate while a job for that video is
pending or recently swept. That closes the **wide** window — the minutes at step 2.

It does not close the residual one. The refusal is checked once, before the copy phase, and that copy
phase is a loop of N sequential blob round-trips (`reconcile-serial.ts:232-236`). A job enqueued and
claimed inside that span reads the pre-relocation serial and is invisible to a probe that already ran.
The comment at `:236` states the honest scope: *"a large reduction, not an elimination."*

Widening the freshness check cannot fix the residual, for the reason recorded in backlog #17: **when
A3 checks, the worker has written nothing.** Its write lands strictly afterwards. Only making that
write conditional closes it.

---

## 2. Scope

**In scope: the serial race only** — a worker persist landing against a row whose `serialNumber`
changed after the worker read it.

**Out of scope, filed separately: the `transferClassA` content race.** `transferClassA`
(`sync-run.ts:371-435`) overwrites the loser's MD blob and patches `summaryMd`/`artifacts` with the
winner's content, but **never writes `serialNumber`** — so the serial guard cannot see it. A worker
persisting a freshly generated summary can clobber a just-transferred winner body. That is a real
defect and is filed as backlog #19.

The two are separated deliberately. The serial race destroys **paid blobs**; the content race loses a
**sync decision** that self-heals on the next run, because both sides still hold readable MD. Bundling
a fuzzy lower-stakes problem into a tight high-stakes one is how a slice stops converging.

**Why this scope is smaller than backlog #17 assumed — guard the sink, not the sources.** That entry
says the fix "must cover the whole sync write path," listing `transferClassA` and `copyAdditiveVideo`
alongside A3. That is **half right**.

For the serial race it is wrong, and the sizing follows directly from §0: those are all *sources* —
places an address gets moved. Making `persist_summary` conditional guards the *sink*, the one place a
stale write can actually land. One guard covers every source at once, including sources not written
yet. Chasing
the sources instead would mean three guards today and a standing obligation on everyone who adds a
fourth.

For the content race it is right — but only because `transferClassA` is not a source at all in this
sense: it never moves the address, it replaces the *content* at an unchanged one. Nothing at the sink
can see that, which is precisely why it is a different problem and a different spec.

---

## 3. Verified ground truth

Every claim below was read from the code on 2026-08-04. Re-verify before implementation; the
stable-blob-addressing spec's §1 shipped a citation to a file that did not exist on the branch being
read, so a citation is not evidence until re-checked on the branch in hand.

| # | Fact | Evidence |
|---|---|---|
| G1 | `serialNumber` is present on **every** video row — `reserve_video_slot` inserts `jsonb_build_object('id', …, 'serialNumber', …)` and raises `(invariant)` if an existing row lacks one | `0009:79-96`, insert at `:95`, raise at `:90` |
| G2 | A bare reserved row has **no `summaryMd`** — only `id` and `serialNumber` | `0009:95` (same insert as G1) |
| G3 | `summaryMd` is payload-wins; `serialNumber` is row-wins | `0021:133` vs `0021:121-134` |
| G4 | Zero affected rows currently raises exactly one error: `persist_summary: no video row for %/%` | `0021:152` |
| G5 | The MD body does **not** embed its own base — `summaryCore` accepts `baseName` and deliberately never destructures it | `lib/ingestion/summary-core.ts:60-61` |
| G6 | The worker write sequence is stage → persist(committed) → promote → persist(promoted) | `summary-handler.ts:172-179` |
| G7 | `persistSummary` has exactly one production caller | `lib/storage/worker-persistence.ts:18-27`, called from `summary-handler.ts:177,179` |
| G8 | `transferClassA` never writes `serialNumber` | `sync-run.ts:397-432` |

**G5 is load-bearing** for §5: because the bytes are base-independent, a re-address is a change of
destination key only, never a regeneration.

**G2 is load-bearing** for §7: it is the reason the guard cannot key on the blob address today.

---

## 4. The conditional write

**One extra parameter in, one extra condition on the `UPDATE`.** The worker says which address it
believes it holds; the write happens only if the row still agrees.

`persist_summary` gains a required parameter naming the serial the worker read, and the `update` gains
one conjunct:

```sql
create function persist_summary(
  p_owner_id uuid, p_playlist_id uuid, p_video_id text,
  p_video jsonb, p_artifact_status text,
  p_expected_serial int                      -- ← required, no default
) …
  update videos v set …
   where v.playlist_id = p_playlist_id
     and v.video_id    = p_video_id
     and v.owner_id    = p_owner_id
     and v.data->'serialNumber' = to_jsonb(p_expected_serial);   -- ← the serial guard
```

Three properties of that predicate are deliberate.

**Required, not defaulted.** A defaulted parameter would leave every existing call site silently
unguarded, which is the failure the last slice's rule was written against: *an optional member does not
propagate, and callers keep inheriting the ambiguous original.* Cost: the function must be dropped and
recreated rather than `create or replace`d, since PostgreSQL treats the arity change as a new function.

**jsonb equality, never a cast.** `(v.data->>'serialNumber')::int = p_expected_serial` would **raise**
on any row whose serial is malformed, and a raise inside this predicate fails the write for a reason
that has nothing to do with staleness. `v.data->'serialNumber' = to_jsonb(p_expected_serial)` compares
jsonb to jsonb and is total. This is the same rule established for the storage RLS predicate: never
cast a value you did not write in the same statement.

**Inside the same `update`, not a preceding `select`.** A separate precondition check would be
TOCTOU — the serial could move between the check and the write. The affected-row count *is* the
check.

---

## 5. Failure taxonomy — two outcomes, not one

**"I wrote nothing" now has two possible reasons, and they need opposite responses.** One means *try
again* (the address moved). The other means *stop* (the row is gone). If the code can't tell them
apart, it will retry forever on the fatal one or give up on the recoverable one.

Today zero affected rows means exactly one thing (G4). Under the serial guard it means **two**:

| Zero rows because | Meaning | Handling |
|---|---|---|
| No row matches `(playlist, video, owner)` | The row is gone — deleted, or never reserved | **Fatal.** Non-retryable; retrying cannot conjure a row |
| A row matches but the serial differs | The base moved under us | **Recoverable.** Re-address and retry (§6) |

Collapsing these into one error would rebuild exactly the ambiguity that cost seven review rounds on
the last slice: *a value meaning ABSENT is also what a FAILURE produces.* The function must therefore
distinguish them explicitly — on zero affected rows, re-probe for the row's existence and raise a
distinguishable error for each case.

The two errors must be distinguishable **by the caller**, not merely by a human reading the log. The
worker branches on them, so the discrimination is part of the contract, not diagnostics.

---

## 6. Recovery — bounded re-address

**Rejected doesn't mean wasted.** The summary is already written and already paid for; only its
destination was wrong. So the worker re-files it under the new address instead of generating it again
— the difference between one blob round-trip and roughly 8¢ of Gemini.

That works only because the MD bytes are base-independent (G5): the file does not contain its own
name, so the same bytes are valid under any address.

```
attempt (bounded, N = 3):
  serial   := reserveVideoSlot(...)          -- returns the CURRENT serial for an existing row
  baseName := pad(serial) + '_' + slug(title)
  ref      := putStaged(baseName + '.md')
  verify staged
  persistSummary(..., expected := serial, 'committed')
      ├─ address-moved  → discard temp; next attempt
      └─ ok             → continue
  promote(ref)
  persistSummary(..., expected := serial, 'promoted')
      ├─ address-moved  → next attempt (re-stage and re-promote under the new base)
      └─ ok             → done
```

**The existing idempotency skip does not rescue the simpler design.** It is tempting to think failing
the job is free because the retry would notice the work is already done — it would not. The skip at
`summary-handler.ts:86-92` keys on `artifacts.summaryMd.status === 'promoted'`, which is false
precisely *because* the write was rejected. So "just fail it" really does pay Gemini twice.

**Both persists are guarded, not just the first.** The serial can move in the gap between them.
Guarding only the `committed` write would leave a promoted blob at the old base with the row believing
otherwise.

**Bounded, and what happens at the bound.** Three attempts. Exhausting them throws retryable, which
returns the job to the queue rather than dead-lettering it — the situation is genuinely transient, and
a queue retry re-runs Gemini only after the cheap local recovery has demonstrably failed. Each
exhaustion is logged with both serials, because repeated exhaustion means something is relocating in
a loop and that is a different bug.

**Temp-blob cleanup is best-effort.** A leaked staging object is inert and swept by existing staging
cleanup; failing the job to guarantee cleanup would trade a harmless orphan for a real one.

---

## 7. Migration to stable blob addressing

**The question: stable blob addressing is coming soon — can we build the guard the way that design
wants it, so the migration is free?**

**The answer: not yet — the thing it wants to compare doesn't exist yet.** But almost nothing is
wasted, because the throwaway part is one line.

The stable-blob-addressing design (§5.1) publishes through a manifest row with the conditional write
`update video_artifacts … where blob_key = <what I read>` — a guard on the **address string**, not on
a serial. So keying this guard on the address now looks like the free migration.

**It cannot be done today, and G2 is the reason.** A bare reserved row carries no `summaryMd`. On a
first-time ingest there is no prior address to compare against, so a base-keyed guard would have
nothing on the left-hand side of the predicate. It would guard the re-summarize path and silently pass
the first-summary path — coverage that looks complete and is not, which is strictly worse than a
narrower guard that always fires.

The manifest CAS escapes this because the manifest row is created **at reservation time** with a real
`blob_key`: the address exists before the content does. That is a structural change this slice is not
making, and it is not portable backwards.

So what migrates is the **protocol, not the predicate**:

| Piece | At migration |
|---|---|
| Bounded re-address loop (§6) | unchanged — still the recovery on a lost CAS |
| Two-outcome failure taxonomy (§5) | unchanged |
| Test corpus — interleavings, mutation checks | retargeted at a new column, cases intact |
| Required-not-defaulted discipline | unchanged as a rule |
| **The `where` conjunct itself** | **replaced** — one line |

The expensive parts are column-agnostic. The throwaway is a line of SQL.

**This slice is also the first evidence for §5.1's central claim.** That section asserts a conditional
write on one small row is *"trivially sufficient"* — and **nothing in this codebase performs a
conditional publish today**, so the claim is untested. Building it on `serialNumber` tests it against
real concurrency while the cost of being wrong is one migration instead of an architecture.

---

## 8. Testing

The gate is not "the guard exists" but "the guard fires on the interleaving that motivated it."

**Required — the race, end to end (integration).** Reserve a slot, relocate the serial out from under
it, then persist with the stale serial. Assert the row is *not* incoherent and the paid dig keys under
the new base are still reachable. This is the test the whole slice exists to make pass; asserting only
that the RPC raises would pass in a world where the digs are still stranded.

**Required — mutation check.** Delete the `and v.data->'serialNumber' = …` conjunct; the race test
MUST go red; restore. Per the standing rule, **commit the fix before mutating** — `git checkout` has
reverted uncommitted work three times on this project. A guard that passes in both worlds is not a
guard.

**Required — the taxonomy is discriminable.** One test per §5 outcome, asserting the caller can tell
them apart, not merely that both raise.

**Required — the re-address loop terminates.** A relocation on every attempt must exhaust the bound
and throw retryable, not spin.

**Required — first-summary and re-summary both guarded.** The G2 asymmetry means these are structurally
different rows (no `summaryMd` vs an existing one). Covering only one is the coverage gap §7 rejects.

**Required — no double charge on recovery.** Assert Gemini is invoked exactly once across a run that
re-addresses. The serve path already produced one confirmed double-charge in this repo; a money-path
claim is asserted, not reasoned about.

---

## 9. Out of scope

- The `transferClassA` content race — backlog #19 (§2).
- Any change to A3's in-flight probe. PR #45 stays as is; it and this guard are complementary, the
  probe reducing the window and the guard closing what remains.
- The local pipeline. `persist_summary` is a Supabase RPC; local writes do not route through it and
  local has no concurrent sync writer.
- `videos.position` (backlog A6b) and the manifest itself — separate slices.

---

## 10. Open questions

1. **Is `reserveVideoSlot` the right re-read on attempt 2+?** It returns the existing serial for an
   existing row, which is what we want — but it also takes `for update` on the playlist row. Whether
   re-taking that lock inside a retry loop is safe under a concurrent sync needs checking before
   implementation, not after.
2. **Does any test double or fixture call `persistSummary` positionally?** The arity change breaks
   positional callers silently if a double is typed `as any` — which opts out of compiler enforcement
   entirely, so behavioural tests are the only net.
3. **Should the guard also cover `docVersion`?** A re-summarize at a new doc version racing a
   relocation is the same shape one level up. Probably out of scope; name it explicitly rather than
   discovering it in review.

---

## 11. Verification

- `python3 scripts/check-docs.py` from the repo root (it resolves paths from `__file__`).
- `grill-with-docs` terminology pass — **run 2026-08-04**. Outcome: the mechanism was renamed from
  "fence" to **conditional write** / **serial guard**, because "fencing" was already taken in this
  codebase for lease fencing (`0008_jobs_queue.sql:94`) — the very mechanism that cannot solve this
  problem. Remaining terms to reconcile with `CONTEXT.md`: *base*, *serial number*, *slot*.
- Dual adversarial review to convergence. This is a money/data-loss path **and** a schema change, two
  independent Iterative Re-Review triggers in `docs/dev-process.md`.
- Standing root-cause shapes to carry into each review round, per the convergence rule:
  *absent-vs-failed conflation*, *a guard with no covering test*, *a value read in one process and
  written in another*, *an optional member that does not propagate*.
