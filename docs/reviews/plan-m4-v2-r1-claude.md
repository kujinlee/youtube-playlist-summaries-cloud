# Plan M4 v2 — Round 1, CLAUDE half

**Subject:** `docs/superpowers/plans/2026-08-25-m4-promote-the-schema-v2.md` (10 tasks, 55 steps)
**Branch:** `docs/m4-plan` @ `7faade5` · **Reviewer:** Claude (independent of the Codex half)
**Method:** every read-only command in the plan was EXECUTED against the live local stack
(`supabase_db_youtube-playlist-summaries-cloud`, PostgreSQL 17.6). Task 1 + Task 2 + Task 6's `0028`
were attempted on a COPY in `begin; … rollback;`. **No repo-tracked file was modified and the shared
stack was verified untouched afterwards** (`workspaces_exists=0`, `probe_user_rows=0`).

ADR-0006/0007/0011 are not re-litigated. Every finding below is about whether the plan *implements*
ADR-0011, not whether ADR-0011 is right.

---

## Blocking

### B1 — `0028` does not run. It fails on its own first statement, and then again. MEASURED twice.

Task 6 Step 3 prints `0028` and asserts, at `plan:494`:

> *"round 5 measured that the drop order is expressible without `cascade` on the first attempt,
> which is the property to preserve."*

Executed verbatim, after building 01+03+04 in the same transaction:

```
---BUILD_OK---
ERROR:  cannot drop view video_artifacts_current because other objects depend on it
DETAIL:  view video_generations_collectable depends on view video_artifacts_current
HINT:  Use DROP ... CASCADE to drop the dependent objects too.
```

`video_generations_collectable` `[04_artifacts.sql:918]` selects from `video_artifacts_current`
`[04:728]`, and the plan drops the **dependency before the dependent**. Reordering those two lines
and re-running produces a *second*, independent failure:

```
ERROR:  cannot drop column workspace_id of table playlists because other objects depend on it
DETAIL:  trigger playlists_resolve_workspace_upd_trg on table playlists depends on column workspace_id
```

`playlists_resolve_workspace_upd_trg` is `before update of owner_id, workspace_id on playlists`
`[03_generations.sql:201-203]`; the same shape recurs at `videos` `[03:207-209]` and `jobs`
`[03:213-215]`. A column-list trigger is a hard dependency on the column.

A working order exists — I measured one: **drop the 7 live-table triggers first**, then
`video_generations_collectable` → `video_artifacts_current` → `video_summary_current`, then the
tables, then the columns. That run reached `---DROP_OK---` with no `cascade`. But it is not the order
in the plan, and the plan states the untrue version as a measured property to *preserve*.

The `⚠` at `:494` ("the list above is the shape … enumerate every view, trigger and function") does
not rescue this: the sentence immediately after it makes a **positive factual claim** about the
printed list that is false. A hedge and an assertion in the same paragraph is not a hedge.

---

### B2 — ⭐ `0028` leaves the schema in a state where signup and every enqueue are dead, and `check-live-schema.py --expect-absent` returns PASS on exactly that database.

This is the most important finding in the review, and it is the two defects above *combined with*
the gate designed to catch them.

**Enumeration of what `0027` creates** (`grep -nE "^create (table|view|type|function|trigger|index|policy)"`
across `01/03/04`, post-ADR-0011), against the plan's drop list at `:479-490`:

| Object class | Created by 0027 | Dropped by 0028 |
|---|---|---|
| Tables | 5 | **5** ✅ |
| Views | 3 | 3 ✅ (wrong order — B1) |
| Columns | 3 | 3 ✅ (needs trigger drops first — B1) |
| **Triggers on LIVE tables** (`profiles`, `playlists`, `videos`, `jobs`) | **7** | **0** ❌ |
| **Functions** | **13** | **0** ❌ |
| **Enum type** `artifact_kind` `[03:264]` | 1 | **0** ❌ |

Measured residue after a `0028` that completes (trigger drops added):

