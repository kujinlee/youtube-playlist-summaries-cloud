# M4 — Promote the schema as migrations — Implementation Plan

> **Anchor:** `stable-blob-addressing` — **ADR:** 0006, 0007, 0011
> **Goal:** A blob's address stops moving when a title or a serial number changes. M4 is the step that makes the accepted schema EXECUTE, for the first time outside a review's rollback.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Promote `01_workspaces.sql`, `03_generations.sql` and `04_artifacts.sql` into a single reversible migration `0027`, applied first to a local stack and then to production, with a rollback and a behavioural gate that both actually run.

**Architecture:** One migration file, one transaction. The three spec files are concatenated in dependency order; `05_assert.sql` is never a migration. A companion `0028` reverses it. Correctness is established by six schema gates (rewritten to read a **live** catalog, not to rebuild from source), the integration suite, and a live-catalog assertion.

**Tech Stack:** PostgreSQL 15 (Supabase), Supabase CLI 2.115.0, Python 3 ratchets, Jest (`--runInBand`) for integration.

---

## ⛔ Read before touching anything

**1 — WRITING `supabase/migrations/0027_*.sql` IS M4-α.** `tests/integration/global-setup.ts:43-51` runs `npx supabase migration up` on **every** integration run and **throws rather than skip**. The moment that file exists on the branch, the next `npm run test:integration` on any machine applies all of M4 to that machine's stack. **That is why 0027 is created in Task 6, not Task 1** — everything that must be ready first is ready first.

**2 — M4 IS NOT INERT.** `01_workspaces.sql:36-48` adds `workspace_id` to `playlists`, `videos`, `jobs`, backfills every row and sets each `NOT NULL`. After ADR-0011 it attaches **SEVEN** triggers to live tables (was nine; the two corrections-sync triggers are deleted in Task 1).

**3 — `05_assert.sql` IS NEVER A MIGRATION.** It contains `delete from profiles where id = p;` `[05_assert.sql:2207]` and `execute p_sql;` — an unrevoked arbitrary-SQL executor `[:37]`. Task 8 gives it a home that is not `supabase/migrations/`.

**4 — THE ONE-TRANSACTION GUARANTEE BELONGS TO THE APPLY COMMAND, NOT THE SQL.** `psql -f` without `--single-transaction`, or a dashboard paste, does not have it. ⚠ `supabase migration down` **exists** but *resets* (drop-and-recreate) and accepts `--linked` — **it is not the rollback. Task 5 is.**

## What this plan supersedes

`docs/superpowers/plans/2026-08-25-m4-promote-the-schema.md` (v5.1) — five revisions, five non-converging review rounds, eleven Blocking/High findings. `docs/reviews/architecture-review-2026-08-25.md` established that nine of the eleven were one defect, and **ADR-0011 dissolves it**. Four findings (r3 H3, r4 M2, r5 B1, r5 B3) require no fix in this plan because the state they describe cannot occur.

**Carried forward, because they survive ADR-0011:** the gate repairs, the named apply command, the `0028` rollback, the `test:integration` gate, and the architecture review's finding 3.

## Global Constraints

- **Migration numbering starts at `0027`** — `0026_record_correction_spend.sql` is the highest taken.
- **`05_assert.sql` is never promoted.** Task 3's gate makes this mechanical rather than stated.
- **Any gate that cannot reach its subject exits non-zero saying "treat this as NOT RUN"** — never 0. (`CLAUDE.md`.)
- **Anything longer than a line goes in a file** — `git commit -F`, `--body-file`, `--prompt-file`. Backticks inside double-quoted bash *and* inside psql `\echo` are command substitution.
- **Merging is a human gate. Applying M4-β to production is a second human gate.**

## File Structure

| File | Responsibility |
|---|---|
| `docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema/03_generations.sql` | **Modify** — remove corrections per ADR-0011 (Task 1) |
| `…/schema/04_artifacts.sql` | **Modify** — corrections-currency ranking moves to the reader (Task 2) |
| `scripts/check-live-schema.py` | **Create** — the live-catalog gate; the only instrument that can confirm M4-β happened (Task 3) |
| `supabase/migrations/0027_stable_blob_addressing.sql` | **Create** — the three spec files, one transaction (Task 6) |
| `supabase/migrations/0028_rollback_stable_blob_addressing.sql` | **Create** — the reverse (Task 6) |
| `scripts/check-guard-coverage.py`, `check-sentinel-meanings.py`, `check-vocabulary-collisions.py` | **Modify** — inventories, after Task 1 removes objects (Task 5) |
| `docs/superpowers/specs/2026-08-03-stable-blob-addressing/verify-schema.sh`, `mutate-schema.py` | **Modify** — read the migration, not the spec dir (Task 4) |

---

## Task 1: Remove corrections from `workspace_videos` (ADR-0011)

**Files:**
- Modify: `docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema/03_generations.sql:52,61,89-95,183-185,227-236,253-262`

