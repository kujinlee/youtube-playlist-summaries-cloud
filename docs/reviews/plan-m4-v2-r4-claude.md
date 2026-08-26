# M4 v2 — ROUND 4 adversarial review (CLAUDE half)

**Reviewer:** Claude (adversarial half of the round-4 dual review)
**Date:** 2026-08-25
**Branch:** `docs/m4-round4`, based on `master` @ `903004d`
**Primary subject:** PR #152 (`903004d`) — `scripts/m4_catalog.py`, `scripts/gen-m4-manifest.py`,
the rewritten `scripts/check-live-schema.py`, `docs/superpowers/specs/m4/live-manifest.txt`.
**Merged to `master` without any adversarial pass.** This is its first review.

**Verdict: NOT CONVERGED.** 2 Blocking · 3 High · 5 Medium · 4 Low.

---

## What I executed

Every finding below was produced by running something, against throwaway databases in the local
Supabase container (Postgres 17.6). The commands are quoted inline so each is reproducible.

| Run | Result |
|---|---|
| Independent re-derivation of the manifest, twice, into `r4_rederive_a` / `r4_rederive_b` | **161 objects both times, set-identical to the committed manifest** |
| `check-live-schema.py --self-test` | **20/20, exit 0** |
| `build-m4-schema.py --self-test` | **22/22, exit 0** |
| `mutate-live-schema-check.sh` | exit 0, **6 `report` lines all ✓** (the plan and commit message say "5") |
| `run-schema-assertions.sh` with a genuinely failing assertion | **exit 1** — the harness can go red |
| Rollback step 9's `version = '0027'` against the live ledger | **CORRECT** — see *Verified good*, below |
| 12 direct probes of `strip_comments` / `table_body` | 2 latent defects (M4, L3) |
| 6 manifest-corruption probes + 3 same-name/different-semantics probes | **B1, H1** |

**Hygiene.** The shared `postgres` database was never mutated and is still pre-M4 (`--expect-absent`
→ exit 0 at the end of this review; the M4 table count in `public` is 0). Every scratch database I
created was dropped; `pg_database` is byte-identical to its state at the start
(`_supabase, postgres, storage_vectors, template0, template1`). `git status --porcelain` shows only
this review file and the codex half. **No repo-tracked file was modified.**

---

## BLOCKING

### B1 — ⭐ The new gate compares **names only**. All seven own-table guards can be disabled, two
guard function bodies replaced with `return new`, and a check constraint weakened to `check (true)`,
and it still prints **"M4 is PRESENT as expected — checked all 161 objects", exit 0.** MEASURED, three ways.

This is r3 B2 again. r3 B2's harm was stated precisely — `m4_catalog.py:14-17`:

> MEASURED: it reported "M4 is PRESENT as expected", exit 0, over a database with ALL SEVEN of M4's
> own-table triggers dropped — every append-only, freeze and immutability guard gone

The fix widened the *inventory* from 29 names to 161 names. It did not widen the *predicate*.
`CATALOG_SQL` (`m4_catalog.py:33-61`) selects identifiers and nothing else:

```sql
select 'trg:' || c.relname || '.' || t.tgname from pg_trigger t …
select 'con:' || conrelid::regclass::text || '.' || conname from pg_constraint c …
```

No `pg_get_triggerdef`, no `tgenabled`, no `prosrc`, no `pg_get_constraintdef`, no `pg_get_expr` for
policies, no column type or nullability. So a database in which every guard exists and none of them
*does* anything is indistinguishable from a correct one.

**Attack A — disable, don't drop.** Built M4 into scratch `r4_semantics`, then:

```sql
alter table video_artifacts        disable trigger video_artifacts_append_only_trg;
alter table video_generations      disable trigger video_generations_freeze_trg;
…all seven…
```

`tgenabled` proves the guards are off:

```
art_summary_has_no_source_trg          -> D
forbid_collecting_current_trg          -> D
video_artifact_sources_append_only_trg -> D
video_artifact_sources_insert_once_trg -> D
video_artifacts_append_only_trg        -> D
video_artifacts_generation_complete_trg-> D
video_generations_freeze_trg           -> D
```