```
RESIDUE-FUNCTION: art_summary_has_no_source, corrections_hash_of, ensure_workspace_for_profile,
  forbid_collecting_current, no_corrections_hash, record_artifact, resolve_workspace_from_playlist,
  slot_kind, video_artifact_sources_append_only, video_artifact_sources_insert_once,
  video_artifacts_append_only, video_artifacts_generation_complete, video_generations_freeze
RESIDUE-TYPE: artifact_kind
```

**Now the outage.** Postgres' own `HINT` on both B1 errors says *"Use DROP ... CASCADE"*. That is the
fix an implementer reaches for. `cascade` removes only the three **column-list** (`_upd_`) triggers;
the four `before insert` triggers have no column dependency and survive. Measured:

```
NOTICE:  drop cascades to trigger playlists_resolve_workspace_upd_trg on table playlists
NOTICE:  drop cascades to trigger videos_resolve_workspace_upd_trg on table videos
NOTICE:  drop cascades to trigger jobs_resolve_workspace_upd_trg on table jobs
---DROP_COMPLETED---
SURVIVING-TRIGGER: jobs_resolve_workspace_ins_trg on jobs
SURVIVING-TRIGGER: playlists_resolve_workspace_ins_trg on playlists
SURVIVING-TRIGGER: profiles_ensure_workspace_trg on profiles
SURVIVING-TRIGGER: videos_corrections_sync_ins_trg on videos
SURVIVING-TRIGGER: videos_corrections_sync_upd_trg on videos
SURVIVING-TRIGGER: videos_resolve_workspace_ins_trg on videos
```

Then, on that database, a real signup:

```
ERROR:  relation "public.workspaces" does not exist
QUERY:  insert into public.workspaces (id, owner_id) values (new.id, new.id) on conflict (owner_id) do nothing
CONTEXT: PL/pgSQL function public.ensure_workspace_for_profile() line 6 at SQL statement
  SQL statement "insert into public.profiles (id, is_anonymous) values (new.id, ...)"
  PL/pgSQL function public.handle_new_user() line 3 at SQL statement
```

**No user can sign up.** `playlists_resolve_workspace_ins_trg` and `jobs_resolve_workspace_ins_trg`
break playlist creation and every enqueue the same way (`resolve_workspace_from_playlist()` reads
`public.workspaces` `[03:162]` and `playlists.workspace_id` `[03:168]`, both gone).

**And here is the layer the plan is silent about.** In the same transaction, what
`check-live-schema.py` reads:

```
TABLES_FOUND: (none)
COLUMNS_FOUND: (none)
```

`verdict(set(), set(), "absent")` → `not tables and not columns` → **True** → **exit 0**.

Task 6 Step 5 `[plan:513]` designates precisely this as the proof:

> *"⚠ **This, not "the schema gates go red", is the observation that proves removal.**"*

It proves nothing of the kind. `M4_TABLES` and `M4_COLUMNS` `[plan:263-265]` cover 5 tables and 3
columns; the gate has **no query for triggers, functions or types**, which is the entire residue.
The rollback's own falsifier is structurally blind to the rollback's actual failure mode — a gate
that reads the wrong subject, which `CLAUDE.md` names as *"an assertion in better packaging, and more
dangerous than prose, because nobody re-examines it."*

Note the shape: this is **not** the tables being wrong. The plan is *correct about every object it
names* and silent about the layer — triggers and functions on live tables — that decides whether the
database still works. That is the dominant defect shape already recorded for this workstream.

---

### B3 — ADR-0011 is implemented at two of three sites. `05_assert.sql` has 31 `corrections_hash` references and **no task touches them.**

Mandate item B. Search across the whole schema dir:

```
$ for f in .../schema/*.sql; do echo "$(basename $f): $(grep -c corrections $f)"; done
01_workspaces.sql: 0
03_generations.sql: 50
04_artifacts.sql: 6
05_assert.sql: 52
```

Task 1's **Files** list is `03_generations.sql` only `[plan:57]`. Task 2's is `04_artifacts.sql` only
`[plan:139]`. Task 8 modifies `05_assert.sql` **"(classification comments only)"** `[plan:571]`.
**Nothing in the plan edits `05_assert.sql`'s corrections content.**

Seven of those are hard references to the column Task 1 deletes:

```
05_assert.sql:62   select count(*) into n_null from workspace_videos where corrections_hash is null;
05_assert.sql:65   select count(*) into n_corr_wv from workspace_videos where corrections_hash <> no_corrections_hash();
05_assert.sql:119  insert into workspace_videos (workspace_id, video_id, corrections_hash)
05_assert.sql:820  update workspace_videos set corrections_hash='H_TYPED_JUST_NOW'
05_assert.sql:899  select wv.corrections_hash, wv.corrections into h, c
05_assert.sql:910  select wv.corrections_hash into h
05_assert.sql:917  select assert_raises($$insert into workspace_videos (workspace_id, video_id, corrections_hash) …, '23502');
```

Consequences the plan does not address:

1. `:899-912` assert the behaviour of `sync_corrections_to_workspace_video()` — **the function Task 1
   Step 5 deletes.** `:917-919` asserts the `NOT NULL` on a **dropped column**. These are not
   `@MIGRATION-ONLY` and not `@RE-RUNNABLE`; they are **obsolete**, and Task 8 Step 1 offers only two
   categories `[plan:585-586]`. An implementer has no instruction covering them.
2. Task 8's harness runs the `@RE-RUNNABLE` subset **against the live applied schema** `[plan:628-632]`.
   Any of these tagged re-runnable raises `column "corrections_hash" does not exist`.
3. `:62-65` is the backfill assertion, whose own precondition the plan quotes at `[plan:582]` — it
   asserts the corrections backfill that ADR-0011 deletes.

**The plan's own completeness check would have caught this, and its stated expectation is wrong.**
Task 2 Step 4 `[plan:180-184]`:

```bash
grep -rn "corrections_hash" docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema/
```
> *Expected: only the two **function definitions** in `03` … no column reference anywhere.*

Run verbatim: **51 hits**, 31 of them in `05_assert.sql`, seven of them column references. The step
written to prevent "a claim fixed at one of two sites" states an expected output that is off by an
order of magnitude, so an implementer comparing output to expectation sees a mismatch with no
instruction for what to do about it.

---

### B4 — Task 1's line citations are invalidated by Task 1's own earlier steps. Step 3 edits the wrong seven lines; Step 4 leaves a duplicate clause.

Mandate item A. The plan cites `03_generations.sql:52,61,89-95,183-185,227-236,253-262` `[plan:57]`
and issues them as **sequential steps** with no instruction to re-locate between edits.

*Which citations are correct against the pristine file:* `:52` ✅, `:61` ✅, `:89-95` ✅ (the backfill),
`:227-236` ✅ (function + `revoke`), `:253-262` ✅ (both triggers). `:183-185` ✗ — see below.

**Step 2 changes the file's length before any of them is used.** It deletes lines 52 and 61 (−2) and
inserts a 4-line ADR-0011 comment above `create table workspace_videos` at :48 (+4) `[plan:73-80]`.
Net **+2**. Simulating exactly that, the file's lines 89-95 then read:

```
  89: -- by "has corrections first" makes the pick deterministic and biased toward keeping content — a
  90: -- corrected row never loses to an uncorrected duplicate.
  91: insert into workspace_videos (workspace_id, video_id, corrections, corrections_hash)
  92:   select distinct on (workspace_id, video_id)
  93:          workspace_id, video_id,
  94:          nullif(data->>'corrections', ''),
  95:          corrections_hash_of(data->>'corrections')
```

Step 3 says *"Replace lines 89-95"* `[plan:84]`. Applied literally it consumes two comment lines and
**stops one line short of the statement**, leaving the original `from videos` and `order by …` behind:

```sql
insert into workspace_videos (workspace_id, video_id)
  select distinct workspace_id, video_id from videos;
   from videos
   order by workspace_id, video_id, (coalesce(data->>'corrections','') <> '') desc;
```

A syntax error, not a visible mistake. The cascade continues: Step 3 replaces 7 lines with 2 (−5),
so cumulative drift at Step 4 is **−3**, and *"Replace lines 183-185"* lands on the original 186-188
(`on conflict …` / `end if;` / `return new;`).

**Independently, `:183-185` is a mis-citation even against the pristine file.** The statement is
183-**186**:

```
183:    insert into public.workspace_videos (workspace_id, video_id, corrections, corrections_hash)
184:    values (v_ws, new.video_id, nullif(new.data->>'corrections', ''),
185:            public.corrections_hash_of(new.data->>'corrections'))
186:    on conflict (workspace_id, video_id) do nothing;
```

The plan's replacement block `[plan:98-101]` **already ends with** `on conflict (workspace_id,
video_id) do nothing;`. Replacing 183-185 therefore yields the clause twice — a syntax error even
with zero line drift.

Every `file:line` in the plan shares this property, but Task 1 is the only task that issues six
ordered edits to one file, so it is the only one where the drift is guaranteed rather than possible.

---

### B5 — Task 8's assertion selector selects **nothing** today, exits 0, and prints "passed". It is a fail-open gate.

Mandate item E. Run against `05_assert.sql` as it exists:

```
$ awk '/@RE-RUNNABLE/{p=1} p' .../05_assert.sql | wc -l
0
$ grep -c "@RE-RUNNABLE" .../05_assert.sql
0
```

Trace the harness `[plan:628-637]` with that empty result: `SQL` = seed corpus +
*nothing* + `\echo ASSERTIONS_OK\nrollback;`. psql prints `ASSERTIONS_OK`, `grep -q ASSERTIONS_OK`
succeeds, and the script echoes **"schema assertions: RE-RUNNABLE subset passed against the live
schema"** and exits **0**.

The markers are created in **Step 1** and the harness in **Step 3** — different steps, no ordering
guard, and the plan wires this in as gate `8/8` `[plan:664]`. A partial or forgotten Step 1 yields a
permanently green gate that runs zero assertions. That is the exact failure `CLAUDE.md` forbids:
*"'Cannot run' is a FAILURE, never a pass."* Here it is worse than cannot-run — it is
**did-not-run-and-said-pass**.

**And once the markers exist, the selector is still wrong.** `p=1` is a latch with **no reset**:
`awk` emits everything from the **first** `@RE-RUNNABLE` marker to EOF, including every
`@MIGRATION-ONLY` block that follows it. The selection is not "the RE-RUNNABLE subset"; it is "the
tail of the file". With `05_assert.sql` structured as interleaved `do $$ … $$;` blocks, that tail
includes `delete from profiles where id = p;` `[:2207]` — the statement the plan's own ⛔ at
`[plan:615]` cites as the reason this file must never be a migration. It is inside the rollback, so
it is contained; the claim printed by the harness is nonetheless false.

A correct selector needs a reset (`/@MIGRATION-ONLY/{p=0}`) **and** block-boundary awareness, since
cutting at a marker can slice a `do $$ … $$` block in half. Neither is specified.

---

### B6 — After Task 6, `check-schema-gates.sh` can never be green. Task 9 Step 3's expectation is unsatisfiable.

Mandate item F. `scripts/check-schema-gates.sh:26` — `run()` treats **any** non-zero as failure:

```bash
if "$@"; then :; else echo "❌ FAILED: $*"; fail=1; fi
```

The plan's own docstring `[plan:252-254]` states the premise:

> *"Measured 2026-08-25: with 0027 applied, re-running that DDL fails with `relation "workspaces"
> already exists`, so those gates go RED on a correctly-migrated database."*

Task 4 Step 2's remedy `[plan:349-355]` is to make gate 1 **`exit 2`** on an applied database. `run()`
scores `exit 2` as FAILED, so `check-schema-gates.sh` exits 1. Task 6 Step 6 deliberately leaves the
stack migrated `[plan:518]`. Task 9 Step 3 then requires `./scripts/check-schema-gates.sh` →
*"9 checks, 0-8"* all green `[plan:704]`, and the milestone gate list repeats it `[plan:770]`.

Gate 2 is worse: **nothing in the plan gives `mutate-schema.py` a cannot-run branch at all.** It
rebuilds the schema against the live DB inside a rollback (`mutate-schema.py:875-884` copies
`verify-schema.sh` into temp and re-runs it per mutation), so on a migrated stack every one of its
~44 mutations fails at `create table workspaces` — before reaching the mutated guard. A mutation
"caught" for the wrong reason reports GREEN, which is `mutation-harness-needs-a-verdict-per-mechanism`
exactly.

Task 4 Step 1's migration-if-present branch does not help: reading `0027` and executing it in a
rollback against a DB where `0027` is applied still raises `already exists`.

The contradiction is structural, not a wording slip: **the plan requires the stack migrated and
requires gates that only pass on an unmigrated stack.** Either the gate list drops 1 and 2 after
Task 6 with that stated, or `run()` learns to distinguish `2` from `1`, or the gates get a
throwaway database. The plan picks none.

---

## High

- **H1 — `check-live-schema.py`'s `TABLE_SQL` is not runnable.** `[plan:267-268]` uses
  `c.relname = any(%s)` — psycopg paramstyle — in a module whose only imports are
  `argparse, subprocess, sys` `[plan:260]` and whose transport is `docker exec … psql`
  `[plan:262]`. Measured: `ERROR: syntax error at or near "%"`. Task 3 Step 5 ("run it against the
  real, pre-M4 stack, expect exit 0") cannot pass. Note `COLUMN_SQL` `[:269-271]` has no placeholder
  and is fine — so a hasty fix at one site leaves the other.

- **H2 — Task 3 Step 6's red-proof cannot fire; it uses two connections.** `[plan:293-300]` creates
  `public.workspaces` inside a heredoc `psql` session, then says *"in the same session run
  `--expect-absent`"*. The heredoc closes stdin, psql exits, the transaction rolls back — and
  `check-live-schema.py` is a separate `docker exec`. Measured:
  `created_in_session_1=1` then `visible_in_session_2=0`. The step expects exit 1 and will get exit
  0, i.e. **the mutation proof reports the gate cannot go red.** The likely "fix" is to `commit`,
  which mutates the shared stack — the failure the step's own ⚠ warns against.

- **H3 — Task 8's seed corpus fails on two counts.** Run verbatim `[plan:598-603]`:
  ```
  ERROR: insert or update on table "profiles" violates foreign key constraint "profiles_id_fkey"
  DETAIL: Key (id)=(00000000-...-a1) is not present in table "users".
  ```
  `profiles_id_fkey -> auth.users`. The seed must create an `auth.users` row first (or go through
  `handle_new_user()`). Separately, `playlists.playlist_url` is `NOT NULL` with **no default** and
  the seed omits it. The plan's ⚠ at `[plan:606]` covers only the second ("column lists must be
  verified against `0001_core_schema.sql`") — the FK is not a column-list problem and is not visible
  in that file's column list.

- **H4 — `verify-schema.sh`'s new branch uses an undefined variable under `set -u`.** Task 4 Step 2
  `[plan:350]` calls `python3 "$REPO/scripts/check-live-schema.py"`. `verify-schema.sh` defines only
  `DIR` `[:8]` and `CONTAINER` `[:9]`, under `set -uo pipefail` `[:7]`. `$REPO` → *unbound variable*
  → the gate dies before it runs. (Step 1's `$(cd "$(dirname "$0")/../../../.." && pwd)` **is**
  correct — four levels from the spec dir is the repo root. Verified.)

- **H5 — The plan's very first command states a wrong expectation.** Task 1 Step 1 `[plan:67]`:
  `grep -c "corrections" 03_generations.sql # expect 20`. Actual: **50**. (`grep -c` counts matching
  lines.) The sibling on the next line — `grep -c "^create trigger"` → **10** — is correct, as are
  Task 2 Step 1's two `mdCorrectionsHash` hits at exactly `717` and `777`. So the file is right and
  the number is invented. Step 6's follow-up `# expect 8 (was 10)` is consistent and correct.
  A plan whose opening measurement is wrong trains the implementer to skip the measurements.