**Interfaces:**
- Consumes: nothing.
- Produces: a `workspace_videos` with columns `(workspace_id, video_id)` only; `corrections_hash_of(text)` and `no_corrections_hash()` **remain defined** (Task 2 keeps a caller); triggers on `videos` reduce from 4 to 2.

- [ ] **Step 1: Confirm the starting state, so the diff is a measurement not a hope**

```bash
cd docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema
grep -c "corrections" 03_generations.sql          # expect 20
grep -c "^create trigger" 03_generations.sql      # expect 10
```

- [ ] **Step 2: Drop the two columns**

In `03_generations.sql`, delete line 52 (`  corrections        text,`) and line 61 (`  corrections_hash   text not null default no_corrections_hash(),`). Add above the `create table workspace_videos`:

```sql
-- ⟳ ADR-0011 (2026-08-25) — CORRECTIONS ARE PER-PLAYLIST AND DO NOT LIVE HERE.
-- This table is workspace-scoped; `videos` is playlist-scoped (0001_core_schema.sql:30). Carrying
-- `corrections` here collapsed N playlist rows into 1 with no merge rule, and produced nine of the
-- eleven Blocking/High findings across five review rounds. The truth stays in `videos.data`.
```

- [ ] **Step 3: Simplify the backfill**

Replace lines 89-95 with:

```sql
insert into workspace_videos (workspace_id, video_id)
  select distinct workspace_id, video_id from videos;
```

⚠ `distinct`, not `distinct on` — there is no longer a column whose value depends on which row wins, so the ordering that used to pick a winner is gone with it.

- [ ] **Step 4: Simplify the derive trigger's upsert**

Replace lines 183-185 with:

```sql
    insert into public.workspace_videos (workspace_id, video_id)
    values (v_ws, new.video_id)
    on conflict (workspace_id, video_id) do nothing;
```

- [ ] **Step 5: Delete the sync function and its two triggers**

Delete `sync_corrections_to_workspace_video()` and its `revoke` (lines 227-236) and both `create trigger videos_corrections_sync_*` blocks (lines 253-262), including their explanatory comments.

- [ ] **Step 6: Verify the removal by counting, and that the file still parses**

```bash
grep -c "^create trigger" 03_generations.sql      # expect 8 (was 10)
docker exec -i supabase_db_youtube-playlist-summaries-cloud \
  psql -U postgres -d postgres -v ON_ERROR_STOP=1 <<'SQL'
begin;
\i /dev/stdin
SQL
```

If `\i` is awkward, use the gate's own method:

```bash
(printf 'begin;\n'; cat 01_workspaces.sql 03_generations.sql 04_artifacts.sql; printf 'rollback;\n') \
 | docker exec -i supabase_db_youtube-playlist-summaries-cloud psql -U postgres -d postgres -v ON_ERROR_STOP=1
```

Expected: no error. ⚠ It **will** error until Task 2 lands, because `04_artifacts.sql:717,777` still reference `wv.corrections_hash`. **That is the expected failure that proves Task 2 is required** — record the error text and continue to Task 2 rather than "fixing" it here.

- [ ] **Step 7: Commit**

```bash
git add docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema/03_generations.sql
git commit -F /tmp/t1-msg.txt   # subject: "feat(M4): ADR-0011 — corrections leave workspace_videos"
```

---

## Task 2: Move the corrections-currency comparison to the reader

**Files:**
- Modify: `docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema/04_artifacts.sql:717,777`

**Interfaces:**
- Consumes: Task 1's `workspace_videos` (no `corrections_hash`).
- Produces: `video_artifacts_current` and its sibling view rank **without** a corrections term. The card's `mdCorrectionsHash` key is unchanged and still written by producers.

- [ ] **Step 1: Read both sites before editing either**

```bash
grep -n "mdCorrectionsHash" docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema/04_artifacts.sql
```

Expected: exactly two hits, `717` and `777`. **If there are three, stop** — v5's `:120` residue was exactly this shape, a claim fixed at one of two sites.

- [ ] **Step 2: Remove the ranking term at both sites, with the reason in place**

At each site, delete the line `(g.card->>'mdCorrectionsHash' = wv.corrections_hash) desc,` and the round-6 B4 comment block above it, replacing with:

```sql
         -- ⟳ ADR-0011 — NO CORRECTIONS TERM. This ranked "prefer the generation whose card says it
         -- reflects the corrections currently in force", comparing an IMMUTABLE stamp inside a frozen
         -- generation against a MUTABLE denormalized copy — so a generation could keep claiming to
         -- reflect corrections that had since been overwritten, undetected.
         -- "Is this generation corrections-current?" is NOT a property of the generation. It is a
         -- RELATION between a generation and a VIEWER: one shared artifact seen from two playlists
         -- with different corrections has two answers at once. The card keeps its `mdCorrectionsHash`
         -- stamp (a fact); the COMPARISON belongs to the reader, who knows their playlist.
```

- [ ] **Step 3: Verify the whole schema now parses against a live stack**

```bash
cd docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema
(printf 'begin;\n'; cat 01_workspaces.sql 03_generations.sql 04_artifacts.sql; printf '\\echo ALL_OK\nrollback;\n') \
 | docker exec -i supabase_db_youtube-playlist-summaries-cloud psql -U postgres -d postgres -v ON_ERROR_STOP=1
```

