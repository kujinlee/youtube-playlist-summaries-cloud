# M4 plan v2 — round 3, CLAUDE half

**Subject:** `docs/superpowers/plans/2026-08-25-m4-promote-the-schema-v2.md` + the seven extracted artifacts
**Branch:** `docs/m4-plan` · **PR #150**
**Anchor:** stable-blob-addressing · **ADR:** 0006, 0007, 0011

**⚠ THE SUBJECT MOVED MID-REVIEW — BOTH BUILDS ARE NAMED ON EVERY MEASUREMENT.**
I was dispatched against `2649094` with a clean tree. At 14:47–14:50 PDT, while I was executing, the
coordinator folded the Codex half's round-3 findings into `scripts/build-m4-schema.py`,
`scripts/run-schema-assertions.sh` and the plan, and committed them as **`5d5f1ed`**. Every finding
below was therefore **re-executed against `5d5f1ed`** and is labelled with the build(s) it holds on.
Two of my findings were independently found by Codex and are already closed; the rest survive the
fold. *(This is `an-instrument-that-edits-the-repo-corrupts-its-peers`, one layer out: not a harness
rewriting tracked files, but a concurrent fix rewriting the reviewed subject. It is worth a line in
the coordinator's notes — a round-3 reviewer measuring `2649094` and reporting against `5d5f1ed`
is how a "does not reproduce" verdict gets manufactured.)*

**Method: executed.** Everything marked MEASURED was run. Scratch databases `r3rev_probe`,
`r3rev_probe2` were built and dropped; the shared stack was never mutated (verified below).

---

## ⭐ First: the round-2 decision worked. Every headline claim reproduces exactly.

The mandate said re-run the claims. I re-derived all of them from scratch rather than reading the
plan's tables. **Not one is wrong.**

| Claim | Where | My measurement | |
|---|---|---|---|
| `check-live-schema.py --self-test` = 16 | `:326` | **16/16, exit 0** | ✅ |
| `build-m4-schema.py --self-test` = 14 | `:525` | **14/14, exit 0** (`2649094`); **18/18** at `5d5f1ed` | ✅ |
| `mutate-live-schema-check.sh` 3/3 | `:327` | **3/3 caught, exit 0** | ✅ |
| Inventory **161** objects | `:566` | **161** | ✅ |
| 70 columns · 38 constraints · **14** triggers · 13 functions · 12 indexes · 5 tables · 5 policies · 3 views · 1 enum | `:557-566` | **70 · 38 · 14 · 13 · 12 · 5 · 5 · 3 · 1** | ✅ exact |
| The 14 split **7 live / 7 own** | `:574-577` | 7 on `profiles`/`playlists`×2/`videos`×2/`jobs`×2; 7 on M4's own tables | ✅ |
| `art_summary_has_no_source_trg` is a `create constraint trigger`, so grep misses it | `:568-572` | confirmed — it is in the catalog's 14, absent from `grep -c "^create trigger"` | ✅ |
| Rollback: `skipping-notices: 0 · LEFTOVER: 0 · DESTROYED: 0` | `:616` | **0 / 0 / 0**, exit 0 | ✅ |
| `13 DROP FUNCTION · 7 DROP TRIGGER · 5 DROP TABLE · 4 ALTER TABLE · 3 DROP VIEW · 1 DROP TYPE` | `:615` | **13 · 7 · 5 · 4 · 3 · 1** | ✅ exact |
| `schema_paths = []`, nothing under `supabase/rollback/` is replayed | `:605` | `config.toml:64` confirmed; `sql_paths = ["./seed.sql"]` (`:71`, no glob); `grep -rn` for `supabase/rollback` outside `docs/` → **0 hits** | ✅ (see L2) |
| Task 1's ⚠ correction: `corrections_hash_of` has no caller after Task 2 | `:71-81` | confirmed — only its own definition, `revoke`, and `no_corrections_hash` called from inside it | ✅ |

**The rollback proof, re-run independently.** I cloned the live pre-M4 schema into a throwaway
database, applied `build-m4-schema.py`'s output (161 adds, 0 removes), ran the rollback file
**verbatim** under `ON_ERROR_STOP=1`, and diffed a nine-kind catalog snapshot **both directions**:

```
rollback-exit=0     skipping notices: 0     errors: 0
LEFTOVER  (rolled EXCEPT before): (none)
DESTROYED (before EXCEPT rolled): (none)
check-live-schema.py --expect-absent -> exit 0
```

The rollback is genuinely correct. **The three Blockings below are not in it.**

---

## Blocking

### B1 — `build-m4-schema.py`'s end-state verdict is blind to the two column edits it exists to make. **MEASURED on both builds.**

The docstring (`:21-26`) and the plan (`:523-525`) rest the whole design on one claim:

> The verdict does NOT rest on the edits, though — it rests on the END STATE, which is asserted
> regardless of how the file got there. That is deliberate: anchors are a means, and **a means that
> silently stops matching is exactly the failure this repo keeps measuring.**

**That claim is false for 2 of the 8 edits — and they are the two that define the ADR-0011 columns.**

`apply_edits`' `sub()` treats `n == 0` as `already` and returns the text unchanged
[`build-m4-schema.py:91-93`]. So an anchor that drifts is a **silent skip**, and the only thing
standing behind it is `assert_end_state`. Its residual check is:

```python
residual = [ln.strip() for ln in code.splitlines()
            if "corrections_hash" in ln
            and "corrections_hash_of" not in ln and "no_corrections_hash" not in ln]
```
[`build-m4-schema.py:119-121`, unchanged at `5d5f1ed`]

The line `COL_B` must delete is `03_generations.sql:61`:

```sql
  corrections_hash   text not null default no_corrections_hash(),
```

It contains `no_corrections_hash`, so **the residual filter excludes the very line it is meant to
catch.** And `COL_A`'s line (`  corrections        text,`) contains no `corrections_hash` at all, so
the filter never looks at it. Neither column has any other assertion.

MEASURED — I copied the spec to a temp dir and drifted **one space** in each anchor in turn:

| Drift | `2649094` | `5d5f1ed` |
|---|---|---|
| `COL_B` (one space) | `build-exit=0`, `already  T1.2b`, output line 111 = `corrections_hash  text not null default no_corrections_hash(),` | **identical** |
| `COL_A` (one space) | `build-exit=0`, `already  T1.2a`, output line 103 = `corrections       text,` | **identical** |

`build-m4-schema.py` exits **0**, reports the edit as `already`, and emits into `0027` the exact
column ADR-0011 removes — the object whose presence produced nine of eleven findings across five
rounds.

**Why the r3 fold does not close it.** Codex found a neighbouring defect (a `--` inside a string
literal blinding `strip_comments`) and the coordinator hardened `strip_comments` and grew the
self-test 14 → 18. **The residual filter was not touched, and none of the four new cases covers an
anchor drift.** The predicate is still the verdict, and it is still blind here.

**Blast radius.** `mutate-live-schema-check.sh:68` consumes this builder's output as "the REAL
pre-M4 schema". A silently partial build means the live gate is re-proven against a schema M4 will
never ship — *precisely* the defect the plan's own "fourth measurement" (`:314-318`) was written to
close, re-entered through a different door. The live gate's `ADR0011_REMOVED` columns check would
catch the consequence at Task 6 Step 4, so this is defended in depth — but the plan names this
builder as the thing that makes Task 6 Step 1 safe, and it does not.

**Fix:** assert on the *end state* as advertised — `if re.search(r"^\s*corrections(_hash)?\s+text", code, re.M)` inside the `workspace_videos` block, independent of `corrections_hash_of`. Or make `sub()`'s `already` branch require positive evidence the edit already landed, rather than inferring it from a non-match.

---

### B2 — `check-live-schema.py --expect-present` blesses a database with **all seven** of M4's own-table guard triggers missing. **MEASURED.**

The plan calls this gate *"the only instrument that can confirm M4-β happened"* (`:46`) and Task 9
Step 7 (`:892`) makes it the sole production verification.

