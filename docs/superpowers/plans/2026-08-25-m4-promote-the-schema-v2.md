# M4 — Promote the schema as migrations — Implementation Plan

> **Anchor:** `stable-blob-addressing` — **ADR:** 0006, 0007, 0011
> **Goal:** A blob's address stops moving when a title or a serial number changes. M4 is the step that makes the accepted schema EXECUTE, for the first time outside a review's rollback.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Promote `01_workspaces.sql`, `03_generations.sql` and `04_artifacts.sql` into a single reversible migration `0027`, applied first to a local stack and then to production, with a rollback and a behavioural gate that both actually run.

**Architecture:** One migration file, one transaction. The three spec files are concatenated in dependency order; `05_assert.sql` is never a migration. A companion **rollback script** reverses it — a manual repair tool, never a migration (Task 6 Step 3). Correctness is established by six schema gates (rewritten to read a **live** catalog, not to rebuild from source), the integration suite, and a live-catalog assertion.

**Tech Stack:** PostgreSQL 15 (Supabase), Supabase CLI 2.115.0, Python 3 ratchets, Jest (`--runInBand`) for integration.

---

## ⛔ Read before touching anything

**1 — WRITING `supabase/migrations/0027_*.sql` IS M4-α.** `tests/integration/global-setup.ts:43-51` runs `npx supabase migration up` on **every** integration run and **throws rather than skip**. The moment that file exists on the branch, the next `npm run test:integration` on any machine applies all of M4 to that machine's stack. **That is why 0027 is created in Task 6, not Task 1** — everything that must be ready first is ready first.

**2 — M4 IS NOT INERT.** `01_workspaces.sql:36-48` adds `workspace_id` to `playlists`, `videos`, `jobs`, backfills every row and sets each `NOT NULL`. After ADR-0011 it attaches **SEVEN** triggers to live tables (was nine; the two corrections-sync triggers are deleted in Task 1).

**3 — `05_assert.sql` IS NEVER A MIGRATION.** It contains `delete from profiles where id = p;` `[05_assert.sql:2207]` and `execute p_sql;` — an unrevoked arbitrary-SQL executor `[:37]`. Task 8 gives it a home that is not `supabase/migrations/`.

**4 — THE ONE-TRANSACTION GUARANTEE BELONGS TO THE APPLY COMMAND, NOT THE SQL.** `psql -f` without `--single-transaction`, or a dashboard paste, does not have it. ⚠ `supabase migration down` **exists** but *resets* (drop-and-recreate) and accepts `--linked` — **it is not the rollback. Task 5 is.**

## What this plan supersedes

`docs/superpowers/plans/2026-08-25-m4-promote-the-schema.md` (v5.1) — five revisions, five non-converging review rounds, eleven Blocking/High findings. `docs/reviews/architecture-review-2026-08-25.md` established that nine of the eleven were one defect, and **ADR-0011 dissolves it**. Four findings (r3 H3, r4 M2, r5 B1, r5 B3) require no fix in this plan because the state they describe cannot occur.

**Carried forward, because they survive ADR-0011:** the gate repairs, the named apply command, the rollback script, the `test:integration` gate, and the architecture review's finding 3.

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
| `scripts/check-live-schema.py` + `gen-m4-manifest.py` + `m4_catalog.py` | **Created** — the live-catalog gate. Checks **all 161** objects against a manifest DERIVED BY EXECUTION (r3 B2, option (a)) |
| `supabase/migrations/0027_stable_blob_addressing.sql` | **Create** — the three spec files, one transaction (Task 6) |
| `supabase/rollback/rollback_0027_stable_blob_addressing.sql` | **Created** `322d411` — the reverse, PROVEN by execution. ⛔ NOT a migration (Task 6 Step 3) |
| `scripts/check-guard-coverage.py`, `check-sentinel-meanings.py`, `check-vocabulary-collisions.py` | **Modify** — inventories, after Task 1 removes objects (Task 5) |
| `docs/superpowers/specs/2026-08-03-stable-blob-addressing/verify-schema.sh`, `mutate-schema.py` | **Modify** — read the migration, not the spec dir (Task 4) |

---

## Task 1: Remove corrections from `workspace_videos` (ADR-0011)

**Files:**
- Modify: `docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema/03_generations.sql`

