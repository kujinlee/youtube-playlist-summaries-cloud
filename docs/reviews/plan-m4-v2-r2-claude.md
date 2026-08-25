# M4 plan v2 — round 2, CLAUDE half

**Subject:** `docs/superpowers/plans/2026-08-25-m4-promote-the-schema-v2.md` (v2.1)
**Branch:** `docs/m4-plan` @ `794f462` · **Anchor:** stable-blob-addressing · **ADR:** 0006, 0007, 0011
**Method:** executed. Everything below marked MEASURED was run against
`supabase_db_youtube-playlist-summaries-cloud` inside a transaction that was rolled back.

---

## ⭐ THE PRIMARY QUESTION, first

### Did v2.1's own fixes introduce new defects? **YES — three of them, and two are Blocking.**

| v2.1 fix | What it broke |
|---|---|
| **r1 B1/B6 → the `M4_PHASE` parameter** (Task 3 Step 7) | **B1.** Task 9 Step 3 and the milestone gate list still invoke the suite with no `M4_PHASE`, and `0027` exists by then. The suite now `exit 2`s **before running a single gate**. The same unsatisfiability as r1 B1/B6, one layer out |
| **r1 B5 → `insert into auth.users` in the seed** (Task 8 Step 2) | **B2.** That new line fires `on_auth_user_created`, which already inserts the `profiles` row. MEASURED: `duplicate key value violates unique constraint "profiles_pkey"`. The seed dies on its own second statement |
| **r1 B3 → Task 2 Step 5's proof grep** (new in v2.1) | **H3.** Its `Expected: no output` cannot occur — and **Task 2 Step 2's own added comment block is one of the reasons**. MEASURED: 17 lines on a *perfectly* swept `03`+`04` |

That is the standing condition from `plan-m4-v2-r1-coordinator.md:106-107` firing on its own terms.

### But the headline fix is genuinely right, and I proved it rather than trusting it.

**The rewritten `0028` runs clean. No `cascade`. Nothing survives. Nothing pre-M4 is touched.**

MEASURED. Scratchpad copies of `01/03/04` with Task 1 + Task 2 applied verbatim by content
anchor, built into a rolled-back transaction, then the plan's `0028` block (`plan:603-663`)
extracted byte-for-byte and executed:

```
===BUILD_ALL_OK===
DROP TRIGGER ×7 · DROP VIEW ×3 · ALTER TABLE ×1 · DROP TABLE ×4 · ALTER TABLE ×3 ·
DROP TABLE ×1 · DROP FUNCTION ×13 · DROP TYPE ×1
===DROP_OK===
```

Three independent assertions on that database, all inside the transaction:

1. **Forward catalog diff — `after_drop EXCEPT before` → 0 rows.** Nothing `0027` created survives, across
   tables, views, indexes, columns, triggers, functions, types, policies **and constraints**. This is
   broader than the plan's own five kinds and it is still empty.
2. **Reverse catalog diff — `before EXCEPT after_drop` → 0 rows.** `0028` removes nothing that predates
   M4. (Mandate question: no, it does not drop anything M4 did not create.)
3. **Zero silent no-ops. All 13 `drop function` signatures are correct.**
   Under `if exists` a wrong signature succeeds and the function survives, so the absence of a
   `NOTICE … does not exist, skipping` is the load-bearing observation. The run emitted **no NOTICE at
   all**. **Control, because a negative claim needs one** — the same pipeline, same flags, against
   objects I know are absent:
   ```
   NOTICE:  function public.this_function_does_not_exist(uuid,text) does not exist, skipping
   NOTICE:  trigger "no_such_trigger" for relation "public.profiles" does not exist, skipping
   ```
   The instrument can see a skip. It saw none in `0028`.

**One deliberate deviation, stated:** `0028`'s trailing `commit;` was replaced by a no-op so the outer
rollback would hold. Its own `begin;` was left in (it only WARNS). Every `drop` statement was
byte-identical to the plan. Nothing else was changed.

**Also verified against the schema, not the prose:** `M4_FUNCTIONS` (13), `M4_LIVE_TRIGGERS` (7),
`M4_TABLES` (5), `M4_COLUMNS` (3) and `M4_TYPES` (1) are **exactly** the sets the build produces —
correctly named, complete, nothing extra. Post-ADR-0011 the plan's "13 functions" is right.
Its "13 triggers" is not (M4, below). And `--expect-absent` genuinely passes on today's stack:
no M4 name collides with anything already present, so Task 3 Step 5's expectation is sound.