```
$ python3 scripts/check-live-schema.py --database r4_semantics --expect-present
live schema: M4 is PRESENT as expected — checked all 161 objects (…14 triggers…)
rc=0
```

**Attack B — same name, gutted body.**

```sql
create or replace function video_artifacts_append_only() returns trigger
  language plpgsql security definer set search_path = public as $fn$
begin
  return new;   -- every append-only guard removed; the NAME is untouched
end $fn$;
```

Same for `video_generations_freeze()`. Gate: **exit 0, "checked all 161 objects".**

**Attack C — weaken a check constraint, keep its name.**

```sql
alter table video_artifacts drop constraint art_dig_has_span;
alter table video_artifacts add  constraint art_dig_has_span check (true);
```

Gate: **exit 0, "checked all 161 objects"** — `con:video_artifacts.art_dig_has_span` is still in
`pg_constraint`, which is all the gate reads.

**Why this is Blocking and not Medium.**

1. It is *the same class* as the finding it closes, at a different depth. `check-live-schema.py:26-27`
   condemns the old gate as *"a gate asserting a claim four times wider than what it reads"*. The
   new one asserts `M4 is PRESENT` — a claim about the schema — from a set of identifiers.
2. The flagship mutation is one word from being defeated. `mutate-live-schema-check.sh:110-118`
   proves the gate by **dropping** the seven guards. Change `drop trigger` to
   `alter table … disable trigger` and the harness reports the mutation SURVIVED. The harness
   therefore measures deletion, not enforcement.
3. `docs/superpowers/plans/2026-08-25-m4-promote-the-schema-v2.md:961` makes this gate the sole
   post-M4-β check on production, and §4's one-transaction property is marked NOT VERIFIED. The
   question it must answer is *"is the schema that is now live the schema in this repo?"*, and it
   cannot see a difference in any definition.
4. The realistic production path is not sabotage: an out-of-band `create or replace function`
   hotfix, or an older `0027` pushed before the final one, produces exactly this state — identical
   names, different semantics — and the gate says PRESENT.

**Fix, and it is cheap precisely because the manifest is derived.** There is no hand-list to
maintain: extend `CATALOG_SQL` to carry the definition alongside the name and regenerate. E.g.

```sql
select 'trg:' || c.relname || '.' || t.tgname || ' = ' || t.tgenabled::text || ' ' ||
       md5(pg_get_triggerdef(t.oid)) from pg_trigger t …
select 'con:' || conrelid::regclass::text || '.' || conname || ' = ' ||
       md5(pg_get_constraintdef(c.oid)) from pg_constraint c …
select 'fn:'  || … || ' = ' || md5(p.prosrc) …
select 'col:' || table_name || '.' || column_name || ' = ' || data_type || ' ' || is_nullable …
```

`check-live-schema.py` needs no change — the comparison is already set algebra, and the failure
report already names offending strings. Then add a sixth mutation: `disable trigger`, not `drop`.

---

### B2 — ⭐ `check-live-schema.py` **cannot connect to production.** The plan's M4-β verification step
runs it "pointed at prod"; run literally it reads the **local** stack and prints PASS.

`plan:958-963`, Task 9 Step 7 — *"Assert against production with the live gate"*:

```bash
python3 scripts/check-live-schema.py --expect-present   # pointed at prod
python3 scripts/check-anon-exposure.py --prod
```

There is no mechanism by which the first line can reach production. The only transport in the whole
module is a `docker exec` into a hard-coded local container — `m4_catalog.py:25`:

```python
CONTAINER = "supabase_db_youtube-playlist-summaries-cloud"
```

`m4_catalog.py:75-77`:

```python
    p = subprocess.run(
        ["docker", "exec", "-i", container, "psql", "-U", "postgres", "-d", database, "-tAq"],
        input=CATALOG_SQL, capture_output=True, text=True)
```

