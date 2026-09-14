# `guard-coverage-scope` (PR #298) — round 1, CLAUDE half

**Reviewer:** Claude (adversarial half). **Date:** 2026-09-14.
**Verdict up front: NOT CONVERGED.** 1 Blocking, 1 High, 2 Medium, 2 Low.

The code change is right and its headline number is exactly right — I reproduced `41 → 46` and the
five named guards. **Every finding below is about a CLAIM, not about a line of Python**, and the
Blocking is the one this repo has paid for three times already: the enumeration is still short, a
review round already said which two clauses are short, and this branch writes *✅ CLOSED* over it.

---

## PROOF OF SUBJECT

```
$ git log --oneline -1
e2c28a67 The guard ratchet built a table and then declined to look at it
$ git status --porcelain      # clean at start; only this file added at end
```

Database: `m4_review_gc_claude`, built by `scripts/ci/start-schema-db.sh` — 27 migrations, M4
present. The developer's own `supabase_db_youtube-playlist-summaries-cloud` was never addressed.
Probe scripts in `…/62196080-…/scratchpad/{widen,probe2,probe3}.py|sql`.

**Controls, run before any finding was written:**

| Check | Result |
|---|---|
| `check-guard-coverage.py` (live) | `guards in schema: 46  SHAPE: 40  reconciling: 6` · ✅ · rc 0 |
| `check-guard-coverage.py --self-test` | 16/16, matching its declared count |
| `mutate-schema.py` (full suite, my container) | **58/58**, baseline restored GREEN, rc 0 |
| the branch's own `41 → 46` claim | **reproduced exactly** — see below |

```
BEFORE (TRIGGER_TABLES as of e2c28a67~1): 41
AFTER  (this branch)                    : 46
newly visible: ['art_summary_has_no_source', 'vas_artifact_fk', 'vas_source_generation_fk',
                'video_artifact_sources_append_only', 'video_artifact_sources_insert_once']
classified but absent from catalog: []
```

So the commit message's central measurement is true, the five are the five, and nothing is stale.

---

## BLOCKING

### B1 — "Now 46, every one classified" is false, and round 12 already named the two clauses that make it false — in this function, with this fix [MEASURED]

`CATALOG_SQL` has four clauses. This branch derives **two** of them from `TRIGGER_TABLES` and leaves
**two** on the old two-table `TABLES` tuple:

* `scripts/check-guard-coverage.py:227-228` — CHECKs, `conrelid = any(array{list(TABLES)})`
* `scripts/check-guard-coverage.py:239-241` — unique indexes, `indrelid = any(array{list(TABLES)})`
  **and** `indexrelid::regclass::text like '%_uq'`

Measured against the same built schema, widening only those two clauses to the set the branch just
widened:

```
OUTSIDE  wide-check   jobs.jobs_kind_chk
OUTSIDE  wide-check   jobs.jobs_progress_phase_check
OUTSIDE  wide-check   jobs.jobs_status_chk
OUTSIDE  wide-check   videos.videos_check
OUTSIDE  wide-pk-uq   video_generations.video_generations_workspace_id_video_id_generation_id_kind_key [u]
OUTSIDE  wide-pk-uq   video_artifact_sources.video_artifact_sources_pkey [p]
```

Three of those are on tables `TRIGGER_TABLES` has contained since **round 9**. Two of them are worse
than that:

1. **`video_generations_..._kind_key` is on a table the gate DOES scan.** It is invisible for one
   reason only — it is spelled `unique (…)` inline at `03_generations.sql:332` and therefore carries
   Postgres's `_key` suffix instead of `_uq`. The gate's `GUARDS` dict contains
   `video_artifacts_state_check` and `video_generations_state_check` under the comment *"Auto-named
   inline CHECKs. Found by this ratchet on its first run — they had been in the schema since round 4
   and were never in anyone's mental inventory, which is the exact failure mode it exists to remove"*
   (`:102-104`). An auto-named inline UNIQUE sits one line away in the same schema file and the
   instrument cannot see it, because a **naming convention** is the boundary of the enumeration whose
   docstring argues that conventions are what an enumeration replaces.