`EXPECTED["triggers"]` is `M4_LIVE_TRIGGERS` — the 7 on live tables [`check-live-schema.py:53-56`] —
and `--expect-present` tests `EXPECTED[k] <= found.get(k)` [`:147`]. M4's own-table triggers are in
no expected set, so their absence is invisible.

MEASURED against a scratch database with M4 applied:

```
baseline                                        --expect-present exit=0
drop video_artifacts_append_only_trg            --expect-present exit=0
drop ALL SEVEN own-table triggers               --expect-present exit=0
  -> "live schema: M4 is PRESENT as expected (5 tables, 3 columns, 7 live triggers, 13 functions, 1 type)"
remaining M4 own-table triggers in that db: 0
```

The seven dropped are `video_generations_freeze_trg`, `forbid_collecting_current_trg`,
`video_artifacts_append_only_trg`, `video_artifacts_generation_complete_trg`,
`video_artifact_sources_append_only_trg`, `video_artifact_sources_insert_once_trg`,
`art_summary_has_no_source_trg` — **every append-only, freeze and immutability guard in the
blob-addressing design.** The gate says PRESENT AS EXPECTED.

Set against the plan's own inventory, measured by me:

| Kind | Inventory | Gate names |
|---|---|---|
| tables | 5 | 5 |
| functions | 13 | 13 |
| types | 1 | 1 |
| triggers | 14 | **7** |
| columns | 70 | **3** |
| views | 3 | **0** |
| indexes | 12 | **0** |
| policies | 5 | **0** |
| constraints | 38 | **0** |
| **total** | **161** | **29 (18%)** |

The plan prints the 161-object inventory table (`:557-566`) five paragraphs from the claim that this
gate confirms M4-β, and the gap between them is never stated. **Zero of the three views** are checked
either — including `video_artifacts_current`, whose dependency ordering the rollback treats as
load-bearing (`:544`).

This is not hypothetical. `:952` lists `supabase db push --linked`'s one-transaction property as
**Still NOT VERIFIED** — "help-checked, never a real remote push." A partial apply is exactly what
that unverified property would permit, and the instrument designated to detect it can see 18% of the
milestone.

**Fix:** the gate already has the honest inventory available — `M4_OWN_TRIGGERS` (7 names) costs one
tuple, and views cost one more catalog query. At minimum, `--expect-present` must assert the full
14 triggers and the 3 views.

---

### B3 — the rollback never reverses the migration ledger, so Task 6 Step 6's re-apply is a silent no-op.

`supabase/rollback/rollback_0027_stable_blob_addressing.sql` drops objects and nothing else.
MEASURED: `grep -c "schema_migrations"` on the rollback file → **0**. On the plan → **0**. The word
does not appear in either artifact.

The sequence is:

- **Task 6 Step 4** (`:643`): `npx supabase migration up` → `0027` applied **and recorded** in `supabase_migrations.schema_migrations`.
- **Task 6 Step 5** (`:653-654`): the rollback runs via `psql`. Objects are dropped. **The ledger row for `0027` remains.**
- **Task 6 Step 6** (`:665`): `npx supabase migration up` — *"Re-apply `0027` so the branch is left in the migrated state"*.

The CLI's own help: *"Apply **pending** migrations to local database"*, and
`--include-all  Include all migrations not found on **remote history table**`. Pending is defined by
the history table, which still carries `0027`. **Step 6 applies nothing.** The branch is left with
M4 absent from the database while the ledger asserts it is applied — and `supabase migration up` can
never restore it.

Everything downstream then runs against a schema that is not there:

- **Task 8 Step 4** (`:801-803`) runs the rollback, then **Step 5** (`:810`) re-applies with the same no-op command; gate 8 is wired in at that point and `run-schema-assertions.sh:40-44` exits 2 forever.
- **Task 9 Step 3** (`:856`) `M4_PHASE=post` → gate 7 `--expect-present` goes red.
- Every developer's local stack lands in a state recoverable only by `supabase db reset`.