`check-live-schema.py:207` calls `read_catalog(a.database)` — no `container` argument, and the CLI
exposes none. Search confirms it: `grep -nEi "DATABASE_URL|PGHOST|host|port|psycopg|connstr"` over
`check-live-schema.py`, `gen-m4-manifest.py` and `m4_catalog.py` returns **no connection option** —
every hit is prose or an `import`. `--help` lists exactly `--expect-absent`, `--expect-present`,
`--self-test`, `--database`, `--manifest`, and `--database` is a *database name inside that
container* (`check-live-schema.py:189-192`).

**The consequence is the worst available one.** By Task 9 Step 7, the local stack has had `0027`
applied since Task 6. So the command as written succeeds, prints
`live schema: M4 is PRESENT as expected — checked all 161 objects`, exits 0 — and the human ticks
"production verified" having verified their laptop. It does not error, does not warn, and does not
name what it connected to. This is the project's own stated worst case, quoted in
`check-anon-exposure.py:34`: *"a check over the wrong subject is an assertion in better packaging."*

**It is worse than an oversight, because the repo already solved it.** `check-anon-exposure.py` — the
other half of the same Step 7 — defaults to **prod** through a read-only URL
(`check-anon-exposure.py:238-269`):

```python
    if os.environ.get("CLAUDE_RO_DATABASE_URL"):
        return os.environ["CLAUDE_RO_DATABASE_URL"]
```

…falling back to `.env.local`, and using `psql "$PGU"` inside the container as a *transport* rather
than as the target. Catalog introspection is read-only, so `CLAUDE_RO_DATABASE_URL` is sufficient.

**Fix:** give `check-live-schema.py` the same `--prod` / `CLAUDE_RO_DATABASE_URL` path
`check-anon-exposure.py` has, print the target it actually read in both the pass and fail lines, and
make a bare invocation refuse to guess between local and prod — the same "no default" discipline
Task 3 Step 7 already applies to polarity. Until then `plan:961` should say **NOT RUNNABLE**, not
`# pointed at prod`.

---

## HIGH

### H1 — A corrupted manifest fails **open** in `--expect-absent`, and `--expect-present` reports
success over a single object. `load_manifest` rejects only the empty file.

`check-live-schema.py:67-78` guards exactly one corruption:

```python
    if not objs:
        raise ValueError(
            f"the manifest at {path} is EMPTY. An empty expected set makes --expect-present pass
             over any database at all, which is the failure this gate exists to prevent.")
```

Nothing asserts the manifest's *size*, its provenance, or that it is current. Measured, against
scratch `r4_rederive_a` which has all 161 objects:

| Manifest | Mode | Result |
|---|---|---|
| full (161) | present | exit 0 — *"checked all 161 objects"* ✅ |
| **truncated to its first line** | present | **exit 0 — *"checked all 1 objects"*** ⛔ |
| comments only | present | exit 2 ✅ correctly rejected |
| CRLF line endings | present | exit 0, 161 objects ✅ handled |
| indented `# comment` appended | present | exit 1 — fails closed (noisy, see L3) ✅ |
| **one line, `table:this_object_never_existed`** | **absent** | **exit 0 — *"M4 is ABSENT as expected"*** ⛔ |

The last row is the dangerous one. That database contains **every one of M4's 161 objects**, and the
gate that exists to confirm the rollback worked says the rollback worked. `absent` is
`MANIFEST ∩ live = ∅`, so *any* manifest that has drifted away from the live names passes it
vacuously — the smaller the corruption leaves it, the more certainly it passes.

The `present` row is the same defect in the polarity that fails loudly-ish: the only signal that 160
objects were not checked is the digit `1` inside a success sentence.

This matters because **the manifest is now the trust root and nothing checks it** (see H2). The file
is a plain-text artifact marked `⛔ DO NOT HAND-EDIT` with no count, no checksum, and no automated
staleness run. A botched merge-conflict resolution or a partial `git checkout` produces exactly rows
2 and 6, six weeks from now, silently.

**Fix (cheap):** have `gen-m4-manifest.py` emit a machine-readable `# objects: 161` line and have
`load_manifest` fail unless the parsed count matches it. That converts every truncation into an
exit 2 without needing the generator to run.