2. **`video_artifact_sources_pkey` is the table THIS BRANCH added**, and it is not incidental — it is
   the guard that actually answers the SEQUENCE question on that table. Measured (probe P1b): a
   second caller re-inserting the identical provenance row is rejected by
   `23505 duplicate key value violates unique constraint "video_artifact_sources_pkey"`, not by
   either trigger. The branch classified five guards on this table and left unclassified the one the
   second caller actually meets. `04_artifacts.sql:231-233` says so in its own words: *"One row per
   (artifact, source). A re-record presenting a source it already records is therefore a duplicate
   rather than a second claim — which is what makes idempotent re-statement possible."*

**This was filed, it is still open, and it is about this exact code.**
`docs/reviews/spec-blob-addressing-r12-claude.md:178-212`, Medium **M1**, prescribes:

> *"drop the `%_uq` filter and enumerate every unique index on the target tables; extend the CHECK
> clause to `TRIGGER_TABLES` as the FK clause already is."*

and `docs/reviews/spec-blob-addressing-r13-claude.md:346-347` predicted precisely what this branch
does:

> *"Fix the enumeration (`scripts/check-guard-coverage.py`) **before** the implementing slice, or the
> re-baseline launders it."*

`r13-codex.md:54` lists it as surviving. It reaches `docs/backlog.md` nowhere. This branch re-baselines
41 → 46 and writes **✅ CLOSED** on backlog #29's half (1), plus *"Now 46, every one classified"* in
the commit message and *"Fixed; it now covers 46"* in the dashboard entry — which is exactly the
re-baseline that r13 M3 said would launder it. **An escalation is closed by a reply, never by work
that moots part of it**, and marking the row closed removes the only reason a future reader looks.

**Why Blocking rather than High:** the blocking artefact is not the Python, it is the three sentences
that go into `docs/backlog.md`, `docs/dashboard-entries.md` and the merge commit — the two documents
this project uses as its memory. The defect class here is *"a gate reported complete"*, and the commit
message itself calls this the third instance.

**Two ways to satisfy it, and either is fine — this is not a demand to widen the gate:**

* (a) Derive the CHECK clause and the index clause from `TRIGGER_TABLES` and drop the `%_uq` filter,
  then classify the ~6 entries that surface (all of them look SHAPE on their faces; the PK is the one
  that needs a sentence). This is round 11's own conclusion — *"DERIVED FROM THE SAME SET AS THE
  TRIGGERS, not a second hand-written list … One list, one place"* (`:230-233`) — applied to the two
  clauses round 11 did not reach; or
* (b) Keep the change exactly as it is and **narrow the claim**: say `TRIGGER_TABLES` is now one list
  for triggers and FKs, that the CHECK and unique-index clauses remain scoped to `TABLES`, and that
  r12 M1 is open with a named cost. Then file r12 M1 into `docs/backlog.md`, because right now it
  exists only inside a review document that this branch's closing sentence gives nobody a reason to
  re-open.

---

## HIGH

### H1 — the SEQUENCE note denies a reconciler that exists, and I measured the reconciler [MEASURED]

`scripts/check-guard-coverage.py:155-161` classifies `video_artifact_sources_insert_once` SEQUENCE
with the note:

> *"does NOT reconcile, and that is the design: provenance is immutable, so a second statement is a
> caller bug rather than a race. … No retry succeeds, and none should"*

Three of those claims are true and two are wrong, in the direction that costs the most.

**True, and I confirmed each:** the trigger does compare the table's existing rows for the artifact
against this statement's (`04_artifacts.sql:1142-1146`); ALL sources really must arrive in one
statement (probe P4b — a second statement adding `gSPARE` to `dig:120` raises
`P0001 … it already records {gNEW}, and this INSERT adds {…}`); and the error does name both sets.

**Wrong:** *"No retry succeeds, and none should."* Measured, probe P1:

```
P1  PASS  — same-set re-statement accepted, 0 row(s) inserted (trigger never saw it)
P1b RAISED — 23505 / duplicate key value violates unique constraint "video_artifact_sources_pkey"
```