⛔ **EDIT BY CONTENT ANCHOR, NEVER BY LINE NUMBER.** ⟳ *r1 B4 (claude) / H1 (codex), coordinator-verified.*
The citations `:52,:61,:89-95,:183-185,:227-236,:253-262` are all correct **against the file as it
stands** — and Step 2 deletes two lines, so every later one shifts by −2 (89→87, 183→181, 227→225,
253→251) **before the step that uses it**. A task cannot address a file its own earlier steps move.
Each step below therefore quotes the text to find. ⚠ This is ADR-0006's lesson one layer up: *an
address derived from something that moves is not an address* — which is the very goal this plan
delivers.

**Interfaces:**
- Consumes: nothing.
- Produces: a `workspace_videos` with columns `(workspace_id, video_id)` only; triggers on `videos` reduce from 4 to 2.

⚠ **CORRECTION, MEASURED 2026-08-25.** This line used to read *"`corrections_hash_of(text)` and
`no_corrections_hash()` **remain defined** (Task 2 keeps a caller)"*. **The parenthetical is false.**
Grepping the built post-ADR-0011 SQL for `corrections_hash_of` outside its own definition returns
**nothing** — Task 2 removes the last call site, and the only remaining reference is
`corrections_hash_of` calling `no_corrections_hash` inside itself.

They do remain *defined*, so the sentence's main clause and `M4_FUNCTIONS` (13) are both right, and
the rollback drops them. But `0027` ships **two functions with no caller**. They are `revoke`d from
`public, anon, authenticated`, so this is dead code rather than exposure. **Open, and deliberately
not decided here:** drop them from the spec (a 13→11 change rippling through four inventories), or
keep them for M5. ⚠ Flagged for round 3 — *not* filed.

- [ ] **Step 1: Confirm the starting state, so the diff is a measurement not a hope**

```bash
cd docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema
grep -c "corrections" 03_generations.sql          # expect 50 (⟳ r1: a draft said 20,
                                                  # which was a COMMENT-FILTERED count pasted
                                                  # into an unfiltered command)
grep -c "^create trigger" 03_generations.sql      # expect 10
```

- [ ] **Step 2: Drop the two columns**

In `03_generations.sql`, delete the two lines that read **exactly**:

```sql
  corrections        text,
  corrections_hash   text not null default no_corrections_hash(),
```

Both sit inside `create table workspace_videos (…)`. Add immediately above that `create table`:

```sql
-- ⟳ ADR-0011 (2026-08-25) — CORRECTIONS ARE PER-PLAYLIST AND DO NOT LIVE HERE.
-- This table is workspace-scoped; `videos` is playlist-scoped (0001_core_schema.sql:30). Carrying
-- `corrections` here collapsed N playlist rows into 1 with no merge rule, and produced nine of the
-- eleven Blocking/High findings across five review rounds. The truth stays in `videos.data`.
```

- [ ] **Step 3: Simplify the backfill**

Find the statement beginning `insert into workspace_videos (workspace_id, video_id, corrections,`
and replace it, through its terminating `;` (the `order by … desc;` line), with:

```sql
insert into workspace_videos (workspace_id, video_id)
  select distinct workspace_id, video_id from videos;
```

⚠ `distinct`, not `distinct on` — there is no longer a column whose value depends on which row wins, so the ordering that used to pick a winner is gone with it.

- [ ] **Step 4: Simplify the derive trigger's upsert**

Inside `resolve_workspace_from_playlist()`, find the block beginning
`insert into public.workspace_videos (workspace_id, video_id, corrections,` and replace it,
through `on conflict (workspace_id, video_id) do nothing;`, with:

```sql
    insert into public.workspace_videos (workspace_id, video_id)
    values (v_ws, new.video_id)
    on conflict (workspace_id, video_id) do nothing;
```

- [ ] **Step 5: Delete the sync function and its two triggers**

Delete, by name rather than by line:

1. the whole `create function sync_corrections_to_workspace_video() returns trigger … $$;` body;
2. the line `revoke all on function sync_corrections_to_workspace_video() from public, anon, authenticated;`;
3. both `create trigger videos_corrections_sync_ins_trg` and `…_upd_trg` statements;
4. the comment block between them that explains the round-9 clobber defect — it documents a
   mechanism that no longer exists, and a comment outliving its subject is how this repo's
   ratchets end up explaining themselves with objects nobody can find.

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
- Modify: `docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema/04_artifacts.sql` (two ranking sites)
- Modify: `…/schema/05_assert.sql` — ⟳ *r1 B3: 52 corrections references, no task touched them*

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

- [ ] **Step 4: Sweep `05_assert.sql` — ⛔ ADR-0011 IS IMPLEMENTED AT TWO OF THREE SITES WITHOUT THIS**