Expected: `ALL_OK`, exit 0. This is the first point at which the post-ADR-0011 schema is known to execute.

- [ ] **Step 4: Prove no third site was missed**

```bash
grep -rn "corrections_hash" docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema/
```

Expected: only the two **function definitions** in `03` (`corrections_hash_of`, `no_corrections_hash`) — no column reference anywhere. ⚠ If those functions now have zero callers, **leave them defined and say so in the commit**; deleting them is a separate decision with its own blast radius (`0021` and the sync path reference the same canonicalization).

- [ ] **Step 5: Commit**

```bash
git add docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema/04_artifacts.sql
git commit -F /tmp/t2-msg.txt
```

---

## Task 3: `check-live-schema.py` — the gate that reads the deployed catalog

**Files:**
- Create: `scripts/check-live-schema.py`
- Modify: `scripts/check-schema-gates.sh` (add as gate 7/7)

**Interfaces:**
- Consumes: nothing from earlier tasks; runnable today.
- Produces: `check-live-schema.py --expect-absent | --expect-present`, exit 0 pass, 1 fail, 2 cannot-run.

**Why this exists (architecture review, finding 3):** five of the six existing gates never read a live database — they *rebuild* the schema from spec files inside a rolled-back transaction (`verify-schema.sh:10`, `check-guard-coverage.py:195-206`). So the suite asks *"is the SPEC consistent?"*, never *"does the DEPLOYED schema match it?"* — the wrong question for the one milestone whose purpose is making the spec execute. **This is a third axis after r3 B2's *path* and *transport*: the SUBJECT axis, built-from-source vs introspected-from-live.**

- [ ] **Step 1: Write the failing self-test**

Create `scripts/check-live-schema.py` with a `--self-test` that must fail first:

```python
def self_test() -> int:
    cases = failures = 0
    def check(label, got, want):
        nonlocal cases, failures
        cases += 1
        ok = got == want
        print(("  ✓ " if ok else "  ✗ ") + label)
        failures += 0 if ok else 1

    check("absent verdict when no objects", verdict(set(), set(), "absent"), True)
    check("absent verdict FAILS when a table survives",
          verdict({"workspaces"}, set(), "absent"), False)
    check("present verdict needs ALL five tables",
          verdict({"workspaces"}, set(), "present"), False)
    check("present verdict needs the columns too",
          verdict(set(M4_TABLES), set(), "present"), False)
    check("present verdict passes when complete",
          verdict(set(M4_TABLES), set(M4_COLUMNS), "present"), True)
    print(f"\n{cases - failures}/{cases} self-test cases passed")
    return 1 if failures else 0
```

- [ ] **Step 2: Run it and watch it fail**

Run: `python3 scripts/check-live-schema.py --self-test`
Expected: FAIL — `NameError: name 'verdict' is not defined`.

- [ ] **Step 3: Write the minimal implementation**

```python
#!/usr/bin/env python3
"""Does the DEPLOYED schema match what M4 claims — a RATCHET on the SUBJECT axis.

    python3 scripts/check-live-schema.py --expect-present   # after 0027
    python3 scripts/check-live-schema.py --expect-absent    # after 0028, or before M4
    python3 scripts/check-live-schema.py --self-test        # 5 cases

WHY THIS EXISTS. Five of the six schema gates REBUILD the schema from spec files inside their own
rolled-back transaction (verify-schema.sh:10, check-guard-coverage.py:195-206). They therefore
answer "is the spec internally consistent?" and CANNOT answer "did the migration actually apply?".
Measured 2026-08-25: with 0027 applied, re-running that DDL fails with `relation "workspaces"
already exists`, so those gates go RED on a correctly-migrated database. A plan that asserted the
opposite polarity shipped in v5 and was caught in round 5.

FAILS IF: --expect-present and any of the five tables or three columns is missing; --expect-absent
and any of them survives; or the database is unreachable (exit 2 — treat as NOT RUN).
"""
from __future__ import annotations
import argparse, subprocess, sys

CONTAINER = "supabase_db_youtube-playlist-summaries-cloud"
M4_TABLES = ("workspaces", "workspace_videos", "video_generations",
             "video_artifacts", "video_artifact_sources")
M4_COLUMNS = ("playlists.workspace_id", "videos.workspace_id", "jobs.workspace_id")

TABLE_SQL = ("select c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace "
             "where n.nspname='public' and c.relkind='r' and c.relname = any(%s);")
COLUMN_SQL = ("select table_name||'.'||column_name from information_schema.columns "
              "where table_schema='public' and column_name='workspace_id' "
              "and table_name in ('playlists','videos','jobs');")


def verdict(tables: set[str], columns: set[str], mode: str) -> bool:
    """PURE. True = pass."""
    if mode == "absent":
        return not tables and not columns
    return set(M4_TABLES) <= tables and set(M4_COLUMNS) <= columns
```

