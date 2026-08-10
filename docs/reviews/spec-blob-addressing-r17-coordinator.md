# Round 17 — coordinator adjudication

**Verdict: NOT CONVERGED.** 1 Blocking, 4 High, 3 Medium, 1 Low (Claude); 1 Blocking, 1 High, 1 Medium
(Codex). Both reviewers executed the schema against live Postgres inside a rollback; Claude ran six
additional probes (T1–T6). Tree clean.

**The dissolution's CONCLUSION survived and could not be broken.** Nothing produces a
`video_generations` row before or during a paid call, `video_generations_collectable` cannot return a
row that does not exist, and round 9's B1 window is genuinely closed by subtraction. **Withdrawing all
three covers was correct.** What fails is the ADR's *account* of why, and three consequences of the
same deletion that it does not name.

---

## B1 — nothing inserts the generation row (both reviewers, MEASURED)

The ADR's load-bearing sentence — *"the row is born complete, at record time"* — **names no writer, and
as the ADR leaves the schema none exists.** `reserve_artifact_slot` is the only non-fixture INSERT
`[VERIFIED: schema/04_artifacts.sql:307-313]` and is deleted; `record_artifact`'s generation write is
an **UPDATE** `[VERIFIED: :556-565]` gated on `g.state = 'pending'` **and** `g.reserved_by = p_token` —
both of which this ADR deletes, so the function would not even resolve after the column drop.

**MEASURED (T4):** record for a slot whose generation is absent →
`[P0001] cannot mark summary as recorded — generation gGHOST is <absent>`. Not a race — the ordinary
first record of a fresh generation.

So the ADR's headline claim held **for a degenerate reason**: no row exists during the call because no
row exists ever. That is round 16's own B1 reproduced by the change that removed it.

I predicted this trap when writing the round-17 brief and **committed the fix without checking it** —
using the next review round as my verification step, which is precisely what makes each round find the
previous round's fixes.

**Fix:** state in Consequences that `record_artifact` **INSERTs** the generation row, born `complete`,
before the artifact insert that FKs it — it already takes every needed column
`[VERIFIED: :468-473]` — that the pending/`reserved_by` UPDATE is **replaced**, not merely unfenced,
and that `on conflict do nothing` + `completed_by_another` `[:576-583]` is what makes a second writer
safe (MEASURED T5: returns `completed_by_another`, does not overwrite `md_hash`).

## H1 — "forced by the deletions" is true for `summary` ONLY (MEASURED) — the FIFTH instance

Three of the four completeness constraints are also gated `kind <> 'summary'`
`[VERIFIED: schema/03_generations.sql:395, :409-410, :411-412]`; only
`gen_complete_has_produced_at` `[:394]` ranges over all kinds. **MEASURED (T1):** a `model`, `dig` or
`digDeeper` row with **only** `produced_at` is **accepted**, and `produced_at` is knowable before any
Gemini call — `record_artifact` defaults it to `now()` `[VERIFIED: :473]`. `05_assert.sql:138-139`
already inserts `gDIG`/`gMODEL` complete with `card` and `md_hash` NULL, green.

So for three of four paid kinds the dissolution is **conventional, not forced** — and `model` is the
kind with no job, no staging, and its own serve lease. An implementer who creates an early `model`
generation reopens round 9's window with the floor now deleted and no assertion to go red.

**This is the fifth instance of "name what the rule ranges over"** — after round 13 B1, round 14 H3,
round 15 H3 and round 16 M1 — and it is in the paragraph that *is* round 16's load-bearing argument.

## H4 — deleting `pending` also falsifies rule 19's MONEY property (Claude only; nobody caught it in six rounds)