**Bound, stated honestly.** I did **not** execute `supabase migration up` — doing so would apply
migrations to the shared local stack, which the mandate forbids. The evidence is (a) `grep` counts of
0 on both artifacts, definitive; (b) the CLI's own documented semantics, quoted above from
`npx supabase migration up --help` on CLI 2.115.0; (c) `npx supabase migration list --local`,
which reports per-version `local`/`remote` state from that table (26 rows, `0001`–`0026`). **The
ledger-driven behaviour is documented, not measured by me — treat that one link as NOT RUN.** The
gap in the artifacts is measured and is sufficient on its own: nothing anywhere reverses the row.

**Fix:** add `delete from supabase_migrations.schema_migrations where version = '0027';` inside the
rollback's existing `begin/commit` — it belongs in the same transaction as the drops, or the
"one transaction" guarantee covers the schema and not the claim about the schema. Then Task 6 Step 6
works as written.

---

## High

### H1 — Task 4 Step 1 deletes 104 behavioural assertions from gate 1, and nothing replaces them. **MEASURED.**

Today `verify-schema.sh:10` is:

```bash
SQL=$(printf 'begin;\n'; cat "$DIR"/0*.sql; printf '\n\\echo ALL_STATEMENTS_OK\nrollback;\n')
```

`0*.sql` includes `05_assert.sql`. MEASURED: `05_assert.sql` holds **104** `raise exception`
assertions, and `./verify-schema.sh` today exits **0** with `ALL_STATEMENTS_OK` — so all 104
currently execute, every time gate 1 runs.

`check-schema-gates.sh:13-16` says so in its own words:

> `05_assert.sql` CANNOT be run standalone … so `verify-schema.sh` concatenates 01/03/04/05 between
> a `begin` and a `rollback`. **Gate 1 below is the only correct way to run them.**

Task 4 Step 1 (`:396`) changes the glob to `0[134]*.sql`, justified as: *"the old glob included
`05_assert.sql`, which is exactly the file that must never execute as schema"* (`:401`).

**Two problems.**

1. **The rationale is aimed at the wrong risk.** The danger `05_assert.sql` poses is being *promoted
   into a migration* — and that is already guarded mechanically, twice, by Task 6 Step 2 (`:531`) and
   Task 7 Step 3 (`:703-705`). Executing it inside gate 1's rolled-back transaction is its *designed
   home*, per the note above. The change removes the safe execution, not the unsafe one.
2. **The replacement covers a subset that is empty by default.** `run-schema-assertions.sh` runs only
   the `@RE-RUNNABLE` block. MEASURED: `05_assert.sql` carries **0** `@RE-RUNNABLE` and **0**
   `@MIGRATION-ONLY` markers today. Task 8 Step 1 (`:730-737`) says to tag assertions but never
   requires every assertion to be tagged, and by construction the `@MIGRATION-ONLY` ones are
   *excluded* from the only remaining runner. After Tasks 4 and 8, **the MIGRATION-ONLY assertions —
   the ones that check the migration's actual output, which is the entire point of M4 — are executed
   by nothing.**

No task updates `check-schema-gates.sh:13-16`, so the suite ships a comment that is false.

**Fix:** keep `05_assert.sql` in gate 1 (it is rolled back; the promotion guards are elsewhere), or
state explicitly in Task 8 Step 1 that the MIGRATION-ONLY subset is run once at Task 6 Step 4 and
name the command that runs it.

---

### H2 — `M4_PHASE=post ./scripts/check-schema-gates.sh` "nine checks, all green" is unsatisfiable.

`check-schema-gates.sh:26` fails on **any** non-zero exit:

```bash
if "$@"; then :; else echo "❌ FAILED: $*"; fail=1; fi
```

Task 4 Step 2 (`:407-414`) gives gate 1 a branch that exits **2** when `0027` is applied. At
`M4_PHASE=post`, `0027` *is* applied — so gate 1 exits 2 and the suite goes red. Gate 2
(`mutate-schema.py`) rebuilds from source the same way; Task 4 Step 4 (`:421-426`) re-points its
source selection but gives it **no cannot-run branch at all**, so at post-phase it fails with
`relation "workspaces" already exists`.