- [ ] **Step 4: Run the self-test to verify it passes**

Run: `python3 scripts/check-live-schema.py --self-test`
Expected: `5/5 self-test cases passed`, exit 0.

- [ ] **Step 5: Run it against the real, pre-M4 stack**

Run: `python3 scripts/check-live-schema.py --expect-absent`
Expected: exit 0 — M4 has not been applied, so its objects are absent. **This is the gate proving itself against the world before it is trusted about the world.**

- [ ] **Step 6: Prove it can go RED (mutation), inside a rolled-back transaction**

```bash
docker exec -i supabase_db_youtube-playlist-summaries-cloud psql -U postgres -d postgres -tAq <<'SQL'
begin;
create table public.workspaces (id uuid primary key);
SQL
```

Then in the same session run `--expect-absent` and expect **exit 1**. ⚠ Roll back and re-verify the stack is untouched — `an-instrument-that-edits-the-repo-corrupts-its-peers`.

- [ ] **Step 7: Wire it in as gate 7/7 and commit**

In `scripts/check-schema-gates.sh`, after line 46:

```bash
run "7/8  live catalog matches expectation"           python3 ./scripts/check-live-schema.py --expect-absent
```

```bash
git add scripts/check-live-schema.py scripts/check-schema-gates.sh
git commit -F /tmp/t3-msg.txt
```

---

## Task 4: Rewrite gates 1 and 2 to read the migration

**Files:**
- Modify: `docs/superpowers/specs/2026-08-03-stable-blob-addressing/verify-schema.sh:8-12`
- Modify: `docs/superpowers/specs/2026-08-03-stable-blob-addressing/mutate-schema.py:25-27,875-884`

**Interfaces:**
- Consumes: Task 3's live-catalog gate (for the "is it already applied?" branch).
- Produces: gates 1 and 2 reading `supabase/migrations/0027_*.sql` when it exists, falling back to the spec dir when it does not.

⚠ **This is a REWRITE, not a re-point** (r2, re-confirmed r3 B2). `verify-schema.sh` concatenates spec files inside one rollback transaction; `mutate-schema.py` hardwires two named spec files and copies the verifier into temp.

- [ ] **Step 1: Make the source a variable, not a constant**

In `verify-schema.sh`, replace line 10:

```bash
MIGRATION="$(cd "$(dirname "$0")/../../../.." && pwd)/supabase/migrations/0027_stable_blob_addressing.sql"
if [ -f "$MIGRATION" ]; then
  SRC=$(cat "$MIGRATION")
else
  SRC=$(cat "$DIR"/0[134]*.sql)      # pre-promotion: the spec files, 05 excluded
fi
SQL=$(printf 'begin;\n%s\n\\echo ALL_STATEMENTS_OK\nrollback;\n' "$SRC")
```

⚠ `0[134]*.sql` not `0*.sql` — the old glob included `05_assert.sql`, which is exactly the file that must never execute as schema.

- [ ] **Step 2: Add the already-applied branch**

Before running, ask the live-catalog gate whether 0027 is applied; if it is, this gate cannot rebuild and must say so rather than fail confusingly:

```bash
if python3 "$REPO/scripts/check-live-schema.py" --expect-present >/dev/null 2>&1; then
  echo "CANNOT RUN — 0027 is already applied to this database, so rebuilding it will fail with"
  echo "  'relation \"workspaces\" already exists'. This gate rebuilds from source by design."
  echo "  Use scripts/check-live-schema.py for an applied database. Treat this as NOT RUN."
  exit 2
fi
```

- [ ] **Step 3: Verify the fallback path still passes today**

Run: `./docs/superpowers/specs/2026-08-03-stable-blob-addressing/verify-schema.sh`
Expected: `ALL_STATEMENTS_OK`, exit 0 (0027 does not exist yet, so the spec-dir branch runs).

- [ ] **Step 4: Apply the same source-selection to `mutate-schema.py`**

Replace the hardwired file list at `:25-27` with the same "migration if present, else spec files" selection, and re-run:

Run: `python3 docs/superpowers/specs/2026-08-03-stable-blob-addressing/mutate-schema.py`
Expected: the mutation suite runs and every mutation is caught.

- [ ] **Step 5: Prove the rewrite is load-bearing — mutate one guard and confirm RED**

Delete one `check` constraint from the source the gate now reads, re-run gate 1, and confirm failure. **A gate that passes because it now reads an empty set is a measured failure mode of this repo, twice.**

- [ ] **Step 6: Commit**

```bash
git add docs/superpowers/specs/2026-08-03-stable-blob-addressing/verify-schema.sh \
        docs/superpowers/specs/2026-08-03-stable-blob-addressing/mutate-schema.py
git commit -F /tmp/t4-msg.txt
```

---

## Task 5: Repair the three ratchet inventories

**Files:**
- Modify: `scripts/check-guard-coverage.py:58,132`
- Modify: `scripts/check-sentinel-meanings.py:9,48`
- Modify: `scripts/check-vocabulary-collisions.py:49`