### H2 — Nothing runs either new gate. The staleness ratchet has **no caller anywhere in the repo**. VERIFIED BY SEARCH.

```
$ grep -rn "check-live-schema\|gen-m4-manifest\|run-schema-assertions" \
      .github/ .claude/ package.json scripts/ supabase/ Makefile \
   | grep -v "<their own files>"
```

Every surviving hit is a prose mention, plus two real call sites:

* `scripts/mutate-live-schema-check.sh:27,104,117,139` — the gate's own mutation harness;
* `scripts/run-schema-assertions.sh:40` — as a *precondition*, not as a gate.

And **neither of those two scripts is itself wired into anything**:

* `scripts/check-schema-gates.sh` runs six gates (`:30-46`), numbered `1/6`…`6/6`. It mentions
  neither script and contains no `M4_PHASE`. `grep -rn "M4_PHASE" scripts/ .github/ .claude/
  package.json` → **zero hits.**
* `package.json` `scripts` — 21 entries, none of them.
* `.claude/hooks/` — 8 hooks, none of them.
* `.github/workflows/` — no hit.

`gen-m4-manifest.py --check` has **zero call sites of any kind.**

Consequences:

1. `check-live-schema.py:32` calls `--check` *"the staleness ratchet"*. A ratchet nobody pulls is a
   convention, and this repo's own memory says a convention catches what you read while a script
   catches what is there.
2. `plan:1001` states milestone Gate 1 as `M4_PHASE=post ./scripts/check-schema-gates.sh` —
   **"nine checks, numbered 0-8, all green"**. That command does not exist. `M4_PHASE` is ignored,
   and the suite runs six checks that do not include either new gate. Task 3 Step 7 (`plan:403-438`)
   is still `- [ ]`, so this is *known*-not-done — but the milestone gate list is written as though
   it were, and it is the list a human will read at the merge gate.
3. Everything asserted about these gates today — 161 objects, 5/5 mutations, 20/20 self-test — is
   true of a script that runs only when someone remembers to type it.

**Fix:** land Task 3 Step 7, and in the same edit add `gen-m4-manifest.py --check` beside it, so the
manifest cannot silently drift from the schema it is derived from.

### H3 — `run-schema-assertions.sh` reports **"RE-RUNNABLE subset passed against the live schema"**
over a block whose only non-comment line is a bare `;`. MEASURED. The r3 H1 fix is defeated by one character.

`run-schema-assertions.sh:70-77` is the r3 fix:

```bash
EXECUTABLE=$(printf '%s\n' "$ASSERTIONS" | grep -v '^[[:space:]]*--' | tr -d '[:space:]')
if [ -z "$EXECUTABLE" ]; then
  echo "CANNOT RUN — no @RE-RUNNABLE block with EXECUTABLE SQL in $ASSERT." >&2
```

The predicate is *"a non-comment, non-whitespace character exists"*. It cannot distinguish an
assertion from punctuation. Measured against `r4_rederive_a` (M4 applied), via the `ASSERT_FILE`
seam:

```
-- @RE-RUNNABLE          -- @RE-RUNNABLE            -- @RE-RUNNABLE
-- nothing asserted      -- nothing asserted        -- only comments
;                        select 1;
```

| Assert file | Result |
|---|---|
| bare `;` | **exit 0 — "RE-RUNNABLE subset passed against the live schema, and rolled back clean"** ⛔ |
| `select 1;` | **exit 0 — same message** ⛔ |
| comments only | exit 2 ✅ (the case the r3 fix *did* close) |
| `select 1/0;` | exit 1 ✅ the harness can go red |

`run-schema-assertions.sh:16-19` names the failure this guard exists to prevent — *"psql runs an
empty script, and the gate reports 'passed' having asserted nothing"* — and the guard admits both a
semicolon and a tautology. This is the **third** iteration of the same fail-open in this one
selector (r1 B5/B6, r3 H1, now).