---

## Blocking

### B1 — The milestone's own gate invocation now exits 2 before running anything. v2.1's fix for r1 B1/B6 caused it.

Task 3 Step 7 (`plan:408-412`) makes `M4_PHASE` mandatory once `0027` exists:

```bash
if [ -f supabase/migrations/0027_stable_blob_addressing.sql ] && [ -z "${M4_PHASE:-}" ]; then
  echo "CANNOT RUN — 0027 exists, so this suite needs M4_PHASE=pre|post …"
  exit 2
fi
```

`0027` is created in Task 6. Task 9 Step 3 then runs, verbatim (`plan:900-903`):

```bash
./scripts/check-schema-gates.sh          # 9 checks, 0-8: 05_assert guard, the six, live-catalog, assertions
```

No `M4_PHASE`. The file exists. **The suite exits 2 and no gate runs.** The milestone gate list
repeats it (`plan:967-968`): *"`./scripts/check-schema-gates.sh` — **nine checks, numbered 0-8, all
green**"* — also with no phase named. Searched: `M4_PHASE` appears in the plan only inside Task 3
Step 7's own block; **no invocation anywhere in the plan sets it.**

r1 said the suite could never be green because a gate asserted the wrong polarity. v2.1 removed the
wrong polarity and replaced it with a required parameter no caller supplies. Same outcome, new cause.

**Fix:** `M4_PHASE=post ./scripts/check-schema-gates.sh` at Task 9 Step 3, and name the variable in
the milestone gate list. See also H5 — the guard is keyed to the wrong subject.

### B2 — Task 8's seed corpus fails on its own second statement, because of the line v2.1 added to fix r1 B5.

`supabase/migrations/0003_provisioning.sql:2-11` (repo-tracked, applied to every stack):

```sql
create function handle_new_user() returns trigger …
  insert into public.profiles (id, is_anonymous) values (new.id, coalesce(new.is_anonymous, false));
create trigger on_auth_user_created after insert on auth.users for each row execute function handle_new_user();
```

No `on conflict`. The seed (`plan:779-788`) inserts `auth.users` — which creates the profile — and
then inserts the profile again. MEASURED, seed run verbatim against a freshly built M4 schema:

```
INSERT 0 1
ERROR:  duplicate key value violates unique constraint "profiles_pkey"
DETAIL:  Key (id)=(00000000-0000-0000-0000-0000000000a1) already exists.
```

`scripts/run-schema-assertions.sh` runs the seed under `ON_ERROR_STOP=1` (`plan:825-829`), so
`ASSERTIONS_OK` never prints and the harness exits 1. **Gate `8/8` can never pass**, and Task 8
Step 4's `expect 0` is unreachable.

Round 1 found the seed could not insert a row for two reasons. v2.1 fixed both and the fix for the
first created a third. **Deleting the `insert into profiles` line is the whole repair** — MEASURED
with it removed, on the same build:

```
INSERT 0 1 · INSERT 0 1 · INSERT 0 1
===SEED_OK===
 ws_derived |  video_id
------------+------------
 t          | seedvid001
```

The derive path fires and `workspace_id` is non-null, so `:1843-1859`'s subject is genuinely
exercised — the rest of the seed is correct, and `videos`/`playlists` satisfy every `NOT NULL`
(checked against `information_schema`: `playlists` needs `owner_id, playlist_key, playlist_url`;
`videos` needs `playlist_id, owner_id, video_id, position, data`; all supplied).

### B3 — Task 4 Step 2's snippet kills gate 1 on every run. `$REPO` does not exist.

`plan:465`: `if python3 "$REPO/scripts/check-live-schema.py" --expect-present …`

`verify-schema.sh` never defines `REPO`. Searched, not assumed:

```
$ grep -c "REPO" docs/superpowers/specs/2026-08-03-stable-blob-addressing/verify-schema.sh
0
```

and the script opens `set -uo pipefail` (`verify-schema.sh:7`). MEASURED:

```
$ bash -c 'set -uo pipefail; if python3 "$REPO/scripts/check-live-schema.py" …; then …; fi; echo "reached the end"'
bash: REPO: unbound variable
exit=127
```