⟳ **r1 B3, BOTH halves.** The first draft edited `03` and `04` and left the assertion harness alone;
Task 8 said it gets *"classification comments only"*. But `05_assert.sql` holds **52** `corrections`
references — it asserts the dropped columns, inserts into them, updates them, and inventories the
deleted sync function:

```bash
grep -c "corrections" docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema/05_assert.sql
# 52. Every one of them breaks the moment Task 1 lands.
```

⛔ **DO NOT WORK FROM A HAND LIST. THE PREDICATE IS THE DELIVERABLE.** ⟳ *r2 B5 (codex) / H2
(claude), and the coordinator's re-measurement made it worse than reported.* A five-row table here
named `:62`, `:119`, `:819-821`, `:899-905`, `:1315-1319` and was cited as the sweep. r2 found it
missed `:1913,:1915`. **Measured 2026-08-25: it misses far more than two.**

**The distinction that makes the sweep tractable — and that a bare `grep corrections` destroys:**

> ADR-0011 removes `workspace_videos.corrections` and `.corrections_hash`. **It does not remove
> corrections.** They stay in `videos.data`, per-playlist. So assertions reading
> `data->>'corrections'` are still valid and **must be kept**.

```bash
S=docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema
# MUST GO — the removed columns and the deleted function. MEASURED: 32 code lines.
grep -n "corrections_hash\|sync_corrections_to_workspace_video\|corrections from workspace_videos\|wv\.corrections" \
  $S/05_assert.sql | grep -v ":\s*--"
# MUST STAY — corrections in videos.data, which ADR-0011 keeps. MEASURED: 11 code lines.
grep -n "corrections" $S/05_assert.sql | grep -v ":\s*--" \
  | grep -v "corrections_hash\|sync_corrections_to_workspace_video\|corrections from workspace_videos\|wv\.corrections"
```

| | Measured |
|---|---|
| `corrections` anywhere in `05_assert.sql` | **52** |
| …on code lines (not comments) | **43** |
| …naming a REMOVED object → delete | **32** |
| …reading `videos.data` → **keep** | **11** |
| named by the old hand list | **5 ranges** |

**Delete the assertions whose subject ADR-0011 removed** — including the whole round-9 block at
`:1908-1917`, which asserts that a second playlist cannot clobber `workspace_videos.corrections`, a
behaviour that no longer exists in a schema without that column. Do **not** rewrite them to assert
something else; an assertion retargeted to keep it alive is how a suite ends up testing what is easy
rather than what matters.

⚠ **The lesson, because it is this repo's most expensive recurring one:** *a convention catches what
you READ; a script catches what is THERE.* A hand list in a plan is a snapshot of one person's
attention. Step 5 below is the actual gate.

- [ ] **Step 5: Prove no site was missed — the search is the deliverable**

⟳ **r3 HIGH (codex) — THIS GATE CONTRADICTED THE PREDICATE THREE PARAGRAPHS ABOVE IT.** It used to
be a bare `grep -rn "corrections"` expecting **no output**, while Step 4 had just established that
**11 code lines reading `videos.data->>'corrections'` MUST BE KEPT.** Measured on the same file, the
same day: `must_go=32`, `must_stay=11`. So the gate as written could only be satisfied by deleting
valid assertions. **The gate must use the sweep's own predicate, not a broader one:**

```bash
S=docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema
grep -rn "corrections_hash\|sync_corrections_to_workspace_video\|corrections from workspace_videos\|wv\.corrections" \
  "$S"/ | grep -v ":[[:space:]]*--" | grep -v "corrections_hash_of\|no_corrections_hash"
```

Expected: **no output**. Anything remaining is a reference to a column or function that no longer
exists. ⚠ A bare `grep corrections` here is **wrong** and will stay wrong: ADR-0011 removes
`workspace_videos.corrections*`, **not** corrections.

⚠ **Fourth instance today of *fixed at one of two sites*** — and this one was self-inflicted within
the hour, by the very edit that introduced the must-keep predicate. The rule again, because writing
it down has not yet been enough: **a fix that adds a requirement must grep for its callers in the
same edit** — and a *predicate* is a requirement, so its gate is a caller.
⚠ If `corrections_hash_of()` / `no_corrections_hash()` now have zero callers, **leave them defined and
say so in the commit** — deleting them is a separate decision with its own blast radius (`0021`
shares the canonicalization).

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

### ✅ STEPS 1–6 ARE DONE — the gate is a real file, committed and mutation-proven

`scripts/check-live-schema.py` exists (`f0c789c`, hardened `322d411`). **This task no longer
contains its source**; it contains what was measured building it, because three of those
measurements changed the design.