The ADR names one knock-on of losing the record-first order (§8's grace period). Rule 19 bought
**two more**, both on the money path `[VERIFIED: …-design.md:864-887]`: **bytes ⊆ records**, and *"a
crash before recording leaves nothing — no bytes, no row, no orphan — **so spending again is correct
rather than a double-charge**"*. It was adopted against a MEASURED defect: *"6¢ → 12¢"*
`[VERIFIED: …-design.md:860-863]`.

With `pending` gone the row cannot precede the bytes, so a crash after the blob write leaves paid bytes
at a generation-derived key **no later attempt can name**, and the next attempt spends again — the
shape rule 19 was rewritten to remove. The design spec's sentence *"a crash before recording leaves
nothing"* is now **false and left standing**.

Bounded, not unbounded (`summary_max_attempts` = 1, `max_serve_attempts` = 5), so it is a **named
residual** — but exactly the kind this ADR's own falsifier #4 exists to surface.

## H2 / H3 — two mechanisms named that do not exist

- **H2 — there is no orphan sweeper.** §8's grace period *is* real and reinstatable
  `[VERIFIED: …-design.md:1995-1996]`, but §8's own opening says *"There is no GC of superseded blobs
  anywhere… GC is currently impossible"* `[:1949-1953]`, and `grep -rniE "orphan.?sweep|garbage.?collect"`
  over `lib/ worker/ app/ scripts/ tests/` returns **zero hits**. Worse, the age predicate is not
  expressible: `BlobStore.list()` returns keys only and the interface has no `stat`/mtime
  `[VERIFIED: lib/storage/blob-store.ts:33-80]`. The ADR trades an **executable, mutation-scored**
  guard for prose in a section the spec marks OPEN — and calls it *"existing"*.
- **H3 — the round-16 re-record rule has no enforcer (MEASURED T6).** *"Same source set, or raise"* is
  assigned to the append-only trigger, installed `before update or delete` `[VERIFIED: :995-997]`. A
  re-record naming a different source is an **INSERT**, which fires no such trigger: measured result
  was a silent **union**. The schema states this rule twice in its own comments — *"a constraint governs
  STATES, a trigger governs TRANSITIONS, and an INSERT is a state with no transition"* `[:1010-1012]`.
  My round-16 fix assigned an invariant to the one mechanism shape that structurally cannot see the
  violating operation.

## MEDIUM / LOW

**M1** the deleted collectable predicate has a paired assertion `[05_assert.sql:1428-1445]` and a named
mutation `[mutate-schema.py:410-413]`; the ADR retires neither, and a stale mutation anchor reports
**INVALID**, which this project has measured reads as *untested* rather than *retired* — the ADR
applied the right standard to the sibling case and not to this one ·
**M2** `video_generations.state` becomes single-valued and its fate is unstated while five consumers
read it · **M3** the grace-period sizing omits `DIG_GENERATE_MAX_PASSES` `[VERIFIED: lib/gemini-cost.ts:51]`
— an enumeration missing a member, in the text that replaced the dissolved warning about enumerations ·
**L1** front matter says three rounds and answers four.

---

## What round 17 could NOT break

The dissolution itself; *"the only production INSERT"*; the correctness of withdrawing all three
covers; and (Codex) M1's restated bound and the four round-16 reconciliation edits.

---

## The decisive observation, and it is about the gates rather than the ADR

Codex: *"the executable schema is still the pre-dissolution schema with `reserve_artifact_slot`,
`pending`, leases, and `record_artifact`'s pending update path intact."*

**Every "the suite ran green" in rounds 13–17 verified the CURRENT design, not the proposed one.** The
ADR's world has never been executed, by construction, because nobody has written it. That is not a
defect in the reviews — it is the reason every remaining finding has the same shape: *the ADR names a
mechanism that does not exist yet.* B1 (no writer), H2 (no sweeper, no age seam), H3 (no enforcer), M1
(orphaned assertion + mutation), M2 (unstated column fate) are all answerable **only by writing the
code**, where the schema executes, the assertions run, and the mutation harness scores.

**Recommendation: apply round 17's findings, then stop reviewing this document and start task #36.**
Blockings across rounds ran 4 → 3 → 1 → 1, and the residue is specification-of-implementation rather
than decision-making. The next genuine test is the migration, not round 18.