It never reaches the end. Pasted as written, gate `1/6` aborts at that line on **every** invocation,
before and after `0027`. Task 4 Step 1 defines `MIGRATION` via its own `$(cd … && pwd)` subshell and
never introduces `REPO`; Step 2 assumes a variable Step 1 did not create.

---

## High

### H1 — Task 3 Step 6's mutation proof can never go red. Codex r1 H2 said so; v2.1 left the step unchanged.

`plan:380-389` opens a heredoc, `begin;`, `create table public.workspaces`, and then says *"in the
same session run `--expect-absent` and expect **exit 1**"*. `check-live-schema.py` is a separate
process opening a new connection; the heredoc session has already ended and its transaction was never
committed. MEASURED, running the step's block verbatim and then querying from a new connection:

```
select count(*) … relname='workspaces';
 0
```

The gate sees nothing, returns **exit 0**, and the step records a passing mutation test as proof the
gate can fail. This repo has a memory for exactly this (`a-checklist-item-can-be-an-unfalsifiable-guard`).
The coordinator's fold-in table (`plan-m4-v2-r1-coordinator.md:63-74`) does not list Codex H2 at all,
which is how it survived.

**Fix:** commit the mutation in one session, run the gate, then drop it — or have the gate accept a
`PGDATABASE`/scratch target so the mutation and the read share a transaction.

### H2 — Task 2 Step 4's "five sites" are not the sites. Two whole blocks are missing and one cited range is truncated.

The mandate said search rather than trust the list, so I did. Of the `corrections` references in
`05_assert.sql` that touch the **dropped columns**, the plan's table (`plan:220-226`) omits:

- **`:917-919`** — `assert_raises($$insert into workspace_videos (workspace_id, video_id, corrections_hash) values (…, null)$$, …, '23502')`. Inserts into a column Task 1 deletes.
- **`:1898-1918`** — the round-9 clobber assertion: `if (select corrections from workspace_videos where video_id='sharedCorr') is distinct from 'KEEP ME'`. This is the assertion **for the very mechanism Task 1 Step 5 deletes** (`sync_corrections_to_workspace_video`), and no task mentions it.

And the anti-drift entry cites `:899-905` while the enclosing `do $$ … end $$;` block runs **`:894-915`**.
Deleting `:899-905` alone leaves `:908-914` — the "clearing corrections restores the constant" half —
still reading `wv.corrections_hash`. MEASURED: taking the plan's five ranges at their word (generously,
whole enclosing block for `:62`), **14 `corrections` lines survive** that the plan's own Step 5 filter
does not exclude.

Severity is High rather than Blocking only because Step 5's grep *would* surface them — but see H3,
because Step 5 cannot produce the observation it asks for.

### H3 — Task 2 Step 5's `Expected: no output` cannot occur, and Task 2 Step 2's own comment is part of why.

Step 5 (`plan:234-239`):

```bash
grep -rn "corrections" …/schema/ | grep -v "corrections_hash_of\|no_corrections_hash\|^.*:-- "
# Expected: no output
```

The filter `^.*:-- ` requires `:` immediately followed by `-- `, which in `grep -rn` output only
matches a **column-0** comment. Every **indented** comment survives. MEASURED today: 53 lines pass the
filter, **14 of them plain comments**.

Worse, it is self-inflicted. Task 2 Step 2 instructs the implementer to insert a replacement comment
indented nine spaces, whose second and fourth lines contain the word `corrections`. MEASURED on
`03`+`04` swept **perfectly** (Task 1 + Task 2 applied by content anchor, Step 2's own block inserted
at both sites), 05 excluded:

```
step5/04_artifacts.sql:718:         -- reflects the corrections currently in force", comparing an IMMUTABLE stamp inside a frozen
step5/04_artifacts.sql:720:         -- reflect corrections that had since been overwritten, undetected.
step5/04_artifacts.sql:781:         -- reflects the corrections currently in force", …
step5/04_artifacts.sql:783:         -- reflect corrections that had since been overwritten, undetected.
… 17 lines total
```

**Step 2's fix defeats Step 4's verification, inside the same task.** A step whose stated expected
observation cannot occur is not a gate — the implementer either ignores it or deletes the explanatory
comments the plan just told them to write.

**Fix:** make the filter structural (`grep -vE ':[0-9]+: *--'`) and scope it to the two dropped column
names rather than the substring `corrections`.

### H4 — `--expect-present` cannot see views, policies, indexes, constraints or grants — and a partial apply is the exact scenario it exists for.