| Was specified | What running it showed |
|---|---|
| a self-test of **5** cases | **16.** The file prints its own count — a number in prose is a number that rots |
| check tables and columns | **five kinds.** `drop table workspaces cascade` removes every M4 table and column while leaving all seven live-table triggers alive; the two-kind version returned **exit 0** over a database where nobody can sign up |
| prove RED "inside a rolled-back transaction" | ⛔ **impossible.** The gate opens its OWN connection, so it cannot see another session's uncommitted transaction. `scripts/mutate-live-schema-check.sh` builds the state for real in a throwaway database instead. **3/3 mutations caught** |

⭐ **A fourth measurement, 2026-08-25, changed it again.** Its inventory is the *post*-ADR-0011 one,
so it was structurally blind to anything ADR-0011 deletes. A rollback over a schema built without
Tasks 1–2 left `sync_corrections_to_workspace_video()` and both `videos_corrections_sync_*` triggers
alive, and the gate reported **ABSENT as expected** — the same shape as the `cascade` residue it was
written to catch. `ADR0011_REMOVED` now fails in **both** polarities, and mutation 3 proves it.

⚠ **`--expect-absent` must fail on a PARTIAL teardown, which is the state a failed rollback leaves.**
That is the whole point: the case the first version could not see is the case that kills the product.

### ✅ COVERAGE: r3 B2 RESOLVED — the gate checks all 161 objects, from a DERIVED manifest

⟳ *r3 Blocking (claude). **User chose option (a), 2026-08-25.***

**What was wrong.** The gate carried five hand-written tuples naming **29 of 161** objects — **18%**:

| Kind | Named | Of |
|---|---|---|
| tables · functions · types | 5 · 13 · 1 | 5 · 13 · 1 |
| columns | 3 | **70** |
| triggers | **7** | **14** |
| views · indexes · policies · constraints | **0 · 0 · 0 · 0** | 3 · 12 · 5 · 38 |

MEASURED: it reported *"M4 is PRESENT as expected"*, **exit 0**, over a database with **all seven of
M4's own-table guard triggers dropped** — every append-only, freeze and immutability guard. That is
the dangerous state, not a tidy one: the tables exist and accept writes the design forbids.

**The fix — the manifest is DERIVED BY EXECUTION, never parsed and never remembered.**

```bash
python3 scripts/gen-m4-manifest.py           # clone pre-M4 → apply → `after EXCEPT before`
python3 scripts/gen-m4-manifest.py --check   # staleness ratchet: fails if the schema moved
```

It writes `docs/superpowers/specs/m4/live-manifest.txt` — **161 lines, one `kind:name` per object**
— and `check-live-schema.py` compares a live catalog against exactly that set. Comparison is set
algebra: `present` is `MANIFEST ⊆ live`, `absent` is `MANIFEST ∩ live = ∅`.

⛔ **Why not parse the SQL.** That reproduces the defect being fixed. The old inventory was
hand-written, and separately `grep -c "^create trigger"` undercounts by one because
`art_summary_has_no_source_trg` is a **`create constraint trigger`**. Every reader of the text
inherits that class of error; the catalog does not.

⛔ **The generator fails closed on a baseline that already has M4.** The manifest is a *diff*; if
`0027` is already applied, `after EXCEPT before` is empty or partial and it would write a manifest
that passes over any database at all — the exact failure this finding is about.

**Proven, not asserted** — `scripts/mutate-live-schema-check.sh`, **5/5 caught**:

| Mutation | Result |
|---|---|
| empty database | `--expect-absent` passes |
| M4 applied | `--expect-present` passes |
| `drop table … cascade` residue | `--expect-absent` **FAILS** (live-table triggers survive) |
| pre-ADR-0011 schema | `--expect-present` **FAILS** (sync fn + 2 triggers) |
| ⭐⭐ **all seven own-table guards dropped** | `--expect-present` **FAILS** — *the case the 29-object gate blessed with exit 0* |

Self-test **20 cases**, five of which assert a *view / index / policy / constraint / column* is
missing — kinds the old gate named **zero** of.

⚠ **What this does NOT do.** It compares against the manifest generated from *this* repo's pre-M4
baseline. It is not a proof that `db push --linked` is atomic — §4's one-transaction property is
still **NOT VERIFIED**, and remains the other half of option (b). What changed is that a partial
apply is now *detectable*, where before it was not.

- [ ] **Step 6: Re-run both, and record the counts against a commit**

```bash
python3 scripts/check-live-schema.py --self-test > /tmp/st.txt 2>&1; echo "self=$?"
bash scripts/mutate-live-schema-check.sh > /tmp/mut.txt 2>&1; echo "mut=$?"
git rev-parse --short HEAD
```