Yet **two** places assert all-green at post-phase:

- Task 9 Step 3 (`:856`): `M4_PHASE=post ./scripts/check-schema-gates.sh   # 9 checks, 0-8`
- Milestone Gates, item 1 (`:932-935`): *"nine checks, numbered 0-8, **all green**"*

The plan **sees** this and does not resolve it — `:364-366`:

> ⚠ Gates 1 and 2 have the **same** problem in the opposite direction … Task 4 Step 2 gives them a
> cannot-run branch; **that branch and this parameter must tell the same story, or the suite
> contradicts itself.**

It then writes the contradiction. This is the same class as r1 B1/B6, which the plan claims to have
*class*-fixed (`:342-344`: *"Fixing the instance did not fix the class"*) — and CLAUDE.md's rule
("cannot run is a FAILURE, never a pass") collides head-on with a checklist that requires all-green.
One of the two must give, and the plan must say which.

**Fix:** teach `run()` to distinguish 2 from 1 (`SKIPPED (not applicable at this phase)` vs `FAILED`), and say so in the gate list — or make gates 1–2 not members of the post-phase suite at all.

---

### H3 — Task 4 Step 2's snippet dies on an unbound variable, exiting **1** from the branch designed to exit 2. **MEASURED.**

`verify-schema.sh:7` is `set -uo pipefail`, and the script defines only `DIR` (`:8`) and `CONTAINER`
(`:9`). Task 4 Step 1's snippet adds `MIGRATION`. **`REPO` is never defined anywhere** — yet Step 2's
snippet opens with:

```bash
if python3 "$REPO/scripts/check-live-schema.py" --expect-present >/dev/null 2>&1; then
```

MEASURED, running that snippet in `verify-schema.sh`'s exact preamble:

```
repotest.sh: line 5: REPO: unbound variable
exit=1
```

So the branch written to say *"CANNOT RUN … Treat this as NOT RUN"* and exit 2 instead dies with a
bash error and exit **1**, which `check-schema-gates.sh` reports as `❌ FAILED:
…/verify-schema.sh` — i.e. *"the schema failed to verify"*. A gate that cannot reach its subject
reporting a subject failure is the precise confusion the branch exists to prevent.

**This is round 1/2's finding shape — a defect in fenced code that has never been executed — and it
is not "closed by construction."** The extraction moved seven artifacts out of the plan; Task 4's
two snippets stayed behind, and they are still wrong. (Fix: `REPO="$(cd "$(dirname "$0")/../../../.." && pwd)"`, which Step 1 already computes inline for `MIGRATION` and should hoist.)

---

## Medium

### M1 — the legend Task 8 Step 1 prints re-opens the selector fail-open. **MEASURED, survives `5d5f1ed`.**

Task 8 Step 1 (`:734-737`) instructs the worker to tag assertions and prints this block:

```sql
-- @MIGRATION-ONLY: compares the migration's output; any later write invalidates it.
-- @RE-RUNNABLE:    an invariant that must hold at all times.
```

Written at the top of the file as a legend — which is what "tag each assertion" naturally produces —
the `@MIGRATION-ONLY` line sets `p=0` and the `@RE-RUNNABLE` line immediately sets `p=1`, so **the
entire rest of the file is selected as re-runnable**, MIGRATION-ONLY blocks included.

MEASURED against the **current** (`5d5f1ed`) selector, which now requires the marker to sit on a
comment line — the legend lines *are* comment lines, so the hardening does not help:

```
awk selects: the whole file after the legend, including the trap block
run-schema-assertions.sh -> exit=1
  ERROR: THIS MIGRATION-ONLY ASSERTION SHOULD NOT HAVE BEEN SELECTED
```

Per r5 M1 (`:732`), MIGRATION-ONLY assertions *"diverge permanently"* after any write — so once real
data exists, gate 8 is permanently red for a reason that has nothing to do with the schema.

**Fix:** require the marker to be the *whole* comment (`^\s*--\s*@RE-RUNNABLE\s*$`), and have the
harness refuse when the first marker in the file is not preceded by an assertion — or drop the legend
from Task 8 Step 1 and give the markers a non-comment sigil.