- **H6 — Task 2 Step 4's expected output is wrong by 25×** — see **B3**. Filed separately because
  the fix differs: B3 needs new work in `05_assert.sql`; H6 needs the expectation corrected so the
  step can discriminate.

---

## Medium

- **M1 — `check-live-schema.py` is under-specified for the question it names.** Its docstring
  `[plan:243]` asks *"Does the DEPLOYED schema match what M4 claims"*, but it inspects 5 tables and
  3 columns — not the 3 views, 13 functions, 7 live-table triggers, 1 enum, the RLS policies or the
  grants. `--expect-present` passes on a database where `0027`'s tables exist and **every trigger is
  missing**, which is the failure mode that matters (ingest breaks silently — `03:99-140` documents
  exactly that class). `verdict()` itself is sound for what it is given; the hole is the **input
  set**, and the self-test cannot see it because the self-test feeds `verdict()` the same impoverished
  vocabulary. The five self-test cases `[plan:221-229]` do test what they claim about `verdict()`.

- **M2 — Task 1 leaves ~30 lines of comments describing deleted objects.** The ranges omit the
  comment blocks that explain them: `03:82-88` (*"THE SEED CARRIES THE CORRECTIONS … `distinct on`
  rather than `distinct`"*) survives Step 3 while Step 3 changes it to `distinct`; `03:181`
  (*"the second insert must not clobber the first's corrections"*) survives Step 4; `03:217-226`
  (the ROUND 6 B4 denormalized-copy block) and `03:237-252` (the two-triggers rationale) both sit
  **outside** the `227-236` and `253-262` ranges. Step 5 says *"including their explanatory
  comments"* `[plan:105]` but the cited ranges do not contain them. `check-sentinel-meanings.py`'s
  dead docstring is fixed by Task 5 Step 3 — the same defect inside the schema is not.

- **M3 — Gate numbering never reconciles.** `check-schema-gates.sh` labels six checks `1/6`…`6/6`
  `[:30-46]`. Task 3 adds `7/8` `[plan:307]`, Task 8 adds `8/8` `[plan:664]`, Task 7 adds `0/8`
  `[plan:553]`. No step renumbers `1/6`→`1/8`, so the output reads `1/6 … 6/6, 7/8, 8/8, 0/8` while
  the milestone gate claims *"nine checks, numbered 0-8"* `[plan:770]`. Also `0/8` is appended last,
  so the check numbered zero runs ninth. Cosmetic alone, but it is the arithmetic the gate list
  asserts.

- **M4 — Task 4 Step 4 is one sentence for a rewrite the plan itself calls a rewrite.**
  *"Replace the hardwired file list at `:25-27`"* `[plan:365]`. Those lines are
  `SPEC`/`GEN`/`ART` `[mutate-schema.py:25-27]`, and `GEN`/`ART` are the **keys** of the `MUTATIONS`
  table's `target` field and of `copy_of` `[:884]` and `originals` `[:886]`. Collapsing two sources
  into one migration file invalidates every entry. Worse, `mutate-schema.py` copies the spec dir and
  `verify-schema.sh` into a temp dir and runs from there `[:879-883]`, so Step 1's
  `$(dirname "$0")/../../../..` resolves to `/` — the migration is never found and the gate
  **silently keeps reading the spec files**, which is a gate that reports success about the wrong
  subject. Neither the copy list nor the `MUTATIONS` retarget is specified.

- **M5 — Task 5 Step 4's "expect all `0`" is asserted, not established.** The plan states gate 3 is
  RED today `[plan:395]` and Step 2 asks for *"entries for every constraint and trigger on
  `video_artifact_sources`, each classified `SHAPE` or `SEQUENCE`"* `[plan:407]` — but
  `check-guard-coverage.py` also requires every SEQUENCE guard to *reconcile and be mutated*
  (`dev-process.md`). Adding inventory entries without the matching mutations moves the gate from
  "RED, wrong inventory" to "RED, missing mutations". No step adds mutations.

---

## Low

- **L1 — Task 7's `05_assert` guard is green today.** Verified:
  `grep -lE "execute p_sql|delete from profiles" supabase/migrations/*.sql` → no matches. The guard
  is well-formed (`!` inverts `grep`'s exit 1 correctly, and `check-schema-gates.sh:18` `cd`s to the
  repo root so the glob resolves). Noted only because it is the one new gate that does what it says.

- **L2 — `t1-blast-radius.sql` exists.** `docs/superpowers/specs/m4/t1-blast-radius.sql` is present,
  so Task 9 Step 1 `[plan:688]` is not a dangling reference. `MONEY_TABLES` exists at
  `scripts/check-anon-exposure.py:68`, so Task 9 Step 4 is actionable. Both checked because the plan
  references them without creating them.

---

## What the plan gets right (so a revision does not lose it)

- `01/03/04` **do** execute against a live stack — `---BUILD_OK---` reached on every run above.
- The ADR-0011 edits to `03` and `04` are the right edits; the diagnosis at `[plan:158-165]` and
  ADR-0011's "comparison belongs to the reader" are sound and are not in question.
- Task 6's ⛔ about `0027`'s existence arming `global-setup.ts` `[plan:18]`, and the refusal to split
  `0027` `[plan:443]`, are correct and load-bearing.
- Task 3's **premise** — five gates rebuild from source and cannot answer "did it apply?" — is
  correct and is the right new axis. The instrument is what falls short (M1, H1).
- The `--expect-absent` polarity at Task 6 Step 5 is the right *direction* (v5 had it backwards); it
  is the gate's blindness (B2), not its polarity, that fails.

---

## IS THIS PLAN EXECUTABLE AS WRITTEN?

**No.**

A competent engineer with no context cannot follow it end to end. The failures are not judgement
calls they could route around:

- **Task 1 Step 1** reports 50 against an expected 20 on the first command (H5).
- **Task 1 Steps 3 and 4** produce SQL that does not parse if the line numbers are followed (B4).
- **Task 2 Step 4** reports 51 hits against an expected 2, with no instruction for the mismatch (H6),
  and the work that mismatch reveals — `05_assert.sql` — has no task (B3).
- **Task 3 Step 5** cannot pass, because the SQL is not valid psql (H1); **Step 6** cannot fail,
  because it uses two connections (H2).
- **Task 4 Step 2** dies on an unbound variable (H4).
- **Task 6 Step 3** errors on `0028`'s first statement (B1).
- **Task 8 Step 2** errors on a foreign key (H3); **Step 4** expects `0` from a harness that would
  print "passed" having executed nothing (B5).
- **Task 9 Step 3** requires a green gate run that the plan's own design makes unreachable (B6).

Nine of the ten tasks contain at least one step that halts or silently misreports. The design is
sound — ADR-0011 is the right decision and the plan's *shape* implements it — but the executable
layer has not been run. **Every one of these was found by executing the plan's own commands**, which
is the strongest available evidence that they were written rather than measured, in a plan whose
predecessor was abandoned for the same reason.

### The single most important finding

**B2.** B1 is a bug and B3, B4, B5, H1-H4 are bugs; they will be fixed in a round or two. B2 is a
*design* failure and it will survive those fixes unless it is named: `check-live-schema.py` is
appointed the falsifier for the rollback `[plan:513]` while being structurally incapable of seeing
the rollback's real failure — 7 triggers and 13 functions on live tables, pointing at objects that
no longer exist, with signup and every enqueue dead and the gate reporting **exit 0**. Fixing `0028`'s
drop list without widening the gate's subject leaves a repaired mechanism guarded by an instrument
that would not have caught the original, and the next omission from `0028` passes just as quietly.

**The gate must enumerate what `0027` creates, not a hand-written list of five tables** — derive the
inventory from the migration file or from `pg_depend`, so an object added to `0027` cannot be
forgotten by `0028` *and* by the gate at the same time.

---

## NOT VERIFIED

- `supabase db push --linked`'s one-transaction property (Task 9 Step 6) — not executed; no remote.
- `supabase migration down`'s reset behaviour `[plan:24]` — not executed.
- Production's ACLs / `--prod` anon exposure — no `CLAUDE_RO_DATABASE_URL` in this environment.
- The plan correctly lists all three under "Still NOT VERIFIED" `[plan:786-790]`.

## Cleanup

All work was done on copies in
`…/scratchpad/m4/`. Every DDL statement ran inside `begin; … rollback;`. Post-run verification of the
shared stack: `workspaces_exists=0`, `probe_user_rows=0` — the M4 schema is absent and the probe user
did not persist. No repo-tracked file was modified; `git status` was clean at start and no `Edit`/
`Write` touched the working tree except this review file.

---

**NOT CONVERGED**