Expected: `self=0` with `16/16`, `mut=0` with `✅ every mutation caught`. ⚠ A tick records *that*
something was verified, never *what against* — name the commit.

- [ ] **Step 7: Wire it in — ⚠ THE EXPECTED STATE IS A PARAMETER, NOT A CONSTANT**

⟳ **r1 B1 (codex) / B6 (claude).** The first draft hard-wired `--expect-absent` into
`check-schema-gates.sh`. But Task 9 Step 3 runs that same suite **after `0027` is applied**, and
`check-schema-gates.sh:22-27` fails on any non-zero — so the milestone's "all green" was
**structurally unsatisfiable**. A gate asserting *absence* cannot sit in a checklist run when the
thing is *present*.

**This is the same defect as v5's B2, which was fixed this morning** — asserting a polarity without
asking what the gate observes at that moment. Fixing the instance did not fix the class. The class
fix is: **make the expected state something the caller must supply**, so omitting it is an error.

In `scripts/check-schema-gates.sh`, take the phase from the environment and **refuse to guess**:

```bash
# M4_PHASE is REQUIRED once 0027 exists: `pre` (0027 not applied) or `post` (applied).
# ⛔ No default. A default is how a gate silently answers the wrong question.
if [ -f supabase/migrations/0027_stable_blob_addressing.sql ] && [ -z "${M4_PHASE:-}" ]; then
  echo "CANNOT RUN — 0027 exists, so this suite needs M4_PHASE=pre|post to know which polarity to"
  echo "assert. Refusing to guess. Treat this as NOT RUN." >&2
  exit 2
fi
case "${M4_PHASE:-pre}" in
  pre)  LIVE_FLAG=--expect-absent  ;;
  post) LIVE_FLAG=--expect-present ;;
  *)    echo "M4_PHASE must be pre or post, got '$M4_PHASE'" >&2; exit 2 ;;
esac
run "7/8  live catalog matches M4_PHASE=${M4_PHASE:-pre}"  python3 ./scripts/check-live-schema.py "$LIVE_FLAG"
```

⚠ Gates 1 and 2 have the **same** problem in the opposite direction — they rebuild from source and so
can only run `pre`. Task 4 Step 2 gives them a cannot-run branch; that branch and this parameter must
tell the same story, or the suite contradicts itself.

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

## Task 6: Create `0027`, and prove the rollback against it

**Files:**
- Create: `supabase/migrations/0027_stable_blob_addressing.sql`
- Run (already created, `322d411`): `supabase/rollback/rollback_0027_stable_blob_addressing.sql` — ⛔ **not a migration**, see Step 3

**Interfaces:**
- Consumes: Tasks 1–5 (schema edited, gates able to read a live catalog, inventories repaired).
- Produces: an applied M4 schema on the local stack and a proven reversal.

⛔ **Creating `0027` starts M4-α on every machine that runs the integration suite.** Tasks 1–5 exist so that is safe.
⛔ **Splitting `0027` is an outage** (r2): `enqueue_job` inserts into `jobs` without `workspace_id` `[0009:26-27]` and the derive trigger lands with the column — every enqueue fails between two commits.

- [ ] **Step 1: Build `0027` with the builder — ⛔ NOT `cat`**

```bash
cd /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
{ printf -- '-- 0027 — M4: promote the stable-blob-addressing schema (ADR-0006, 0007, 0011).\n'
  printf -- '-- Generated by scripts/build-m4-schema.py. 05_assert.sql is NOT a migration.\n'
  printf -- '-- ⚠ ONE TRANSACTION. The CLI applies a migration file as one implicit transaction;\n'
  printf -- '-- that property is the whole recovery argument and it belongs to `supabase db push`,\n'
  printf -- '-- NOT to this SQL. `psql -f` without --single-transaction does not have it.\n\n'
  python3 scripts/build-m4-schema.py
} > supabase/migrations/0027_stable_blob_addressing.sql
```

⟳ **MEASURED 2026-08-25 — this step used to be `cat 01 03 04`, and that builds the WRONG SCHEMA.**
Until Tasks 1–2 land, the spec files still create `sync_corrections_to_workspace_video()` and both
`videos_corrections_sync_*` triggers, which ADR-0011 deletes. Two consequences were measured, not
argued: `scripts/mutate-live-schema-check.sh` was proving the live gate against a schema M4 will
never ship, and a rollback over that schema left all three objects alive while
`check-live-schema.py --expect-absent` reported **ABSENT as expected**.