`verdict()` (`plan:351-363`) is correct for the five kinds it has, and I confirmed the `absent` branch
by hand against the post-`0028` database: `not (found & expected)` per kind, all five empty, verdict
`True`, correctly `False` on any survivor. The logic is sound.

The gap is the kinds not chosen. MEASURED, what `0027` actually creates:

| kind | count | seen by `--expect-present`? |
|---|---|---|
| tables | 5 | ✅ |
| columns | 35 (3 on live tables) | ✅ the 3 |
| triggers | **14** | ✅ the 7 live-table ones |
| functions | 13 | ✅ |
| types | 1 | ✅ |
| **views** | **3** | ❌ |
| **policies** | **5** | ❌ |
| **indexes** | **12** | ❌ |
| **constraints** | **38** | ❌ |

`--expect-present` returns 0 on a database with **no views** — and the three views *are* the product's
read path. The plan itself flags the reachable route: the one-transaction guarantee "belongs to the
apply command, not the SQL" and is void for `psql -f` or a dashboard paste (`plan:24`), and
`supabase db push --linked`'s one-transaction property is listed under **Still NOT VERIFIED**
(`plan:985`). So the plan simultaneously says a partial apply is possible and ships the gate that
would bless one.

r1 B7/B2 said "tables and columns cannot prove **absence**". v2.1 added three kinds that close the
absence direction — which I verified works — and applied the same five by symmetry to the **present**
direction without asking what a partial apply looks like. Fixed the direction that was reported.

### H5 — The `M4_PHASE` guard is armed on the FILE; the thing it describes is the DATABASE.

`[ -f supabase/migrations/0027_stable_blob_addressing.sql ]` is a property of the **checkout**.
Whether M4 is applied is a property of the **machine**. The plan deliberately separates them: Task 6
Step 6 and Task 8 Step 5 both end with `npx supabase migration up`, *"so the branch is left in the
migrated state"*.

So: finish Task 6, `git checkout master`. The file is gone, the guard does not fire,
`case "${M4_PHASE:-pre}"` selects `--expect-absent`, and the live gate goes **red on master** for a
reason that has nothing to do with master. Meanwhile Task 4 Step 2's cannot-run branch keys on the
**database** and correctly reports CANNOT RUN. The plan names this hazard itself at `:421-423` —
*"that branch and this parameter must tell the same story, or the suite contradicts itself"* — and
then writes the two halves against different subjects.

This is the shape `dev-process.md` records from the blob-addressing retrospective: *the inventory was
right; the arming condition was wrong.*

**Fix:** arm on the database. `check-live-schema.py` already knows how to look.

### H6 — Task 4 Step 1 silently removes `05_assert.sql` from the only gate that runs it, and the MIGRATION-ONLY assertions end up with no runner at all.

`verify-schema.sh:10` today: `cat "$DIR"/0*.sql` — which globs `01, 03, 04, **05**`.
`check-schema-gates.sh:13-16` states this as the design: *"`verify-schema.sh` concatenates 01/03/04/05
between a `begin` and a `rollback`. **Gate 1 below is the only correct way to run them.**"*

Task 4 Step 1 changes the glob to `0[134]*.sql` with the note *"the old glob included `05_assert.sql`,
which is exactly the file that must never execute as schema"* (`plan:458`). That reasoning is about
**`0027`**, and it is right about `0027`. But it also drops 05 from the **pre-promotion** branch,
where running it inside a rollback is the entire point.

Task 8 then gives a home only to the `@RE-RUNNABLE` subset (`plan:818-819`). **Nothing in the plan
ever runs the `@MIGRATION-ONLY` assertions** — including the backfill assertion the plan itself quotes
at `05_assert.sql:56-58` as the worked example of the category. The milestone gate list has no entry
for them either.

Round 1 focused on Tasks 1-3, 6, 8; this is in Task 4, which got less attention.

---

## Medium

### M1 — Codex r1 H3 was marked "to verify at fold-in" and then not fixed. Both sites still stand.

```
$ grep -n "sync_corrections" scripts/check-guard-coverage.py
53:# guards" with a brand-new guard sitting outside its query. `sync_corrections_to_workspace_video`
119:    "sync_corrections_to_workspace_video": (
168:    "sync_corrections_to_workspace_video": ("the anti-drift trigger removed",

$ grep -n "corrections" scripts/check-sentinel-meanings.py
9:  * `workspace_videos.corrections_hash` nullable = "no corrections" OR "nobody
71:    ("workspace_videos", "corrections"):     "this video carries no correction text",
```