**Interfaces:**
- Consumes: Tasks 1–2 (the objects these inventories name are now gone).
- Produces: three ratchets whose inventories match the post-ADR-0011 schema.

⚠ **r3 B3 established gate 3 is RED against this schema even before ADR-0011** — it names `art_pending_is_leased`, `art_pending_has_token`, `art_pending_has_reserved_at`, all **verified absent** outside comments, and has **zero** entries for `video_artifact_sources`. **Repair the inventory first; re-pointing a stale one changes what it measures without saying so.**

- [ ] **Step 1: Establish which entries are stale, by running not reading**

```bash
python3 scripts/check-guard-coverage.py 2>&1 | tail -20
```

Record every name it reports as missing.

- [ ] **Step 2: Remove the three phantom guards and add `video_artifact_sources` coverage**

Delete the `art_pending_*` entries; add entries for every constraint and trigger on `video_artifact_sources`, each classified `SHAPE` or `SEQUENCE` per the file's own contract.

- [ ] **Step 3: Fix the sentinel docstring, which teaches with a dead example**

`check-sentinel-meanings.py:9` names `workspace_videos.corrections_hash` as its worked example of a nullable-column meaning. That column no longer exists. Replace with a live example from the same table set, or the ratchet explains itself using an object nobody can find.

- [ ] **Step 4: Run all three and confirm green**

```bash
python3 scripts/check-guard-coverage.py; echo "guard=$?"
python3 scripts/check-sentinel-meanings.py; echo "sentinel=$?"
python3 scripts/check-vocabulary-collisions.py; echo "vocab=$?"
```

Expected: all `0`.

- [ ] **Step 5: Commit**

```bash
git add scripts/check-guard-coverage.py scripts/check-sentinel-meanings.py scripts/check-vocabulary-collisions.py
git commit -F /tmp/t5-msg.txt
```

---

## Task 6: Create `0027` and `0028` together

**Files:**
- Create: `supabase/migrations/0027_stable_blob_addressing.sql`
- Create: `supabase/migrations/0028_rollback_stable_blob_addressing.sql`

**Interfaces:**
- Consumes: Tasks 1–5 (schema edited, gates able to read a live catalog, inventories repaired).
- Produces: an applied M4 schema on the local stack and a proven reversal.

⛔ **Creating `0027` starts M4-α on every machine that runs the integration suite.** Tasks 1–5 exist so that is safe.
⛔ **Splitting `0027` is an outage** (r2): `enqueue_job` inserts into `jobs` without `workspace_id` `[0009:26-27]` and the derive trigger lands with the column — every enqueue fails between two commits.

- [ ] **Step 1: Build `0027` from the three files, in dependency order**

```bash
cd /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
S=docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema
{ printf -- '-- 0027 — M4: promote the stable-blob-addressing schema (ADR-0006, 0007, 0011).\n'
  printf -- '-- Generated from %s/{01,03,04}. 05_assert.sql is NOT a migration.\n' "$S"
  printf -- '-- ⚠ ONE TRANSACTION. The CLI applies a migration file as one implicit transaction;\n'
  printf -- '-- that property is the whole recovery argument and it belongs to `supabase db push`,\n'
  printf -- '-- NOT to this SQL. `psql -f` without --single-transaction does not have it.\n\n'
  cat "$S"/01_workspaces.sql "$S"/03_generations.sql "$S"/04_artifacts.sql
} > supabase/migrations/0027_stable_blob_addressing.sql
```

- [ ] **Step 2: Assert `05_assert.sql` did not get in — mechanically, not by looking**

```bash
grep -c "execute p_sql\|delete from profiles" supabase/migrations/0027_stable_blob_addressing.sql
```

Expected: `0`. **A non-zero result means the arbitrary-SQL executor and the profile deleter are queued for production.** Add this as a permanent guard in Task 7's gate list.

- [ ] **Step 3: Write `0028`, reversing in dependency order**

```sql
-- 0028 — reverse 0027. ⚠ NOT `supabase migration down`, which RESETS (drop-and-recreate) and
-- accepts --linked; this is a forward migration that happens to undo.
--
-- LOSSLESS, and here is the falsifiable claim: every column and row 0027 creates is a function of
-- state that predates it, and no caller writes any of it. `workspace_videos` holds only
-- (workspace_id, video_id), both derived (ADR-0011 removed the one column that was not).
-- ⛔ THIS PROPERTY EXPIRES AT M5, the moment `record_artifact` gets a caller. Re-verify with
-- Task 9's repo-wide grep before running this after M5.
begin;
drop view if exists video_artifacts_current;
drop view if exists video_generations_collectable;
drop view if exists video_summary_current;
alter table videos drop constraint if exists videos_workspace_video_fk;
drop table if exists video_artifact_sources;
drop table if exists video_artifacts;
drop table if exists video_generations;
drop table if exists workspace_videos;
alter table playlists drop column if exists workspace_id;
alter table videos    drop column if exists workspace_id;
alter table jobs      drop column if exists workspace_id;
drop table if exists workspaces;
commit;
```