The reconciling retry — `on conflict do nothing` re-presenting the recorded set — **succeeds**,
because the PK makes it insert nothing and the transition table is then empty, so this trigger never
fires. And it is not an accident that it succeeds: `04_artifacts.sql:606-607` says the same-set
re-statement *"is the path a crash-retry takes and **must NOT be refused**"*, and `record_artifact`'s
`else` branch at `:593-608` is the no-op that does the refusing-not. So there IS a reconciler, it is
two-part (`video_artifact_sources_pkey` + `record_artifact`'s same-set no-op), and the note the
ratchet exists to produce says there is none.

**Wrong, second:** *"a second statement is a caller bug"* — over-broad by the same measurement. Only a
second statement that **changes the set** is a caller bug. The note states the stronger claim, and the
stronger claim is what a future reader would act on.

This matters more than a wording nit because of what the note is FOR. The script's own docstring
(`:122-126` in `GUARDS`) records why the two-way label was split: *"the reconcilers holding a SHAPE
guard back from rejecting a blameless second caller were exactly what nothing protected."* This entry
is now the **first** member of `RECONCILING` whose note names no reconciler at all — compare
`forbid_collecting_current`, which is SEQUENCE and names one (*"the sweeper selects THROUGH
video_generations_collectable"*). Delete `record_artifact`'s same-set branch tomorrow and the ratchet's
own note endorses the result.

Note also what the ratchet can see: `evaluate` checks only `if not note` (`:330`). A SEQUENCE entry
whose note says *"does not reconcile"* passes. `MUTATION_EXEMPT` carries the comment *"Empty by
design: if this grows, the ratchet is being talked out of rather than met"* (`:204-205`) — the note
field is now a second escape hatch with no such property, and this entry is its first user.

**Change:** rewrite the note to name the reconciler that exists, e.g. *"the reconciler is the PK plus
`record_artifact`'s same-set no-op (`04:606`): an idempotent re-statement inserts nothing, so this
trigger never sees it. It raises only on a set CHANGE, and all sources must arrive in one statement."*
That is accurate, it is still a SEQUENCE entry, and it keeps the mutation requirement.

---

## MEDIUM

### M1 — `video_artifact_sources_append_only` is SHAPE on a reason that is false for half its body [MEASURED]

`scripts/check-guard-coverage.py:149-151` records the reason as *"before update|delete, per row:
rejects the operation itself, like its sibling `video_artifacts_append_only`"*. The UPDATE half does
exactly that. The DELETE half does not — it rejects **conditionally on another table's state**
(`04_artifacts.sql:1111-1117`: raise only `if exists (select 1 from public.video_artifacts a where
a.artifact_id = old.artifact_id)`), which is the shape of a sequencing question, not a well-formedness
one.

Measured, probe P5/P6, on a generation that is a SOURCE and owns no artifact of its own:

```
P5a ACCEPTED — dig:120 now sources gSPARE (which owns no artifact)
P5b RAISED   — P0001 / video_artifact_sources: cannot DELETE the provenance of a live artifact … (source gSPARE)
P6           — gSPARE appears in video_generations_collectable: 0 row(s)
```

That is *structurally identical* to `forbid_collecting_current`, which the same file classifies
**SEQUENCE** with the note *"the sweeper selects THROUGH `video_generations_collectable`; trigger kept
as a backstop for direct writes"* — a raise that aborts a batch statement, over a filter the intended
caller is supposed to select through, which P6 confirms already excludes this row. Two guards, one
structure, two classifications, and the difference is not written down anywhere.

**Reported against my own hypothesis:** the more obvious victim does not exist. Deleting a generation
that owns an artifact never reaches this trigger at all — probe P2 died first at
`23503 … violates foreign key constraint "video_artifacts_workspace_id_video_id_generation_id_kind_fkey"`.
And `delete from workspace_videos` dies earlier still, at `video_artifacts`'s own append-only trigger
(probe P3, `P0001 … cannot DELETE recorded paid row`), which `04_artifacts.sql:214-221` already
records. So the reachable blameless caller is narrow — a future §8 sweeper or erasure path that
deletes source-only generation rows — and that is a real argument for SHAPE.

**Change (cheap, and not necessarily a reclassification):** make the recorded reason true. Either
reclassify to SEQUENCE naming `video_generations_collectable` as the reconciler, or keep SHAPE and
write the note the file already writes for exactly this situation — `video_artifacts_identity_uq`
carries *"the SEQUENCE question has no reachable case, rather than a reconciler"* (`:173-180`). What
should not survive is *"rejects the operation itself"*, because that sentence is what stops the next
reader opening the body.

### M2 — the component that has now failed three times is the one part of this script with no falsifier [MEASURED]

All 16 `--self-test` cases drive `evaluate` (`:360-405`). All five entries in
`scripts/mutations/check-guard-coverage.json` mutate `evaluate`'s rules (the UNCLASSIFIED sweep, the
STALE sweep, the UNJUSTIFIED check, `COVERED_BY`, `MUTATION_EXEMPT`). **Nothing anywhere tests
`CATALOG_SQL` or `TRIGGER_TABLES`** — which is the component that was short in round 9, short in round
11, and short again here, three for three. The one instrument that could have caught it is the live
gate, whose only verdict on its own enumeration is its own green tick.

A falsifier is available and needs no database, because the property is textual and pure:

* `set(TABLES) <= set(TRIGGER_TABLES)`;
* the CHECK clause and the index clause are rendered from the **same tuple** as the FK and trigger
  clauses — i.e. `str(list(TRIGGER_TABLES))` occurs four times in `CATALOG_SQL`, not twice.

Today that case goes RED; under option (a) of B1 it goes green and stays green, and a fourth
recurrence becomes a failing self-test instead of a fourth review round. This is the project's own
*after fixing, search for the class* rule: the branch fixed the third instance and left the class
exactly as reachable as it was.

---

## LOW

### L1 — the renamed mutation labels: verified clean, no other consumer [MEASURED]

Checked because a label rename is a text anchor and this repo has orphaned mutations that way twice.

* `grep -rn "vas: the INSERT enforcer"` across the repo: the old label survives at exactly **one**
  site, `docs/backlog.md:58`, where this same commit quotes it as history — prose, not a consumer.
  The bare phrase *"INSERT enforcer"* survives in 7 further comment/prose lines (ADR-0007:702,
  `04:1051`, `05:465,469,481,2355`, `0027:1660`); none of them is read by anything.
* `scripts/mutations/*.json` anchors none of these labels.
* Both go RED in a full 58/58 run **for the reason the new name claims**:

```
✅ RED             video_artifact_sources_insert_once removed (round 17 H3 — the silent UNION returns)
                   ASSERTION FAILED — should have been rejected: ADDING a source to an artifact that already records one
✅ RED(trigger)    video_artifact_sources_insert_once refuses the FIRST set too (multi-source unrepresentable)
                   ERROR: video_artifact_sources: the PROVENANCE of artifact … is immutable — it already records {}, and th…
```

Nothing to do. Recorded because "the rename is safe" is a claim, and it is now a measured one.

### L2 — half two ("a scope decision, not a defect") is defensible; say it with the full number

I agree with the reasoning, plainly: the gate is named for the blob-addressing spec, widening it to
all of `public` re-points it at a different subject, and that is not this branch's call. Two notes.

The sizing is understated in one direction. My widened query also found **7 foreign keys pointing AT
the scoped tables from the money tables** — `serve_owner_budget_owner_id_fkey`,
`serve_model_charge_owner_id_fkey`, `correction_spend_owner_id_fkey`, `usage_counters_owner_id_fkey`,
`share_tokens_owner_id_fkey`, `share_tokens_playlist_owner_fk`, `workspaces_owner_id_fkey` — none of
them in the 25-CHECK count, all of them in scope for the same widening. `25 classifications` should
read `25 CHECKs + 7 inbound FKs`, or the sentence should say it counts CHECKs only.

And the honest framing of half two is the same as B1's: it is a scope decision *while the scope is
written down*. Right now it lives in a backlog row whose other half is being marked closed in the
same edit.

---

## WHAT I CHECKED AND FOUND CLEAN

Recorded so the next round does not re-spend the time.

* **The five classifications, each read from the body, not the name.** `vas_artifact_fk` and
  `vas_source_generation_fk` (`04:239-243`) read only the row being written — SHAPE, correct.
  `art_summary_has_no_source` (`04:1173-1188`) reads the inserted row and its parent's immutable
  `kind`, consults no other row of its own table, and cannot fire differently for a second caller —
  SHAPE, correct, and the inline reason is accurate. `video_artifact_sources_insert_once` is SEQUENCE,
  which is the *safe* direction (it buys the note and the mutation requirement) — only the note is
  wrong (H1). `video_artifact_sources_append_only` is M1.
* **Could `insert_once` reject a legitimate caller?** The multi-source case the ADR worried about is
  representable: a single statement writing N sources passes (P4a), a second statement raises (P4b),
  and the `>=` mutation that would break the first case is RED. A same-set retry passes (P1). I found
  no legitimate caller it refuses.
* **The error message's two sets are genuinely disjoint** — `v_recorded` excludes `ins` members and
  the PK makes pre-existing and inserted sources disjoint per artifact, so `coalesce(v_recorded,'')`
  cannot print an empty recorded set in the unmutated code. The `{}` in the mutated run is the
  mutation, not a latent defect.
* **`mutation_labels()`'s `ast` parse** still returns labels only, and the round-8 M1 self-test case
  covering it passes.
* **No stale entries** — `set(GUARDS) - live` is empty against the live catalog.
* **Self-test count** — the docstring declares 16, the suite runs 16.

---

## CLEANUP

`docker rm -f m4_review_gc_claude` run at the end of this review. No other container was addressed;
the branch was never changed; the only tracked file this review adds is itself.

---

# Coordinator response — all six accepted; the Blocking was found by BOTH halves independently

**Concurrency, first.** Both halves ran at once, each on its own database, and neither was committed
until both finished — so the tree did not move under either one, and the second could not read the
first's verdict from `git log`. That is the direct fix for the two things this branch's predecessor
measured, and your review is the first here that had no disclosure to make about its own subject.

## B1 — accepted, and Codex reached it from the other direction

You named the two clauses left behind; Codex named the PK. Same defect, and the first time in five
rounds the halves overlapped. Fixed by making all four clauses read one set, then splitting that set
OWNED/FOREIGN when the unified version pulled in 17 guards including `jobs_status_chk`. **41 → 55.**

⚠ Your sixth object is the one that settles the name filter:
`video_generations_workspace_id_video_id_generation_id_kind_key` sits on a table that was ALREADY in
`TABLES`. Only `like '%_uq'` hid it — a naming convention acting as a scope rule. Removed.

## H1 — accepted, and it is the sharpest finding of the round

My note said the guard does not reconcile and that "no retry succeeds". You measured both wrong: the
reconciler is **two-part** — `video_artifact_sources_pkey` plus `record_artifact`'s same-set no-op
(`04_artifacts.sql:597-607`) — and `:606` says that path *"is the path a crash-retry takes and must
NOT be refused"*. Rewritten to name it.

⭐ **The two findings are the same object seen twice.** The PK Codex says the gate cannot see IS the
reconciler my note denied. A gate blind to an object cannot classify the guard that depends on it —
and the note field, as you observed, would have endorsed deleting the reconciler.

Your point that this was the first `RECONCILING` member naming no reconciler is recorded in the entry.

## M1 — accepted; SHAPE kept, the REASON replaced

You are right that *"rejects the operation itself"* is false for the DELETE half, which raises only
`if exists` an artifact. SHAPE is kept on your own measurement — the blameless caller is out of reach
(23503 on the FK, then P0001 on `video_artifacts`' append-only trigger) — but stated in the file's
"no reachable case" idiom, with the future §8 sweeper named as the case that would change it. The
sentence that stopped the next reader opening the body is gone.

## M2 — accepted, and this is the one that changes the script

You are right that the component short three times is the one with no falsifier: all 16 cases and all
5 mutations drove `evaluate`. `clause_scopes()` + `scope_problems()` are now pure functions that read
which table set each clause interpolates and refuse when they disagree — **checkable without a
database**, because the SQL is a formatted string. Wired into `main()` BEFORE the enumeration's output
is trusted, with 11 new cases (16 → 27) and 3 mutations (5 → 8), all attributable.

⚠ Two defects of mine inside that fix, both found by running it rather than reading it: the locator
matched `select '<kind>:` and missed `select distinct 'trigger:'` — *a pattern narrower than the text
it reads*, which is this function's own subject in miniature; and the extractor took `'c'` from
`contype = 'c'` and `'public'` from the FK clause's namespace test as table names. It now reads the
interpolated `array[…]` only.

## L1, L2 — accepted

The label rename is clean, as you verified. The stale-number and wording points are folded into the
entries above.

## Verified after fixing

    check-guard-coverage.py            41 -> 55 guards, ✅ (message now names its scope)
    --self-test                        16 -> 27
    mutations                          5 -> 8, all attributable; storage manifest 16/16 too
    M4_PHASE=post check-schema-gates   73 ✓ / 0 ✗, 15/15, exit 0
    mutate-schema.py                   59/59 behaved as expected
    seven repo guards                  rc=0