*(⟳ Convergence note: the sibling defect — a `@RE-RUNNABLE` block containing only comments reporting
"subset passed" over zero assertions — I measured independently at `2649094` (`exit=0`), Codex
reported it in the same round, and the coordinator's `5d5f1ed` fold closes it. I re-ran it: **exit=2
now, correctly**. Not counted as an open finding. Same for `strip_comments`' inverted bound —
`:76-78`'s claim that "an over-eager cut can only make an assertion stricter, never blind it" is
backwards, since every check in `assert_end_state` but two is a presence-of-bad-string test; Codex
found it and it is fixed.)*

### M2 — "`0021` shares the canonicalization" is false, and it is load-bearing twice.

The plan defers the `corrections_hash_of` / `no_corrections_hash` decision on this premise, at
`:279` and again at `:948`:

> deleting them is a separate decision with its own blast radius (`0021` shares the canonicalization)

A **search**, not a read: `grep -rn "corrections_hash_of\|no_corrections_hash" supabase/migrations/`
→ **0 hits**. `grep -n "digest\|sha\|hash\|canonical\|md5" supabase/migrations/0021_cloud_sync_signals.sql`
→ **0 hits**. `grep -rln "digest(" supabase/migrations/` → **nothing**. 0021 handles `corrections` as
a field in `videos.data`'s allowlist (`:24-25`, `:67`); it performs no hashing at all, and no
migration in the repo does.

So the two functions have **no blast radius outside M4** — which makes the open question at `:948`
much cheaper to close than the plan believes. The plan's own Task 1 ⚠ (`:71-81`) already re-measured
and corrected the sibling claim in this same paragraph; this half went unmeasured.

### M3 — the plan's highest-blast-radius risk is the only one with no mechanical guard.