Task 5 Step 2 says delete the `art_pending_*` entries and add `video_artifact_sources` coverage —
neither covers `:119`/`:168`. Task 5 Step 3 fixes the **docstring** at `:9` and the Files list scopes
the file to `:9,48`, leaving the **live inventory entry** at `:71` describing a column ADR-0011
deletes. `check-sentinel-meanings.py:173` reconciles catalog→inventory (`if key not in meanings`), so
a dead entry in the other direction is **not** flagged: Task 5 Step 4's "expect all `0`" will hold
while the ratchet quietly carries a meaning for an object nobody can find. That is precisely what
Step 3's own sentence warns against, applied to the entry it did not search.

### M2 — The self-test has 8 cases; the plan says 5, twice, and the expected output can never appear.

`plan:283-298` contains **8** `check(...)` calls. The docstring says `--self-test  # 5 cases`
(`plan:316`) and Step 4 says *"Expected: `5/5 self-test cases passed`"* (`plan:373`). The code prints
`f"{cases - failures}/{cases}"` → `8/8`. r1's gate had fewer cases; v2.1 expanded it and updated
neither number.

### M3 — The `check-live-schema.py` docstring still describes the two-kind gate v2.1 replaced.

`plan:325-326`: *"FAILS IF: `--expect-present` and any of **the five tables or three columns** is
missing; `--expect-absent` and any of **them** survives."* The gate now checks five kinds. The
`FAILS IF:` clause is this repo's falsifiability statement (`scripts/check-gate-falsifiability`), and
it under-describes the gate in exactly the direction the fix was about — true about the kinds it
names, silent about the three that were the whole point.

### M4 — The "derived, not listed" inventory is a `grep` artifact, and it is wrong by one trigger.

`plan:596-597`: *"**44 objects** — 5 tables, 3 views, 14 functions, 15 triggers, 1 enum, 3 indexes,
5 policies. After ADR-0011: **13 functions, 13 triggers.**"*

MEASURED from the catalog: **14 triggers**, not 13. The missing one is
`art_summary_has_no_source_trg`, created at `04_artifacts.sql:1149` by **`create constraint trigger`** —
which `grep "^create trigger"` cannot see. (It is harmless to `0028`: its table is one of M4's own and
it dies with the `drop table`. The defect is the claim, not the SQL.)

Same shape for the rest: "3 indexes" is the count of explicit `create index` statements against **12**
in the catalog, and "44 objects" is a statement count against **91** non-column objects + 35 columns.
Defensible as a statement inventory; not what "derived" implies, and it is the number a `0028` author
would check their work against.

### M5 — Task 4 Step 4 is one sentence for a rewrite the plan itself calls a rewrite.

`plan:442` insists *"This is a REWRITE, not a re-point"*. `mutate-schema.py:26-27` hardwires **two**
files (`GEN`, `ART`) and never touches `01_workspaces.sql`; after promotion there is **one** file
containing all three. Step 4's *"apply the same source-selection"* does not say what the two-file
structure becomes, and Step 4's expectation — *"the mutation suite runs and every mutation is
caught"* — does not say against which source. Step 5 asks for a mutation proof but not for a
before/after mutation **count**, which is the observation that catches a harness now reading a
different set.

### M6 — Task 3 never exercises its own cannot-run path, and never specifies the half where that rule lives.

Task 3 Step 3 gives the constants and `verdict()` — the pure part — and nothing else: no argument
parsing, no catalog queries that build `found`, no psql invocation, no exit-2 path. The docstring
promises `exit 2` on an unreachable database. **No step runs it.** Contrast Task 8 Step 4, which
explicitly requires *both* branches be executed and says why (`plan:850`). The same rule, applied in
one task and skipped in the neighbouring one, in the milestone whose stated purpose is gates that read
live state.

---

## Low