`build-m4-schema.py` applies Tasks 1–2, is idempotent (each edit reports `applied` or `already`, so
it keeps working once Tasks 1–2 have landed), and rests its verdict on the **end state** rather than
on the anchors. `--self-test`: 14 cases. It exits 1 if the spec is in neither state — which is also
this step's guard that Task 1 actually landed.

- [ ] **Step 2: Assert `05_assert.sql` did not get in — mechanically, not by looking**

```bash
grep -c "execute p_sql\|delete from profiles" supabase/migrations/0027_stable_blob_addressing.sql
```

Expected: `0`. **A non-zero result means the arbitrary-SQL executor and the profile deleter are queued for production.** Add this as a permanent guard in Task 7's gate list.

- [ ] **Step 3: Run the rollback — ⛔ IT IS ALREADY WRITTEN, AND ITS ORDER IS LOAD-BEARING**

⟳ **r1 B1/B2, both halves, and the coordinator reproduced it.** The previous draft of this step was
wrong twice over and the second failure was catastrophic. **Read this before writing a line:**

| What was tried | What Postgres did |
|---|---|
| drop `video_artifacts_current` first | `ERROR: cannot drop … view video_generations_collectable depends on it` `[04:918 selects 04:728]` |
| reorder the views, then drop the columns | `ERROR: cannot drop column workspace_id … trigger playlists_resolve_workspace_upd_trg depends on it` — a column-list trigger `[03:201-203]` is a hard dependency |
| **`drop table workspaces cascade`** — *the fix Postgres' own `HINT` suggests on both errors* | ⛔ **ALL SEVEN workspace triggers SURVIVE**, still referencing `public.workspaces`. Measured signup: `ERROR: relation "public.workspaces" does not exist` in `ensure_workspace_for_profile()` via `handle_new_user()`. **No user can sign up; playlist creation and every enqueue break identically.** |

⛔ **NEVER USE `cascade` IN THE ROLLBACK.** Postgres will recommend it twice and it produces a live outage
rather than a rollback. If a drop fails, the order is wrong — fix the order.

### The inventory, MEASURED — 161 catalog objects

⟳ *r2-claude M4.* The previous figure ("44 objects … 13 triggers") was **derived by grep and wrong**.
This one is a catalog diff: the post-ADR-0011 schema applied to a clone of the live pre-M4 database,
`after EXCEPT before`.

| Kind | Adds | |
|---|---|---|
| tables + views | **8** | 5 tables, 3 views |
| columns | **70** | including the 3 derived `workspace_id` |
| triggers | **14** | ⚠ **not 13** |
| functions | **13** | |
| enum | **1** | |
| indexes | **12** | |
| policies | **5** | |
| constraints | **38** | |
| **total** | **161** | |

⚠ **WHY THE TRIGGER COUNT WAS OFF BY ONE, because the cause generalises.** `grep -c "^create
trigger"` returns **13**; the catalog holds **14**. The missing one is
`art_summary_has_no_source_trg`, declared as **`create constraint trigger`** `[04_artifacts.sql]`. A
constraint trigger is still a trigger, so **any inventory built by grepping `create trigger`
systematically misses every one of them.** The count that matters is the catalog's.

**The distinction that makes the rollback writable:** the 14 split **7 / 7**. The seven on M4's
**own** tables (`video_generations` ×2, `video_artifacts` ×2, `video_artifact_sources` ×3) die with
`drop table`. The **seven on LIVE tables** — `profiles`, `playlists` ×2, `videos` ×2, `jobs` ×2 —
survive, and must be named. Those seven are `M4_LIVE_TRIGGERS` in `check-live-schema.py`.

### ⛔ IT IS NOT A MIGRATION, AND IT IS ALREADY WRITTEN

**The rollback lives at `supabase/rollback/rollback_0027_stable_blob_addressing.sql`** (committed
`322d411`). This step no longer writes SQL — it runs a file that has already been executed.

⟳ **MEASURED 2026-08-25, and this is why it moved.** Two throwaway migrations, `9998` creating a
table and `9999` dropping it:

```
Applying migration 9998_probe_create.sql...
Applying migration 9999_probe_drop.sql...
{"applied":[…9998…,…9999…],"message":"Migrations applied"}
m4_order_probe rows in catalog: 0
```

`supabase migration up` applies **every** pending file in ascending order in **one pass**, and the
later file wins. A rollback filed as `0028` therefore runs immediately after `0027` on every fresh
database — `db push` to production, `db reset`, and `tests/integration/global-setup.ts` alike. **The
pair composes to a no-op: production receives an empty milestone, and the local suite tests a schema
that is not there.** The previous draft of this step committed both files into
`supabase/migrations/`.