The realistic path is not an adversary: `05_assert.sql` carries **zero** markers today. Task 8 adds
them. If a later edit removes the assertions from inside a marked block and leaves the marker and a
stray `;` or `commit;`, this gate stays green forever, and **the success line names neither the file
nor how many statements ran** — `ASSERT_FILE` is an unbounded env seam whose target is never echoed.

**Fix:** count statements that are neither comments nor bare punctuation, refuse below a floor
(≥1 is fine; ≥1 *terminated statement containing an identifier* is better), and put the count and
the resolved `$ASSERT` path in the success line: *"N assertion statements from `<path>` passed"*.
A gate that reports what it read cannot be silently emptied.

---

## MEDIUM

### M1 — The committed manifest is **not** what the generator now produces, and `--check` cannot see it.

`render()` (`gen-m4-manifest.py:121-123`) and the committed file differ, measured by calling
`render()` on the committed object set:

```
--- committed
+++ rendered
-# 5 tables · 3 views · 70 columns · 14 triggers · 13 functions · 1 type · 12 indexs · 5 policys · 38 constraints
+# 5 tables · 3 views · 70 columns · 14 triggers · 13 functions · 1 type · 12 indexes · 5 policies · 38 constraints
```

`docs/superpowers/specs/m4/live-manifest.txt:13` still carries `12 indexs · 5 policys` — the exact
naive-plural output that `m4_catalog.py:64-65` was written to fix:

> `# singular, plural — because "12 indexs · 5 policys" is what naive +s produced, and a summary line`
> `# is the part of a gate a human actually reads.`

So the manifest was generated *before* `KIND_LABEL` landed and never regenerated, and it shipped in
the same commit as its own fix. `--check` reports `manifest is current` regardless, because
`read_committed()` (`gen-m4-manifest.py:126-130`) strips every `#` line: the ratchet covers the 161
object lines and **not the file**. Harmless today; it means "current" is a narrower claim than the
word implies, and the one artifact that documents the derivation is stale on day one.

**Fix:** in `--check`, compare `render(manifest)` against the file's full text, not just the object
set.

### M2 — The generator's declared fail-closed guard is decorative. The real protection is a property
of `build-m4-schema.py`'s output that nothing asserts.

`gen-m4-manifest.py:82-87`:

```python
    # fail closed: a baseline that already has M4 yields a manifest asserting nothing
    if any(o in before for o in ("table:workspaces", "table:video_generations")):
```

Two names, out of 161. A baseline carrying any *other* M4 residue passes it. I tested the obvious
one — a leftover enum, which is what a rollback that dropped tables but not types leaves:

```
$ (clone pre-M4 baseline into r4_partial_m4; create type artifact_kind …)
guard-named tables present: 0        # the guard would NOT have fired
$ psql -d r4_partial_m4 -v ON_ERROR_STOP=1 < built.sql
apply-over-residue rc=3
ERROR:  type "artifact_kind" already exists
```

**So it does fail closed — but not for the declared reason.** It fails because
`build-m4-schema.py`'s output contains, measured over all 136,081 bytes:

* `if not exists` — **0 occurrences**
* `create or replace` — **0 occurrences**
* `drop …` — **0 occurrences**

Every `create` and every `add column` is unconditional, so *any* pre-existing M4 object aborts the
apply, and `derive()` turns that into exit 2 (`gen-m4-manifest.py:111-112`). That property is
load-bearing for the manifest's integrity and is written down nowhere. Adding a single
`create table if not exists` — the most natural thing anyone ever does to make a migration
re-runnable — silently converts an abort into a partial diff, and the guard's two table names will
not catch it.

**Fix:** assert the property where it lives. Either widen the guard to *"any manifest object is
already in `before`"* (the manifest is right there), or add an assertion in `build-m4-schema.py`
that its output contains no `if not exists` / `or replace`, with the reason.

### M3 — The clone step's exit status is the pipeline's last command, and its `psql` has no
`ON_ERROR_STOP`. A failing `pg_dump` is invisible. MEASURED.

`gen-m4-manifest.py:93-99`:

```python
    clone = subprocess.run(
        ["docker", "exec", "-i", CONTAINER, "sh", "-c",
         f"pg_dump -U postgres -d postgres --schema-only --no-owner --no-privileges "
         f"| psql -U postgres -d {SCRATCH} -q"],
        capture_output=True, text=True)
    if clone.returncode != 0:
```

`sh` returns the status of the **last** command in a pipeline, so `clone.returncode` is psql's, never
pg_dump's; and psql without `-v ON_ERROR_STOP=1` exits 0 after any number of errors. Measured — my
own re-derivation, using this exact command:

```
clone rc: 0    ERROR:  permission denied to set parameter "log_min_messages"
```

An error on stderr, and rc 0. The same shape appears three more times in
`mutate-live-schema-check.sh:56-58`, `:86-88`, `:132-134`.

The baseline is the manifest's trust root; it is the one input whose fidelity is never asserted. I
could not construct a case where a partial clone *inflates* the manifest (`after − before` can only
drop objects the baseline has), and the two positive `report` lines in the mutation harness act as
canaries — so the live risk today is low. But the mechanism is precisely the class this repo keeps
paying for: a status that reports the wrong process.

**Fix:** add `set -o pipefail` to the `sh -c`, and `-v ON_ERROR_STOP=1` to the receiving psql.

### M4 — The mutation harness scores **exit 2 (cannot run) as "mutation caught"**, and its own counting
does not match its claims.

`mutate-live-schema-check.sh:27`:

```bash
gate() { python3 ./scripts/check-live-schema.py --database "$SCRATCH" "$1" >/dev/null 2>&1; }
```

`gate` collapses exit 1 (*the gate detected the mutation*) and exit 2 (*the gate never ran — missing
manifest, unreachable database*) into a single non-zero, and `report … fail "$r"` scores non-zero as
✓ for every negative expectation (`:83`, `:118`, `:140`). A missing manifest would be recorded as
three caught mutations. The two positive expectations (`:77`, `:105`) are canaries that would fire
first, so this is not currently exploitable — but the harness is the *only* evidence that the gate is
load-bearing, and it must distinguish "went red" from "did not run". That distinction is the first
rule in `CLAUDE.md`.

Counting: the commit message says *"mutate-live-schema-check.sh 5/5"* and `plan:376-383` tabulates
five. The script emits **six** `report` lines (measured), labelled `mutation 1`, an unnumbered
positive, `mutation 2`, `mutation 4`, `mutation 3` — no mutation 5, and out of order. Also `mutation
1` ("an empty database must read ABSENT") is not a mutation; it is the trivial case.

**Fix:** capture `$?` explicitly and treat 2 as NOT RUN → `fail=1`; renumber; state the count from
the script's own tally rather than in prose.

### M5 — The plan contradicts itself on three measured counts, and one of them is now wrong.

| Claim | Where | Measured today |
|---|---|---|
| *Expected: `self=0` with **`16/16`***| `plan:400` | **20/20** — and `plan:384` says "Self-test **20 cases**" *sixteen lines earlier* |
| suite gate number `7/7` | `plan:308` | — |
| suite gate number `7/8` | `plan:430` | — |
| *"**nine checks, numbered 0-8**"* | `plan:1001` | `check-schema-gates.sh` has **six**, numbered `1/6`…`6/6` |

`plan:400` is the one that matters: it is a Step-6 verification instruction, so anyone executing the
plan literally records a **failed** check against a script that is green. Note the plan's own rule
two lines up — *"a number in prose is a number that rots"* (`plan:324`) — written about this exact
number.

The numbering is worse than cosmetic: Step 7's snippet (`plan:430`) inserts `7/8` beside six gates
that still label themselves `x/6`, so applying it literally produces a suite printing
`1/6 … 6/6 … 7/8 … 8/8`. Nothing in the plan renumbers the existing six.

---

## LOW

### L1 — Stale symbols PR #152 deleted, still cited as live code.

* `plan:646` — *"Those seven are `M4_LIVE_TRIGGERS` in `check-live-schema.py`."* The symbol is gone;
  the file's only remaining mentions are historical (`m4_catalog.py:16`,
  `mutate-live-schema-check.sh:90`), correctly in the past tense.
