# Live-system probe — conditional-write spec, round 1

**Date:** 2026-08-04
**Target:** `docs/superpowers/specs/2026-08-04-cas-fence-persist-summary-design.md`
**Method:** direct SQL against the running local Supabase stack
(`docker exec supabase_db_… psql`), not code reading.
**Why:** `docs/dev-process.md` — *"Determine external behaviour by probing the live system, not by
reading vendor types."* The spec's §4 rests on a claim about what the data actually contains, and that
is measurable rather than arguable.

This is the **coordinator's own verification pass**, run before the Codex and Claude adversarial
reviews reported. It is recorded separately so the convergence trail shows which findings came from
measurement and which from review.

---

## P1 — G1 is FALSE as written (spec accuracy)

**Spec claim (§3, G1):** *"`serialNumber` is present on **every** video row."*

**Measured:**

```sql
select coalesce(jsonb_typeof(data->'serialNumber'),'ABSENT'), count(*) from videos group by 1;
```

| `jsonb_typeof` | rows |
|---|---|
| `number` | 2748 |
| **ABSENT** | **154** |

Of those 154, **22 carry a `summaryMd` *and* an `artifacts` object** — i.e. they are summary-bearing
rows, not bare scaffolding:

```sql
select jsonb_object_keys(data), count(*) from videos
 where not (data ? 'serialNumber') and data->>'summaryMd' is not null group by 1;
-- artifacts, docVersion, title, summaryMd, id, language → 22 each
```

**But the conclusion G1 supports still holds, for a different reason.** `reserve_video_slot`
(`0009:89-91`) *raises* when an existing row has no serial:

```sql
if exists (select 1 from videos v where …) then
  raise exception 'reserve_video_slot: existing video %/% has no serialNumber (invariant)', …;
```

The worker calls that at `summary-handler.ts:95`, **before** any persist. So a serial-less row cannot
reach `persist_summary` through the only production caller (G7).

**Why the distinction matters and is not pedantry.** §4 justifies "no NULL case to reason about" with
"the invariant holds on every row." The real guarantee is narrower: *every row the worker can reach,
because reserve refuses otherwise.* That guarantee lives in a **different function** from the one being
changed. Any future caller of `persist_summary` that does not first go through `reserve_video_slot`
inherits a guard that fails **closed and silently** (see P2). The spec must state the real mechanism,
so that a reader adding a second caller sees the precondition they are taking on.

**Disposition:** rewrite G1. Add the precondition to §4 as an explicit contract on callers, and to §10
as an open question about whether it should be asserted in `persist_summary` itself rather than
assumed.

**Unrelated question this raised (not this spec's problem):** how did 22 rows acquire a `summaryMd`
without a serial? `claim_video_slot` (`0023:67`) can *add* a serial to an existing row by update, which
implies rows legitimately exist without one at some point. Worth a look, but out of scope here.

---

## P2 — predicate semantics, measured rather than assumed

```sql
select ('{"id":"x"}'::jsonb)->'serialNumber'        = to_jsonb(7),   -- absent
       ('{"serialNumber":7}'::jsonb)->'serialNumber' = to_jsonb(7),  -- number
       ('{"serialNumber":"7"}'::jsonb)->'serialNumber' = to_jsonb(7);-- string
```

| left-hand value | result | effect in a `where` clause |
|---|---|---|
| absent | **NULL** | not true → **row not matched → write silently rejected** |
| number `7` | `t` | write proceeds — the intended path |
| string `"7"` | **`f`** | **row not matched → write silently rejected** |

Two consequences the spec did not state:

1. **The failure mode of a wrong left-hand value is silent rejection, not an error.** Combined with §5,
   the worker would classify it as *address-moved → retryable*, burn all three re-address attempts,
   throw retryable, and the queue retry then **re-runs Gemini and re-charges**. A permanently-absent
   or permanently-stringified serial therefore produces an unbounded charge loop up to `max_attempts`,
   not a clean failure. That is a money consequence of a type mismatch.

2. **The string case is measurably not live** (0 of 2748 rows) — every SQL writer builds it with
   `jsonb_build_object('serialNumber', v_serial)` where `v_serial` is `int`
   (`0007:37`, `0009:95`, `0023:67`, `0023:89`), and the TS type is `z.number().int().positive()`
   (`types/index.ts:67`). So this is **not a defect today**, but it is a live trap for any future
   writer, and the fail-closed direction makes it expensive.

**Disposition:** §4 keeps `to_jsonb` (it remains the right choice — the alternative `::int` cast
*raises* on malformed input, which is worse). But the spec must name the fail-closed direction
explicitly, and §8 gains a test asserting the guard's behaviour when the left-hand side is absent, so
the silent-rejection path is covered rather than assumed unreachable.

---

## What this probe did NOT check

- Whether `reserve_video_slot`'s `for update` on `playlists` deadlocks against a concurrent sync
  transaction (§6's retry loop). That needs two concurrent sessions, not a single query — left to the
  adversarial reviews and, if unresolved, to an integration test.
- Whether any test double calls `persistSummary` positionally (the arity change). That is a code
  search, not a DB probe.
- Production data. This is the local dev stack; the 154 serial-less rows are local test detritus and
  their **count** carries no production signal. The **existence** of the shape is the finding, and the
  measured predicate semantics are properties of Postgres, not of this dataset.
