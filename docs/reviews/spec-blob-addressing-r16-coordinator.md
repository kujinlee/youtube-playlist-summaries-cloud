# Round 16 — coordinator adjudication

**Verdict: NOT CONVERGED at review time.** Claude 1 Blocking / 2 High / 3 Medium / 2 Low; Codex 1
Blocking / 1 Medium. **All findings are now applied, and the Blocking resolved by DELETION rather than
by a fix.**

Gate strength: **not downgraded.** Both reviewers executed `verify-schema.sh` against live Postgres
inside a rollback; Claude additionally probed option C directly (`P1a`–`P2e`) in a rolled-back
transaction over the live corpus, and exercised `check-sentinel-meanings.py` against a scratchpad copy
of the schema. Tree clean throughout.

---

## B1 — the mechanism this round was verifying could not be written at all

Both reviewers converged on the same Blocking from different directions; Claude's is the decisive
form, and I verified every load-bearing fact by hand.

**`video_generations.in_flight_until` had no row to be written to.**

- `reserve_artifact_slot` is the **only** production INSERT into `video_generations`
  `[VERIFIED: schema/04_artifacts.sql:308]` — I re-ran the grep; every other hit is a fixture in
  `05_assert.sql`. This ADR deletes that function.
- It inserts `state='pending'`, and that state is the only thing that makes a contentless row legal:
  `state` is `not null default 'complete'` `[VERIFIED: schema/03_generations.sql:291]`, and the four
  completeness constraints are each `state <> 'complete' or <requirement>` `[VERIFIED: :394, :395-408,
  :409-410, :411-412]`. With `pending` unreachable they are unconditional, and they demand `card`,
  `md_hash`, `doc_version_major`, `produced_at` — all derived from the Gemini output.

Claude's measured probe:

```
P2a summary pre-content insert:        REJECTED [23514] gen_card_complete
P2b model pre-content insert:          REJECTED [23514] gen_complete_has_produced_at
P2e summary pre-content WITH pending:  ACCEPTED   ← the deleted route
```

The schema had already recorded this trap `[VERIFIED: schema/03_generations.sql:271-283]`: *"The paid
call sits between those two, so both doors were locked."* `pending` was the key cut for that lock;
this ADR throws the key away and then hangs a new mechanism on the door.

**And the fourth exit is the answer.** A sweeper cannot collect a row that does not exist, so round
9's B1 window is closed **by the deletions themselves**. Option C would have been a column, a CI
check, two prose rules, an assertion burden and a mutation-scoring burden spent re-closing a shut
window — *two mechanisms for one concern*, in the document written to stop that.

**Resolution applied: `in_flight_until` is deleted, not fixed.** The ADR now states, as its own
forced consequence, *when a `video_generations` row is created* — at record time, after the paid call
— and reinstates §8's grace period on the **orphan blob**, which is what actually lacks protection in
that window.

**Four other findings dissolved with it** rather than needing fixes: H1 (the covering bound was
computed for `MAGAZINE_MAX_PASSES` = 3 while `SUMMARY_MAX_PASSES` = 12 — verified at
`lib/gemini-cost.ts:27,:29`), M2 (the "grep-checkable" sweeper-only rule had no script and a hole —
the view projects `select g.*`), M3 (was it ever cleared?), L2 (the sentinel registry entry, which
Claude MEASURED failing). **Four findings, one deletion — that is the tell that dissolution was the
right call.**

---

## The other findings, all applied

- **H2 (Claude)** — inside one numbered item, (a) said a re-record **replaces** the source set while
  (b) moved an append-only trigger that forbids exactly that onto the same table. Worse, the cited
  justification inverts: `coalesce(p_source_generation_id, v_src)` means *omission = keep what is
  recorded* `[VERIFIED: schema/04_artifacts.sql:654, :663]`, an argument for idempotent
  **re-statement**, not replacement. Now: *a re-record must present the same source set or raise.*
- **M1 (Claude)** — *"removes this entirely"* was false. Two playlists, one key exhausted at 5 and its
  sibling at 1, still gives `count(*) = 2` and `least(6, 4) = 4`, reviving it. Now stated as: removes
  the single-source case completely, bounds the merged case to one extra call per key, once.
  **Third instance of the same substitution**, caught by the round that came looking for it.
- **L1 (Claude)** — *"ADDED — one column"* followed by a table. Introduced by the reconciliation pass,
  whose purpose was removing exactly that shape. Now "exactly one table, and no columns."
- **Codex Medium** — *"enforced by a check"* with no check on the branch. Dissolved with option C; the
  remaining bound is stated as a **blocking precondition of the implementing slice**, not a promise
  this ADR can keep.

## What round 16 could NOT break — do not re-run

- **The freeze trigger does not reject the marker** (the brief's top suspicion, MEASURED both ways).
  It freezes an explicit denylist, not an allowlist.
- **B3's coverage is complete** — all 19 `source_generation_id` occurrences in `04_artifacts.sql` and
  6 in `05_assert.sql` have a stated fate. H2 was about *what* the rule says, not coverage.
- **`count(*) > 1` identifies the merged set correctly, and the migration is idempotent under re-run.**
- **Reconciliation edits 1, 3, 4, 5 are correct and introduced nothing** (edit 2 became L1).
- **0 wrong citations among the new tags** — against round 14's five and round 15's one created by the
  split.
- **Whole-document coherence on the four named axes is clean**: no per-kind successor, no live
  "exclusivity" claim, the withdrawn render designs only inside strikethroughs, and
  `video_artifacts_free_uq` with exactly one fate.
- **The core decision** — delete the reservation protocol — **was attacked and did not move.** Four
  design reviews now.

---

## The pattern, stated plainly

**Rounds 14, 15 and 16 each found their Blockings in the previous round's fixes.** But the trend is
real and it is not a treadmill:

| Round | Blockings | Character |
|---|---|---|
| 14 | 4 | structural defects in the design's own claims |
| 15 | 3 | structural, plus reconciliation failures |
| 16 | 1 | one mechanism that should never have been added |

Round 16's Blocking **removed** work rather than adding it. That is what convergence looks like from
the inside when the earlier rounds were adding mechanism: the last thing to go is the thing you built
to cover a problem you had already solved.

**And the reconciliation pass keeps earning out.** After this round's edits it found the stale
front-matter, the headline's "one marker survives", the concern-table row, and the Consequences block
— four more cross-section conflicts, none of which any reviewer had flagged, all in changes made
minutes earlier.

**Round 17 is warranted** — this round changed the design again, and a design change has never once
survived unreviewed in this spec.