* `plan:77` and `plan:706` — cite `M4_FUNCTIONS` (13). Also deleted.

`plan:706` is load-bearing prose: *"If a signature is wrong, that gate goes red — which is exactly
why the gate had to \[name signatures]"*. The behaviour survives (the manifest carries
`pg_get_function_identity_arguments`, `m4_catalog.py:48`), so the claim is still true; only the
symbol is dead. Retarget both to the manifest.

### L2 — Success is decided by `grep -q ASSERTIONS_OK` **anywhere** in the output, so the asserted
file can declare its own success. MEASURED.

`run-schema-assertions.sh:79-88`. Assert file:

```sql
-- @RE-RUNNABLE
\echo ASSERTIONS_OK
select 1/0 as this_should_be_red;
```

→ **exit 0, "RE-RUNNABLE subset passed against the live schema, and rolled back clean"**, with a
division-by-zero in the transcript. Low because it needs `\echo ASSERTIONS_OK` inside `05_assert.sql`,
which is implausible. Worth a line: the marker should be required to be the **last** non-empty line
of output, not merely present. The header at `:22-23` correctly cites `scripts/codex-review.py` as
the precedent for marker-decided success — that script checks the *final message*, which is the part
that carries the strength.

### L3 — A manifest line that is an indented comment becomes a phantom expected object.

`check-live-schema.py:73` — `not ln.startswith("#")` — is column-sensitive, so `   # note` is parsed
as an object. Measured: `--expect-present` exits 1 (fails closed, correct) but reports
`1 # an indented comment:` as an object *kind*, because `by_kind` (`m4_catalog.py:87`) splits on the
first `:` and there is none. Cosmetic; `ln.lstrip().startswith("#")` fixes it.

### L4 — `con:` names are rendered through `conrelid::regclass::text`, whose output is
search_path-dependent.

`m4_catalog.py:58`. `regclass`'s text output omits the schema only when the relation is visible in
the current `search_path`. Both reads currently go through the same `docker exec … psql -U postgres`
with the same default, so `before` and `after` agree and all 38 constraints render bare — verified,
my derivation matched the committed manifest exactly. It becomes a real mismatch the moment the gate
reads a target whose role or database sets a different `search_path` — which is exactly what B2's fix
does. Then all 38 `con:` entries mismatch: `--expect-present` fails loudly (fine),
`--expect-absent` passes **vacuously** (not fine, see H1). Prefer
`n.nspname || '.' || rel.relname` explicitly, or `set search_path` in `CATALOG_SQL`.

---

## Verified good — things I tried to break and could not

These are stated so the round's clean results are attributable to a measurement, not to silence.

1. **The manifest is deterministic, and reproduces independently.** Two full derivations into
   distinct scratch databases (`r4_rederive_a`, `r4_rederive_b`), each cloning the pre-M4 baseline,
   applying `build-m4-schema.py --quiet`, and taking `after − before`:
   **161 objects, run A == run B, and both set-identical to the committed manifest — symmetric
   difference empty.** That covers the auto-generated names specifically: `videos_workspace_id_fkey`,
   `video_artifacts_state_check`,
   `video_generations_workspace_id_video_id_generation_id_kind_key` (62 chars, two under the 63-char
   truncation limit) all reproduce. **The r3 B2 "option (a)" claim of 161 is correct.**
2. **Rollback step 9's `'0027'` is the right version string — not a silent no-op.**
   `supabase/rollback/rollback_0027_stable_blob_addressing.sql:114`:
   `delete from supabase_migrations.schema_migrations where version = '0027';`
   Measured against the live ledger:
   ```
   0026|record_correction_spend
   0025|settle_is_observable
   0024|lease_covers_serve
   …
   ```
   The CLI stores the bare 4-digit prefix in `version` and the remainder in `name`, across all eight
   applied migrations. `0027_stable_blob_addressing.sql` will store `0027`. **r3 B3's fix is real.**