⚠ Enumerate every view, trigger and function `0027` creates before finalising this — the list above is the shape, and **round 5 measured that the drop order is expressible without `cascade` on the first attempt**, which is the property to preserve.

- [ ] **Step 4: Apply `0027` locally and assert with the LIVE gate**

```bash
npx supabase migration up
python3 scripts/check-live-schema.py --expect-present; echo "live=$?"
```

Expected: `live=0`.

- [ ] **Step 5: Apply `0028` and assert the reversal**

```bash
docker exec -i supabase_db_youtube-playlist-summaries-cloud psql -U postgres -d postgres \
  -v ON_ERROR_STOP=1 < supabase/migrations/0028_rollback_stable_blob_addressing.sql
python3 scripts/check-live-schema.py --expect-absent; echo "live=$?"
```

Expected: `live=0`. ⚠ **This, not "the schema gates go red", is the observation that proves removal.** v5 asserted the opposite polarity and round 5 measured it backwards.

- [ ] **Step 6: Re-apply `0027` so the branch is left in the migrated state, and commit**

```bash
npx supabase migration up
git add supabase/migrations/0027_stable_blob_addressing.sql supabase/migrations/0028_rollback_stable_blob_addressing.sql
git commit -F /tmp/t6-msg.txt
```

---

## Task 7: Add the behavioural suite to the gate list