- **L1** — Gate numbering, Codex r1 M1, unfixed. Task 7 adds `0/8`, Task 3 adds `7/8`, Task 8 adds `8/8`; `check-schema-gates.sh:30-46` still reads `1/6`…`6/6` and no task renumbers them. The milestone gate asserts the observation *"nine checks, numbered 0-8"* (`plan:967`), which is not what the suite will print.
- **L2** — Task 2 has **two** steps numbered "Step 5" (`plan:232` and `plan:244`).
- **L3** — After Task 2 removes the ranking term, `join workspace_videos wv` remains in both views (`04:698-699` and its sibling) with `wv` referenced only in the join predicate. It still parses (verified in the build) and functions as an existence filter — but it is now load-bearing by accident rather than by statement. One sentence in the Step 2 comment would fix it.
- **L4** — Codex r1 M2, unfixed: `05_assert.sql:37` / `:2207` are still cited by line (`plan:22`, `:801`) in a plan whose Task 8 edits that file. Same class as r1 B4, which v2.1 fixed for Task 1 by switching to content anchors.

---

## Anchor uniqueness (mandate item e) — this one is clean

Every content anchor Task 1 quotes resolves **exactly once**. Verified mechanically rather than by
eye — the applier aborts on a count ≠ 1:

```
anchor 'T1S2 corrections text': 1 occurrence(s)
anchor 'T1S2 corrections_hash default': 1 occurrence(s)
anchor 'T1S3 backfill stmt': FOUND       anchor 'T1S4 trigger upsert': FOUND
anchor 'T1S5 sync fn body': FOUND        anchor 'T1S5 revoke': 1 occurrence(s)
anchor 'T1S5 videos_corrections_sync_ins_trg': FOUND   …_upd_trg: FOUND
anchor 'T2S2 ranking term': removed 2 line(s) (plan expects exactly 2)
```

Task 1 Step 1's and Step 6's counts are also right, checked against the file:
`grep -c "corrections" 03_generations.sql` → **50** (plan says 50);
`grep -c "^create trigger"` → **10** before, **8** after (plan says 10 → 8).

The v2.1 switch from line numbers to content anchors is correct and it worked.

---

## IS THIS PLAN EXECUTABLE AS WRITTEN?

**No.** Three Blocking defects stop execution at named steps: the milestone gate suite refuses to run
(B1), gate `8/8` cannot pass (B2), and gate `1/6` aborts on an unbound variable (B3). Each is a small
edit. None requires re-deriving design — which is a real improvement over round 1, where the rollback
itself was wrong.

## The single most important finding

**B2 — the seed corpus, because of *why* it broke.** `0028` was the round-1 headline and v2.1 fixed it
properly; I executed it and it is correct. The seed is the opposite: round 1 found two reasons it
could not insert a row, v2.1 fixed both, and the fix for the first (`insert into auth.users`) created
a third by reaching a trigger nobody looked for. The plan reasoned about `0001_core_schema.sql`'s
`NOT NULL`s and FKs — the constraints the reviewer had **named** — and stayed silent about
`0003_provisioning.sql`, the layer that acts when you write to the table those constraints describe.
It is this repo's dominant defect shape (`true-about-the-name-silent-about-the-layer`) reproduced
inside a fix for a finding about incompleteness. B1 is the same story with a different subject: a
required parameter added, and no caller updated to supply it.

The class fix is one line in the checklist, not three patches: **when a fix adds a WRITE, ask what
already fires on that write.**

---

## Cleanup — verified, not assumed

All DDL ran inside transactions that were rolled back; the two edited schema files are scratchpad
copies, never repo-tracked ones. Verified after the last run:

```
$ git status --porcelain
?? docs/reviews/plan-m4-v2-r2-codex.md          # the Codex half's file, not mine

M4 tables in public:            0
workspace_id columns anywhere:  0
artifact_kind type:             0
playlists=5124 videos=3547 profiles=6303 auth_users=6303
```

Row counts match the round-1 coordinator's figures exactly. The shared local stack is unmutated.

## NOT VERIFIED — do not read these as cleared

- **`supabase db push --linked`'s one-transaction property.** Not executed. H4's severity depends on it.
- **`mutate-schema.py` against a single-file source.** M5 is read from `:26-27` and the plan's own text; I did not run the mutation suite.
- **Whether `check-guard-coverage.py` goes red or silently passes** on its stale `sync_corrections_to_workspace_video` entries (M1). I read the entries and `check-sentinel-meanings.py`'s reconciliation direction; I did not run the guard-coverage ratchet against a post-ADR-0011 schema.
- **Task 9 Steps 1, 4, 6, 7 and Task 10.** No `CLAUDE_RO_DATABASE_URL` in this environment, and M4-β is outward-facing. Not examined against production.

NOT CONVERGED