3. **A partial-M4 baseline is rejected** (though see M2 for *why*).
4. **Manifest robustness**: CRLF line endings are handled (`.strip()`); a comments-only file is
   correctly rejected with exit 2 and an explanation; an object name containing the delimiter `:`
   groups correctly (`split(":", 1)`); duplicate lines are deduplicated by the set.
5. **Self-tests and the harness**: `check-live-schema.py --self-test` 20/20 exit 0;
   `build-m4-schema.py --self-test` 22/22 exit 0; `mutate-live-schema-check.sh` exit 0 with all six
   reports ✓, including the r3 B2 case (seven guards **dropped** → `--expect-present` correctly red).
6. **`table_body` handles the paren cases it claims.** `create table t (a int, primary key (a, b));`
   → `'a int, primary key (a, b)'`; a `create table` inside a dollar-quoted body does not steal the
   match into a wrong body (it returns `None`, and `build-m4-schema.py:200-202` turns `None` into a
   hard error). Two latent defects remain, neither reachable today:
   * `code.find(f"create table {table}")` has **no word boundary**: `table_body(code, "t")` over
     `create table t_extra (x int); create table t (a int);` returns **`'x int'` — the wrong table's
     body**. Only `"workspace_videos"` is passed today (`:200`), and no M4 table name prefixes
     another, so no live bug. It is the same *"a pattern that matches what I READ"* class the
     docstring at `:116-120` claims depth-counting cured — it cured the paren half, not the locating
     half.
   * `create table  t` (two spaces) → `None` → hard error. Fail-closed, but brittle.
7. **`strip_comments` is line-local**, and `in_str` is reinitialised at every line (`:92-93`). A
   string literal spanning lines therefore desynchronises it, and a `--` on the second line is
   treated as a comment:
   ```python
   strip_comments("raise exception 'line one\n  line two -- NOT a comment';")
   -> "raise exception 'line one\n  line two "
   ```
   That is precisely the blinding the r3 fix was written to prevent (`:76-84`), one line down, and
   the docstring's claim at `:86-89` — *"tracks single-quoted strings … and only honours `--` outside
   one"* — is true within a line only. **Measured not to be live**: scanning all three real inputs
   (`01_workspaces.sql`, `03_generations.sql`, `04_artifacts.sql`) found **zero** string literals
   spanning a line break; every odd-quote line is an apostrophe inside a trailing `--` comment, which
   the code handles correctly. Latent, but it is the second time this function has been wrong in the
   blinding direction.

---

## What I could not run

Nothing material was blocked. Docker and the local Postgres 17.6 container were available throughout.

**One thing is untestable by construction and must be said:** B2 means **no claim in this review, or
in any prior round, is evidence about the production database.** Every measurement here — mine, r3's,
the mutation harness's — was taken against the local container, because that is the only thing the
instrument can reach. *Treat every statement about prod as NOT RUN.*

---

## Round-4 stop-condition note

Three of round 3's fixes were re-examined here. Two hold (**rollback step 9**, `table_body`'s paren
handling). One does not (**H3** — the `run-schema-assertions.sh` selector is fail-open for the third
consecutive round, now by a bare `;`). And the round-3 Blocking that was closed by PR #152 is
**re-opened one level down** (**B1** — 18% of names became 100% of names and 0% of definitions).

That is the pattern `docs/dev-process.md` arms Phase 6 on: a fix that moves the defect rather than
removing it, in the same component, across rounds. Round 4 is round 4 of this plan. **If round 5
produces another Blocking in `check-live-schema.py` or the assertion selector, fire Phase 6 rather
than opening round 6** — the question stops being *"is this gate correct?"* (always locally
patchable) and becomes *"is name-set equality the right predicate for 'did the migration apply?'"*,
which no per-round fix will reach.

---

**NOT CONVERGED.** 2 Blocking · 3 High · 5 Medium · 4 Low.

**B1 and B2 both block M4-β specifically**, not merely the PR: B2 means the production assertion step
cannot be executed as written, and B1 means that even once it can be, a PASS does not establish that
the guards which make the artifact tables append-only are enforcing anything.