Note which gate would have caught it: `check-live-schema.py --expect-present`, because it reads the
live catalog. The five that rebuild from the spec files would all have stayed green — they never
read the migration directory. That is the SUBJECT axis, again.

`schema_paths = []` in `supabase/config.toml`, so nothing under `supabase/rollback/` is ever
replayed.

### It is PROVEN, not asserted

Built the post-ADR-0011 schema into a throwaway database (161 objects), ran the file verbatim under
`ON_ERROR_STOP=1`, and diffed the catalog **both directions** against the pre-M4 clone — tables,
views, columns, triggers, functions, types, indexes, policies **and constraints**:

```
13 DROP FUNCTION · 7 DROP TRIGGER · 5 DROP TABLE · 4 ALTER TABLE · 3 DROP VIEW · 1 DROP TYPE
skipping-notices: 0        LEFTOVER: 0        DESTROYED: 0
```

⛔ **A WRONG `drop function` SIGNATURE IS A SILENT NO-OP UNDER `if exists`** — the statement
succeeds, the function survives, and nothing reports it. **`skipping-notices: 0` is the falsifier**,
and it is why the run greps for `NOTICE … skipping` rather than trusting the exit code. ⟳ *My own
first draft got **two of thirteen** wrong:* `slot_kind` takes **`text`**, not `artifact_kind`; and
`record_artifact` takes **13** parameters, not the 7 I first wrote.

**Do not eyeball this. Derive it, then assert it:**

```bash
# every signature, as Postgres itself renders it — this is the form `drop function` needs
docker exec -i supabase_db_youtube-playlist-summaries-cloud psql -U postgres -d postgres -tAq -c \
  "select p.proname||'('||pg_get_function_identity_arguments(p.oid)||')'
     from pg_proc p join pg_namespace n on n.oid=p.pronamespace
    where n.nspname='public' order by 1;"
```

**And the falsifier that makes the no-op impossible to miss:** after the rollback,
`check-live-schema.py --expect-absent` reports any surviving function by name (Task 3's
`M4_FUNCTIONS`). If a signature is wrong, that gate goes red — which is exactly why the gate had to
grow past tables and columns.

- [ ] **Step 4: Apply `0027` locally and assert with the LIVE gate**

```bash
npx supabase migration up
python3 scripts/check-live-schema.py --expect-present > /tmp/live.txt 2>&1; echo "live=$?"
```

Expected: `live=0`. ⚠ **Redirect, then read `$?` on its own line.** `$?` after a pipe reports the
LAST command's status, and that mistake produced four false greens in one day.

- [ ] **Step 5: Run the rollback and assert the reversal**

```bash
docker exec -i supabase_db_youtube-playlist-summaries-cloud psql -U postgres -d postgres \
  -v ON_ERROR_STOP=1 < supabase/rollback/rollback_0027_stable_blob_addressing.sql > /tmp/rb.txt 2>&1
grep -c "skipping" /tmp/rb.txt            # expect 0 — a NOTICE here is a SILENT no-op drop
python3 scripts/check-live-schema.py --expect-absent > /tmp/live.txt 2>&1; echo "live=$?"
```

Expected: `live=0`, `skipping` count `0`. ⚠ **This, not "the schema gates go red", is the observation
that proves removal.** v5 asserted the opposite polarity and round 5 measured it backwards.

- [ ] **Step 6: Re-apply `0027` so the branch is left in the migrated state, and commit**

```bash
npx supabase migration up
git add supabase/migrations/0027_stable_blob_addressing.sql
git commit -F /tmp/t6-msg.txt
```

⛔ **`0027` ONLY.** The rollback is already committed, and it is not a migration — adding it to
`supabase/migrations/` is the no-op composition measured in Step 3.

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
- Modify: `…/schema/05_assert.sql` (classification comments; the ADR-0011 sweep happens in Task 2 Step 4)
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

### ✅ THE SEED AND THE HARNESS ARE WRITTEN AND EXECUTED

Both exist and both have been run. **This task no longer contains their source.**

| File | State |
|---|---|
| `docs/superpowers/specs/m4/seed-assertion-corpus.sql` | ⟳ **r3 B4, r1 B5, r2** — third draft, first one that runs |
| `scripts/run-schema-assertions.sh` | all four outcomes exercised |

**The seed's third draft is the first that inserts a row, and the second failure is the instructive
one.** Draft 1 could not insert at all (`profiles.id` → `auth.users(id)`; `playlist_url` NOT NULL).
Draft 2's fix added `insert into auth.users …` *above* an explicit `insert into profiles …` — a
guaranteed `duplicate key … profiles_pkey`, because `auth.users` carries `on_auth_user_created` and
`handle_new_user()` already inserts that row:

```
on_auth_user_created | handle_new_user
  insert into public.profiles (id, is_anonymous) values (new.id, coalesce(new.is_anonymous, false));
```

⛔ **There is no explicit profiles insert in the seed, and adding one back breaks it.** Column lists
were derived by querying `information_schema` for every NOT NULL with no default, not eyeballed.

**The seed asserts itself**, because a corpus that silently seeds nothing makes every downstream
assertion vacuous — and a vacuous assertion reports success. MEASURED, three mutations:

| Mutation | Result |
|---|---|
| `profiles_ensure_workspace_trg` disabled | `ERROR: owner … has no workspace — cannot derive workspace_id` |
| `videos_resolve_workspace_ins_trg` disabled | `ERROR: null value in column "workspace_id" … violates not-null` |
| both, plus `workspace_id` made nullable | `ERROR: SEED FAILED: videos.workspace_id is null — the derive trigger did not fire` |

⚠ **Note what the first two prove and what they do not.** They show the *schema* fails closed before
the seed's own check is ever reached — stronger than the check, but it left the check itself
unproven. The third mutation exists solely to make that branch reachable, and it fires.

**The harness has four outcomes and all four were executed:**

| Outcome | Proven by |
|---|---|
| exit 2 — `0027` not applied | run against the real local stack |
| exit 2 — no `@RE-RUNNABLE` marker | `05_assert.sql` carries **0** today; an empty assertion set must never report success |
| exit 0 — success | a synthetic marked file, with `@MIGRATION-ONLY` traps **before and after** the block; ⟳ *neither was selected — this is r1 B5/B6's fail-open `awk` selector, fixed and demonstrated* |
| exit 1 — an assertion raises | a deliberately false assertion |

⚠ `ASSERT_FILE` exists so the **success path can be proven before Task 8 Step 1 adds the markers**.
Without it the only reachable outcomes are the two cannot-run branches, and a harness whose happy
path has never executed is the artifact this extraction exists to stop shipping. Same reasoning as
`--database` on `check-live-schema.py`.

⚠ Success is decided by a **marker in the output**, never an exit code — `scripts/codex-review.py`'s
rule, for its reason.

- [ ] **Step 4: Run it, and prove the cannot-run path is real**

```bash
chmod +x scripts/run-schema-assertions.sh
./scripts/run-schema-assertions.sh; echo "exit=$?"          # expect 0 with 0027 applied
```

Then run the rollback and run again:

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

- [ ] **Step 2: Establish the repo-wide "no caller" property that the rollback depends on**

```bash
rg -n "record_artifact|video_artifacts_current|video_summary_current" lib app worker --glob '*.ts' --glob '*.tsx'
```

Expected: no matches. **Record the command and its count** — this is the rollback's lossless falsifier, not a general reassurance.

- [ ] **Step 3: M4-α — apply to the local stack, seeded per Task 8, and run every gate**

```bash
M4_PHASE=post ./scripts/check-schema-gates.sh   # 9 checks, 0-8; see the caller warning below
python3 scripts/check-anon-exposure.py --local
npm run test:integration
```

⛔ **`M4_PHASE=post` IS REQUIRED HERE, AND OMITTING IT IS AN `exit 2`, NOT A FAILURE YOU WOULD
NOTICE.** ⟳ *r2 B3 (codex) / B1 (claude).* Task 3 Step 7 made the suite **refuse to guess** once
`0027` exists — the right design, and it left every existing caller unchanged. By this step `0027`
does exist, so a bare invocation prints `CANNOT RUN` and stops.

⚠ **This was the THIRD instance in one day of *fixed at one of two sites*** — after v5's `:120`
maintenance-window residue and the `05_assert` sweep. The counter-practice, stated so it is
mechanical: **a fix that adds a requirement must grep for its callers in the same edit.** The two
callers in this plan are here and the milestone gate list; both now carry the variable.

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

1. `M4_PHASE=post ./scripts/check-schema-gates.sh` — **nine checks, numbered 0-8, all green**: the
   `05_assert` guard (0), the six originals (1-6), the live-catalog gate (7), the re-runnable
   assertions (8). ⛔ **The variable is not optional once `0027` exists** — without it the suite
   exits 2 by design (Task 3 Step 7). Before `0027`, use `M4_PHASE=pre`.
2. `check-live-schema.py --expect-present` after `0027`; `--expect-absent` after the rollback.
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