*"A rollback filed as `0028` … composes to a NO-OP: production receives an empty milestone"* is
stated in bold in three places (`:594-599`, `:670-671`, and the rollback file's own `:12-16`).
It is defended entirely by prose. MEASURED: `grep -rn "supabase/rollback"` across `*.ts *.sh *.py
*.toml *.json *.yml` outside `docs/` → **0 hits**. Nothing in `check-schema-gates.sh` or `scripts/`
asserts it.

Every *lesser* risk in this milestone got a ratchet — `05_assert.sql` promotion got two. This one is
a one-liner in the same gate list Task 7 Step 3 already edits, e.g.
`! ls supabase/migrations/ | grep -qi rollback`, or better, a check that no migration file contains
`drop table if exists workspaces`. Per `dev-process.md`: *"Before adding a rule here, ask whether it
can be a script."*

### M4 — step numbering is broken in three of ten tasks, and this plan is executed step-by-step against checkboxes.

- **Task 2** has two `Step 5` — `:269` ("Prove no site was missed") and `:281` ("Commit").
- **Task 3** declares `### ✅ STEPS 1–6 ARE DONE` (`:302`) and then gives a **to-do** `Step 6` (`:323`).
- **Task 8** jumps `Step 1` (`:730`) → `Step 4` (`:792`); Steps 2 and 3 do not exist (extraction residue).

With `subagent-driven-development` as the Phase 3 default, "do Task 2 Step 5" is ambiguous and "Task 3
Step 6 is done" is contradicted by the same task.

---

## Low

- **L1 — the "148 lines" claim does not reproduce.** MEASURED by parsing the fences: **48 blocks,
  155 body lines** (142 excluding the 4 non-code output transcripts at `:587`, `:614`, `:754`,
  `:918`). Neither number is 148. Note also the **block count is unchanged** from round 2's "48
  blocks, 336 lines" — only line count fell, so "embedded code is down" is true of volume and not of
  surface area. Each block is still a place unexecuted code can hide, and H3 is one.
- **L2 — `schema_paths = []` is not the mechanism the claim needs.** `:605` reasons from it, but
  `schema_paths` (`config.toml:64`) governs *declarative schema* files for `db diff`; migration
  discovery is `supabase/migrations/` by convention and is not configurable there. The **conclusion**
  is correct — I verified `sql_paths = ["./seed.sql"]` (`:71`, no glob) and zero repo references —
  but the stated reason would survive someone changing an unrelated setting, and a load-bearing
  negative deserves the real mechanism.
- **L3 — mutation 2's evidence line overstates.** `mutate-live-schema-check.sh:85-87` prints
  "surviving live-table triggers, for the record" without filtering to M4's; my run listed **9**, of
  which `profiles_is_anonymous_immutable` and `trg_videos_updated_at` predate M4. The gate itself
  intersects correctly — only the harness's printed evidence is wrong, and evidence is what gets
  pasted into commit messages.

---

## What remains unexecuted (mandate item 7)

48 fenced blocks / 155 lines. Classified:

| Category | Blocks | Can it fail the way r1/r2's code failed? |
|---|---|---|
| Already executed as extracted artifacts (Tasks 3, 6 Step 3, 8) | ~12 | No — they are files now, and I ran them |
| Shell one-liners: `grep -c`, `git add`, `git commit -F` | ~22 | Low risk; no state, immediate failure |
| **Task 4 Steps 1–2 — the gate rewrites** (`:391-399`, `:407-414`) | **2** | **YES — H3 is exactly that, measured** |
| **Task 3 Step 7 — the `M4_PHASE` block** (`:348-362`) | **1** | **YES — H2; the branch has never been run inside `check-schema-gates.sh`** |
| Task 7 Step 3 / Task 8 Step 5 — the two new `run` lines | 2 | Untested against a real suite invocation; coupled to H2 |
| Task 9 Steps 1, 6, 7 — production commands | 3 | Cannot be executed here; correctly flagged NOT VERIFIED at `:950-954` |
| SQL edit fragments (Tasks 1–2) | 5 | Covered by `build-m4-schema.py` — **except the two column deletions, which is B1** |

**The 13-line `M4_PHASE` block and the two Task 4 snippets are the residue that matters.** They are
the only remaining blocks that are *logic* rather than *invocation*, and both carry a live defect.

---

## Hygiene

- Scratch databases `r3rev_probe`, `r3rev_probe2` created and **dropped**; the harness's
  `m4_gate_mutation_probe{,_raw}` dropped. Final `pg_database`: `_supabase`, `postgres`,
  `storage_vectors` — as before.
- The shared stack was never mutated: `check-live-schema.py --expect-absent` → **exit 0** after all
  work; `supabase_migrations.schema_migrations` → **26 rows**, unchanged. `verify-schema.sh` was run
  once, which is its designed rolled-back transaction.
- All scratch artifacts written outside the repo. **The only repo file I created is this review.**
  `git status --porcelain` is otherwise clean at `5d5f1ed`.

---

## Verdict

**Counts:** 3 Blocking · 3 High · 4 Medium · 3 Low.
*(Two further defects I measured independently — the comment-only `@RE-RUNNABLE` fail-open and
`strip_comments`' inverted bound — were found by the Codex half in the same round and closed by
`5d5f1ed` before I finished. They are recorded above, not counted.)*

**The round-2 decision was right and it worked.** Extraction did what it was supposed to: every
executed artifact holds, and every measured claim in the plan reproduces — the 161-object inventory
to the object, the rollback to the statement, the three self-tests to the case. That is a genuinely
strong result and it should be said plainly.

**But the extraction moved the defects rather than removing them.** All three Blockings live in the
seam between artifacts, where nothing executes:

- **B1** — the builder's verdict does not check what its docstring says it checks.
- **B2** — the gate designated to confirm production sees 18% of what it confirms.
- **B3** — the rollback reverses the schema and not the ledger, so the plan's own re-apply step is a no-op.

Each is the same shape as the shape this milestone keeps producing, and the one the architecture
review named: *individually correct components whose composition is not*. Round 2's finding was
"the code has never run." Round 3's is **"the code runs, and the claims about what it covers are
wider than the code."** B2 is the clearest instance and the most dangerous, because it is the
instrument the human gate at M4-β will read.

## NOT CONVERGED