**Files:**
- Modify: `docs/superpowers/plans/2026-08-25-m4-promote-the-schema-v2.md` (this file's gate list)
- Modify: `scripts/check-schema-gates.sh` (the `05_assert` guard from Task 6 Step 2)

**Interfaces:**
- Consumes: Task 6's applied `0027`.
- Produces: a recorded `test:integration` run against a named commit.

**Why (r4 B2):** M4 takes four live tables from **2** triggers to **9** (7 new + the 2 existing). Those triggers sit on the insert path of `claim_video_slot` `[0023:87]`, `persist_summary` / `reserve_video_slot` `[0009:94-96]`, `enqueue_job` `[0009:26-27]`, and the direct writes at `supabase-metadata-store.ts:183-191`. **The six schema gates test the schema against itself and never call an application RPC.** `tests/integration/` is the only suite that does, and `.github/workflows/ci.yml:6-10` excludes it from CI.

- [ ] **Step 1: Run the integration suite against the migrated stack**

```bash
npm run test:integration 2>&1 | tail -30
git rev-parse --short HEAD
```

Expected: green. **Record the commit** — a suite result without a build is a claim.

- [ ] **Step 2: If it cannot run, fail loudly**

If the stack is unavailable, the gate exits non-zero saying *treat this as NOT RUN*. **A skipped suite must never read as a pass** (`CLAUDE.md`).

- [ ] **Step 3: Add the `05_assert` guard to `check-schema-gates.sh`**

```bash
run "0/8  05_assert.sql is not a migration" \
  bash -c '! grep -qE "execute p_sql|delete from profiles" supabase/migrations/*.sql'
```

- [ ] **Step 4: Commit**

```bash
git add scripts/check-schema-gates.sh docs/superpowers/plans/2026-08-25-m4-promote-the-schema-v2.md
git commit -F /tmp/t7-msg.txt
```

---

## Task 8: Give `05_assert.sql` a home that is not a migration

**Files:**
- Create: `scripts/run-schema-assertions.sh`
- Create: `docs/superpowers/specs/m4/seed-assertion-corpus.sql`
- Modify: `docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema/05_assert.sql` (classification comments only)
- Modify: `scripts/check-schema-gates.sh`

**Interfaces:**
- Consumes: Task 6's applied schema; Task 3's `check-live-schema.py`.
- Produces: `scripts/run-schema-assertions.sh` — exit 0 pass, 1 assertion failed, 2 cannot run.

⚠ It cannot run standalone `[scripts/check-schema-gates.sh:14-16]` and it asserts M4-β behaviour — it reads `videos.workspace_id` `[05_assert.sql:893-911]` and checks that plain inserts derive `workspace_id` `[:1843-1859]`. **It needs an applied schema AND a populated corpus, and it has neither by default.**

- [ ] **Step 1: Classify every assertion MIGRATION-ONLY or RE-RUNNABLE**

⟳ *r5 M1.* Some assertions hold only immediately after the migration and **diverge permanently afterwards** — the backfill assertion's own precondition says so three lines above it: *"the subject here is the MIGRATION'S OUTPUT, so nothing may have touched the table yet"* `[05_assert.sql:56-58]`. Tag each assertion in place:

```sql
-- @MIGRATION-ONLY: compares the migration's output; any later write invalidates it.
-- @RE-RUNNABLE:    an invariant that must hold at all times.
```

- [ ] **Step 2: Write the seed corpus — the assertions are vacuous without one**

⟳ *r3 B4.* Create `docs/superpowers/specs/m4/seed-assertion-corpus.sql`:

```sql
-- Seeds the minimum corpus 05_assert.sql's RE-RUNNABLE assertions need to evaluate at all.
-- ⚠ Runs INSIDE a transaction the caller rolls back. It must never persist.
-- ⚠ It must exercise the DERIVE path (plain inserts), not write workspace_id directly — that is
-- the behaviour :1843-1859 asserts, and pre-filling the column would make it pass vacuously.
insert into profiles (id, is_anonymous) values ('00000000-0000-0000-0000-0000000000a1', false);
insert into playlists (id, owner_id, playlist_key)
  values ('00000000-0000-0000-0000-0000000000b1', '00000000-0000-0000-0000-0000000000a1', 'SEED_PL');
insert into videos (playlist_id, owner_id, video_id, position, data)
  values ('00000000-0000-0000-0000-0000000000b1', '00000000-0000-0000-0000-0000000000a1',
          'seedvid001', 0, '{"id":"seedvid001","title":"seed"}'::jsonb);
```

⚠ Column lists must be verified against `0001_core_schema.sql` before running — the shape above is the intent, not a guarantee that every `NOT NULL` is satisfied.

- [ ] **Step 3: Write the harness**

Create `scripts/run-schema-assertions.sh`:

```bash
#!/usr/bin/env bash
# Runs 05_assert.sql's RE-RUNNABLE assertions against a LIVE, SEEDED schema, then rolls back.
# ⛔ 05_assert.sql is NEVER a migration — it holds `delete from profiles` (:2207) and an
#    arbitrary-SQL executor (:37). This is its home instead.
# FAILS IF: an assertion raises. CANNOT RUN (exit 2) if 0027 is not applied.
set -uo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
CONTAINER="${PGCONTAINER:-supabase_db_youtube-playlist-summaries-cloud}"

if ! python3 "$REPO/scripts/check-live-schema.py" --expect-present >/dev/null 2>&1; then
  echo "CANNOT RUN — 0027 is not applied to this database, so every assertion would be vacuous"
  echo "or hard-red. Treat this as NOT RUN." >&2
  exit 2
fi

SQL=$(printf 'begin;\n'; cat "$REPO/docs/superpowers/specs/m4/seed-assertion-corpus.sql";
      awk '/@RE-RUNNABLE/{p=1} p' "$REPO/docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema/05_assert.sql";
      printf '\n\\echo ASSERTIONS_OK\nrollback;\n')
OUT=$(printf '%s' "$SQL" | docker exec -i "$CONTAINER" \
        psql -U postgres -d postgres -v ON_ERROR_STOP=1 2>&1)
if ! grep -q ASSERTIONS_OK <<<"$OUT"; then
  echo "$OUT" | tail -20 >&2
  exit 1
fi
echo "schema assertions: RE-RUNNABLE subset passed against the live schema"
```

- [ ] **Step 4: Run it, and prove the cannot-run path is real**

```bash
chmod +x scripts/run-schema-assertions.sh
./scripts/run-schema-assertions.sh; echo "exit=$?"          # expect 0 with 0027 applied
```

Then apply `0028` and run again:

```bash
./scripts/run-schema-assertions.sh; echo "exit=$?"          # expect 2, "treat this as NOT RUN"
```

⚠ **Both branches must be executed.** A cannot-run path nobody has triggered is the failure mode this repo has measured — a check that silently passes when it cannot reach its subject.

- [ ] **Step 5: Re-apply `0027`, wire the harness in, and commit**

```bash
npx supabase migration up
```

In `scripts/check-schema-gates.sh`, after the live-catalog gate:

```bash
run "8/8  schema assertions (re-runnable subset)"     ./scripts/run-schema-assertions.sh
```

```bash
git add scripts/run-schema-assertions.sh docs/superpowers/specs/m4/seed-assertion-corpus.sql \
        docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema/05_assert.sql \
        scripts/check-schema-gates.sh
git commit -F /tmp/t8-msg.txt
```

---

## Task 9: M4-α, then M4-β

**Files:** none — this task is execution and evidence.

**Interfaces:**
- Consumes: Tasks 6–8.
- Produces: production carrying `0027`.

- [ ] **Step 1: Re-measure production before applying anything**

```bash
docker exec -i -e PGU="$CLAUDE_RO_DATABASE_URL" supabase_db_youtube-playlist-summaries-cloud \
  bash -c 'psql "$PGU" -tAq -v ON_ERROR_STOP=1' < docs/superpowers/specs/m4/t1-blast-radius.sql
```

⚠ The figures decay with every ingest. **Re-measure; do not quote 2026-08-25's numbers.**

- [ ] **Step 2: Establish the repo-wide "no caller" property that `0028` depends on**

```bash
rg -n "record_artifact|video_artifacts_current|video_summary_current" lib app worker --glob '*.ts' --glob '*.tsx'
```

Expected: no matches. **Record the command and its count** — this is `0028`'s lossless falsifier, not a general reassurance.

- [ ] **Step 3: M4-α — apply to the local stack, seeded per Task 8, and run every gate**

```bash
./scripts/check-schema-gates.sh          # 9 checks, 0-8: 05_assert guard, the six, live-catalog, assertions
python3 scripts/check-anon-exposure.py --local
npm run test:integration
```

- [ ] **Step 4: Set the anon-exposure baseline against the PRE-M4 production world**

⟳ *r3 H1, corrected r4-claude H2.* Extend `MONEY_TABLES` to **all five** new tables — `workspaces`, `workspace_videos`, `video_generations`, `video_artifacts`, `video_artifact_sources` — **before** M4-β. ⚠ **Name the five; do not name a category.** v4 said "the manifest tables" and `workspaces` is the tenancy root, so the instruction added the four already safe and skipped the only unrevoked one.
⚠ **`--local` and `--prod` are not one check at two times** — measured 5 vs 10 anon-executable definer functions. **`--prod` is the gate; `--local` is a smoke test.**

- [ ] **Step 5: Open the PR and STOP. Merging is a human gate.**

- [ ] **Step 6: M4-β — after merge, apply to production with exactly this command**

```bash
supabase link --project-ref <ref>
supabase db push --dry-run     # read it
supabase db push --linked
```

⛔ The one-transaction guarantee is **void** for any other apply method. Record the CLI version.
⚠ **Have a pause-the-worker runbook ready**: `fly.toml:33-35` declares `worker` as an independently scalable process, so it can be scaled to zero if lock acquisition fails. Set an explicit `lock_timeout` (start at `5s`) and let the migration **abort** rather than queue.

- [ ] **Step 7: Assert against production with the live gate, then re-run `--prod`**

```bash
python3 scripts/check-live-schema.py --expect-present   # pointed at prod
python3 scripts/check-anon-exposure.py --prod
```

---

## Task 10: The `doc_key` ⟷ `inflight_uq` coupling, and arm backlog #26

**Files:**
- Modify: `docs/backlog.md` (#26's trigger)
- Modify: the milestone spine's M5 entry

**Interfaces:**
- Consumes: Task 9 Step 2's grep.
- Produces: a mechanical trigger for #26.

- [ ] **Step 1: Record the repo-wide grep and its count in M5's entry** ⟳ *r2 High / r3 M3: "by reading the live serve path" proves something about `serve-doc.ts` and nothing about the repo.*

- [ ] **Step 2: Wire #26's trigger to that command** ⟳ *r3 M2: v3's own paragraph called this "a decision wearing a checkbox" and then wrote one.* The trigger must be observable: *"fails the moment a non-test caller reaches `record_artifact` for a paid kind."*

- [ ] **Step 3: Commit**

---

## Order

```
T1 ─▶ T2 ─▶ T5 ─┐
T3 ──────────────┼─▶ T4 ─▶ T6 ═╤═▶ T7 ─▶ T8 ─▶ T9(α) ─▶ PR ─▶ (human merge) ─▶ T9(β) ─▶ (human gate)
                 │             ║
T10 ── any time  ┘             ╚═▶ ⚡ UNSEEDED M4-α FIRES on every machine running
       before the PR                 `npm run test:integration` from T6 onward
```

**T1 before T2** — T2 fixes the references T1 breaks; the intermediate state does not parse, and that is the proof T2 is required.
**T3 before T4** — gate 1's already-applied branch calls the live-catalog gate.
**T6 is the point of no return** for every developer's local stack.

## Gates for the milestone

1. `./scripts/check-schema-gates.sh` — **nine checks, numbered 0-8, all green**: the `05_assert`
   guard (0), the six originals (1-6), the live-catalog gate (7), the re-runnable assertions (8).
2. `check-live-schema.py --expect-present` after `0027`; `--expect-absent` after `0028`.
3. `npm run test:integration` green **against a named commit**; unavailable stack ⇒ non-zero, *treat as NOT RUN*.
4. `check-anon-exposure.py --prod` at M4-β (the gate); `--local` is a smoke test.
5. `check-docs`, `check-anchors`, `check-review-rounds`, `check-roadmap-consistency`, `check-test-counts`, `check-arch-findings`, `check-ratchet-contract`, `check-gate-falsifiability` — all 0.
6. Dual adversarial review to convergence — **both halves**, per `check-review-rounds.py`.
7. **Merging is a human gate. Applying M4-β is a second one.**

## Open questions this plan does NOT settle

- **Does `workspaces` stay 1:1 with `profiles`?** `01_workspaces.sql:33` seeds it that way with an explicit EXPIRY note. If the answer is "yes for now", it is a rename in waiting.
- **What happens to `videos.playlist_id` once `workspace_videos` exists?** Two parents for one row is the shape ADR-0002's cross-tenant guard depends on.
- **Task 8's seeding depends on whether CI gets a Postgres** — a dev-infrastructure decision with its own cost.
- **Do `corrections_hash_of()` / `no_corrections_hash()` still have callers after Task 2?** If not, deleting them is a separate decision (`0021` shares the canonicalization).

## Still NOT VERIFIED — do not repeat these as fact

- `supabase db push --linked`'s one-transaction property — help-checked, never a real remote push.
- `supabase migration down`'s drop-and-recreate behaviour — inferred from CLI wording, deliberately not executed.
- Production's `arwdDxtm` default ACL — the reviewer's measurement; no `CLAUDE_RO_DATABASE_URL` in the coordinator's environment.
