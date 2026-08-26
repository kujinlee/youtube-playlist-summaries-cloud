# M4 v2 — ROUND 5 adversarial review (CLAUDE half)

**Subject:** everything in PR #153 (`d6688d8`) — the round-4 fixes.
**Branch:** `docs/m4-round5`, based on `master` @ `d6688d8`.
**Method:** executed. A scratch database (`m4_r5_probe`) was cloned from the live pre-M4 schema, had
`build-m4-schema.py`'s output applied, and was confirmed green
(`--expect-present`, exit 0, "checked all 161 objects"). Every sabotage below was then applied to a
`create database … template m4_r5_probe` clone and the real gate re-run against it. All scratch
databases and the probe role were dropped; the shared `postgres` database is unchanged (13 public
tables, no `workspaces`); `git status --porcelain` is empty apart from this file.

**Verdict: NOT CONVERGED — 3 Blocking, 3 High, 5 Medium, 3 Low.**

---

## ⭐ THE HEADLINE

r4's stated lesson was *"a fix that moves a trust boundary must carry the guarantee across with it."*
r4 moved the predicate from **name** to **name@digest**. It carried the guarantee across for
`--expect-present`. It did **not** carry it across for `--expect-absent`, and it did not carry it
across from *"the definition matches"* to *"the rule is in force"*.

Two measured sentences, both printed by the gate as it exists on `d6688d8`:

```
$ alter table video_artifacts disable row level security;
live schema […]: M4 is PRESENT as expected — checked all 161 objects, BY DEFINITION not just by name
exit 0

$ <rollback runs; a SECURITY DEFINER record_artifact survives it>
live schema […]: M4 is ABSENT as expected — checked all 161 objects, BY DEFINITION not just by name
exit 0
```

The phrase **"BY DEFINITION not just by name"** is printed on every pass and is the round-4 claim in
the product's own voice. Both lines above are that claim being false.

---

# BLOCKING

## B1 — `--expect-absent` is blind to any surviving M4 object whose definition drifted. The rollback gate blesses a live `SECURITY DEFINER` function.

`check-live-schema.py:115-126`:

```python
def verdict(live: set[str], manifest: set[str], mode: str) -> bool:
    if forbidden(live):
        return False
    if mode == "absent":
        return not (live & manifest)
    return manifest <= live
```

`manifest` holds `kind:name@digest`. In **present** mode a digest is exactly right: the question is
*"does the live object match the definition M4 shipped?"* In **absent** mode the question is
different — *"does an object M4 created still exist at all?"* — and `live & manifest` answers it only
for survivors that are **byte-identical to the manifest**. Any drift at all makes a survivor
invisible.

`forbidden()` at `:147-154` gets this precisely right for the ADR-0011 set, and says why:

> ⚠ Matched by NAME, not by the full `name@digest` string: `ADR0011_REMOVED` records things that
> must not exist at all, so their definition is irrelevant — **and a digest-bearing comparison here
> would silently never match, which is how this check would have quietly died when digests landed.**

**That sentence is a complete description of the defect in `verdict`'s absent branch, written in the
same file, in the same commit, and not applied to it.**

### MEASURED — case A: same signature, hot-fixed body

Setup: the M4 probe database; `create or replace function video_artifacts_append_only()` with a
changed body (the shape of any post-deploy hotfix); then the **real**
`supabase/rollback/rollback_0027_stable_blob_addressing.sql` with the single line
`drop function if exists video_artifacts_append_only();` removed — i.e. a rollback that misses one
object, which is the exact class `check-live-schema.py:55-60` already documents ("0027 carries
objects the rollback never names").

```
CONTROL — rollback misses the function, body UNCHANGED
  surviving fn: video_artifacts_append_only
  --expect-absent exit=1
  FAILED — expected M4 ABSENT; 1 of 161 objects are SURVIVING:
    1 function:
        ✗ fn:video_artifacts_append_only()@e8afdb028e2855b14f6fdfc29565552c

BUG — same rollback, the function was hot-fixed first (body differs)
  surviving fn: video_artifacts_append_only
  --expect-absent exit=0
  live schema […]: M4 is ABSENT as expected — checked all 161 objects, BY DEFINITION not just by name
```

One `create or replace` is the whole difference between exit 1 and exit 0.

### MEASURED — case B: the wrong-drop-signature case the self-test claims to cover

`check-live-schema.py:222` asserts:

```python
    check("absent FAILS when a function survives — a wrong drop signature is a SILENT no-op",
          verdict({FN}, M, "absent"), False)
```

`FN` is `"fn:record_artifact(uuid)@bbb222"` — an element of the fixture manifest `M`. **A wrong drop
signature is, by definition, the case where the live signature is not the manifest's signature.** The
fixture is constructed so that it cannot exhibit the bug it is named after.

Setup: `record_artifact` has drifted by one defaulted parameter (`p_trace text default null`), so the
rollback's exact 13-type `drop function if exists` is a silent no-op. Full real rollback applied.

```
SURVIVOR: record_artifact(p_ws uuid, …, p_produced_at timestamp with time zone, p_trace text) secdef=true
--expect-absent exit=0
live schema […]: M4 is ABSENT as expected — checked all 161 objects, BY DEFINITION not just by name
```

A live, `SECURITY DEFINER`, M4-authored function on a database the gate certifies as M4-free.

**Fix direction:** absent mode must compare on `name_of(o)` — the same predicate `forbidden()` uses
and for the same stated reason. `residue()` at `:129-131` needs the same treatment, or a failure will
name the wrong objects.

---

## B2 — the digest covers *definitions* but not *enforcement state*. Seven measured sabotages, all exit 0.

The round-4 docstring (`m4_catalog.py:12-40`) frames the fix as moving from *"does an object with this
name exist?"* to *"is the guard in force?"*. It moved to *"does its definition match?"*, which is a
third thing. Every property below is one Postgres flag that decides whether a rule executes, and
**none of them is in `CATALOG_SQL`**.

Every row was applied to a fresh clone of the M4 probe and the real gate re-run:

| # | Sabotage (real SQL, applied) | `--expect-present` |
|---|---|---|
| 1 | `alter table … disable row level security` on all 5 M4 tables | **exit 0 — SURVIVED** |
| 2 | `alter table … no force row level security` | **exit 0 — SURVIVED** |
| 3 | `alter function record_artifact(…) security invoker`, same on `video_artifacts_append_only()` | **exit 0 — SURVIVED** |
| 4 | `alter function video_artifacts_append_only() reset search_path` (×3 guards) + `record_artifact` re-pointed at `public, pg_temp` | **exit 0 — SURVIVED** |
| 5 | `alter function slot_kind(text) volatile` | **exit 0 — SURVIVED** |
| 6 | `revoke select on video_artifacts from authenticated; grant insert, update, delete on video_artifacts to anon` | **exit 0 — SURVIVED** |
| 7 | `alter view video_artifacts_current set (security_invoker = true)`; `security_barrier` on `video_summary_current` | **exit 0 — SURVIVED** |
| 8 | policy dropped and recreated `as restrictive`, same cmd/roles/qual | **exit 0 — SURVIVED** |

### #1 is the one to read twice

M4 ships RLS **enabled and forced** on all five of its tables (measured on the probe:
`video_artifacts rowsecurity=true force=true`, same for the other four). Disabling it does not touch
`pg_policies`, and `pg_policies` is the entire policy input to `CATALOG_SQL:83-85`:

```
relrowsecurity now = false
pol digest = pol:video_artifacts.video_artifacts_owner_read@5de22277523ed3ae6bc225765211d5e6
manifest line = pol:video_artifacts.video_artifacts_owner_read@5de22277523ed3ae6bc225765211d5e6
gate           = M4 is PRESENT as expected — checked all 161 objects, BY DEFINITION not just by name
exit 0
```

**Byte-identical digest, five policies reported as verified, and zero of them enforcing.** This is
`tgenabled='D'` one layer out: the name is there, the definition is there, the rule is not in force.
The r4 finding was that *deletion was the only defect the harness could express*; the r5 finding is
that *redefinition is now the only defect the gate can express.*

### #3 and #4 are the ones that are exploitable rather than merely broken

M4's seven guard functions are all `security definer` with `search_path=''` (measured). `prosecdef`
and `proconfig` are not in the digest, so:

- flipping a guard to `security invoker` silently changes whose privileges the append-only rule runs
  under;
- `reset search_path` on a `SECURITY DEFINER` function is the textbook search-path hijack.

Neither changes `prosrc`, so neither changes `fn:name(args)@md5(prosrc)`.

### Negative claim, established by SEARCH not by reading

```
relrowsecurity         -> NO HITS in scripts/
relforcerowsecurity    -> NO HITS in scripts/
proconfig              -> NO HITS in scripts/
provolatile            -> NO HITS in scripts/
indisvalid             -> NO HITS in scripts/
relacl                 -> NO HITS in scripts/
permissive             -> NO HITS in scripts/
prosecdef              -> scripts/check-anon-exposure.py
has_table_privilege    -> scripts/check-anon-exposure.py
```

The two hits are in `check-anon-exposure.py`, whose `MONEY_TABLES` is
`("spend_ledger", "ledger_audit", "serve_owner_budget", "serve_model_charge", "guardrail_config")` —
**not one M4 table**. Nothing in this repository checks RLS state, grants, `security definer` or
`search_path` on `workspaces`, `video_generations`, `video_artifacts`, `video_artifact_sources` or
`workspace_videos`. The blindness is total, not merely local to this gate.

**Fix direction:** add the enforcement columns to the digest per kind — `relrowsecurity`/
`relforcerowsecurity` and `relacl` to `table:`, `prosecdef`/`proconfig`/`provolatile` to `fn:`,
`permissive` to `pol:`, `indisvalid` to `idx:`, `reloptions` to `view:`. Each is one `||` in
`CATALOG_SQL`; the manifest regenerates itself.

---

## B3 — `M4_PHASE=post ./scripts/check-schema-gates.sh` can never be green. The suite is unsatisfiable at exactly the moment the milestone succeeds.

`gen-m4-manifest.py:92-97` fails closed when the baseline already has M4:

```python
    if any(o in before for o in ("table:workspaces", "table:video_generations")):
        raise RuntimeError(
            "the baseline database ALREADY HAS M4 applied, so `after EXCEPT before` would be empty\n"
```

`before` is `read_catalog("postgres")` (`:87`) — the local container's `postgres` database, which in
the **post** phase is precisely the database that has 0027 applied. `check-schema-gates.sh:73-74`
runs this gate unconditionally, in both phases:

```bash
run "7/8  manifest is current (gen-m4-manifest.py --check)" \
    python3 ./scripts/gen-m4-manifest.py --check
```

and `run()` at `:26` converts any non-zero into `fail=1`, which `:86` returns.

**MEASURED.** `gen-m4-manifest.py --check` was executed with its baseline pointed at a database that
has M4 applied — the only change, one line, the post-phase condition:

```
CANNOT RUN — the baseline database ALREADY HAS M4 applied, so `after EXCEPT before` would be empty
or partial and this would write a manifest that passes over any database.
Treat this as NOT RUN.
gen-m4-manifest.py --check exit code = 2
```

exit 2 → `fail=1` → suite exit 1, permanently, from the moment M4-β lands locally.

`check-schema-gates.sh:58` says a gate that guesses its polarity "is how this plan shipped an
**unsatisfiable milestone twice**". This is the third, and it is in the gate that was added to close
the second.

**It is worse than a red suite.** Gate 7 is the *only* thing that checks the manifest is still what
the schema produces (see H1: the in-file sha256 cannot do it). So in the post phase — the phase in
which the manifest carries the production assertion — the manifest's currency is unverifiable.

**Fix direction:** `derive()` must not use the machine's working database as its baseline. Clone the
pre-M4 schema from the migration history (or from a second scratch database built from
`build-m4-schema.py`'s inputs) instead of from `postgres`, so the ratchet is independent of what the
developer has applied locally.

---

# HIGH

## H1 — the `# sha256:` header is a self-consistent checksum, not an integrity check. The exact r4 B2 failure is restorable in three lines of Python.

`check-live-schema.py:105`:

```python
    actual = hashlib.sha256(("\n".join(sorted(objs)) + "\n").encode()).hexdigest()
```

`objs` is parsed from the same file that carries the claimed digest. The check can detect truncation
and partial writes. It cannot detect an edit, because any edit can recompute it.

`docs/reviews/plan-m4-v2-r4-coordinator.md:46` claims:

> a short or **hand-edited** file is now CANNOT RUN, not a pass.

and `check-live-schema.py:107` says the file "does not match its own sha256 — **it has been edited by
hand** or is partially written".

**MEASURED.** The committed manifest was reduced to one object and its two header fields recomputed —
about three lines — and the gate run against the fully-applied M4 probe:

```
--- manifest_shrunk: exit=0
      live schema […]: M4 is PRESENT as expected — checked all 1 objects, BY DEFINITION not just by
      name (1 table)
```

That is r4 B2, verbatim, restored. The r4 fix raised the cost of the failure from *"delete lines"* to
*"delete lines and rerun a hash"*; it did not change its category.

Two other header attacks were run and are **not** defects (recorded so round 6 does not re-run them):
CRLF throughout → parses identically, exit 0 correct; a duplicated object line → collapses in the set,
header still matches, exit 0 correct; an indented `#` comment inside the body → correctly rejected
("header claims 161 objects, the file holds 162", exit 2).

**Fix direction:** the honest defence is gate 7 (`--check`) plus git, and the docstring should say so
rather than claiming an integrity property the hash does not have. That makes B3 strictly worse: in
the post phase there is currently **no** working defence.

## H2 — `check-schema-gates.sh` itself has no automated caller. B4's fix moved the boundary one level and stopped.

r4 B4 (`plan-m4-v2-r4-coordinator.md:57`) records:

> ✅ **FIXED** — `check-schema-gates.sh` is now **8 gates**

The finding it answers was *"the live gate existed for a whole day and NOTHING CALLED IT … A gate with
no caller is a script, not a gate"* (`check-schema-gates.sh:52-55`). That is now true of the caller:

- **Not in CI.** `grep -n "schema-gates\|check-live-schema" .github/workflows/*.yml` → no match.
- **The only wiring is a PostToolUse hook that prints a box and exits 0.**
  `.claude/hooks/check-schema-gates.sh` runs nothing; its own comment says "nothing here should be
  BLOCKED". Its text still reads *"Runs all four"* — stale by four gates.
- **The hook cannot fire for the event that matters.** `.claude/hooks/check-schema-gates.sh:32`:

  ```bash
  *2026-08-03-stable-blob-addressing/schema/*.sql|*2026-08-03-stable-blob-addressing/mutate-schema.py)
  ```

  It never matches `supabase/migrations/0027_stable_blob_addressing.sql` — the file whose *application*
  is the entire subject of gates 7 and 8.

So the chain still terminates in a human who types the command, one link further along than it did
yesterday.

*(Note for the fix: CI cannot run gates 7-8 today — they need Docker plus a live stack. That makes
this a real constraint, not an oversight; but the r4 disposition says FIXED, and it is not.)*

## H3 — the alphanumeric requirement is defeated by `select 1;`. Fourth round for this selector.

`scripts/run-schema-assertions.sh:77`:

```bash
EXECUTABLE=$(printf '%s\n' "$ASSERTIONS" | grep -v '^[[:space:]]*--' | tr -cd '[:alnum:]')
```

The comment above it (`:70-76`) names the exact shape of a real assertion —

> every real assertion here is a `do $$ … raise exception … $$;`, so requiring one alphanumeric
> character costs nothing

— and then requires something strictly weaker than that shape.

**MEASURED**, with a real run against the M4 probe (`PGDATABASE=m4_r5_probe`):

```
-- @RE-RUNNABLE
select 1;
-- @MIGRATION-ONLY
do $$ begin raise exception 'this real assertion is never sent'; end $$;
```
```
rc=0
schema assertions: RE-RUNNABLE subset passed against the live schema, and rolled back clean
```

Success reported over a block that asserts nothing. The progression is now
`anything after the marker` → `non-comment content` → `;` → **`select 1`**, four rounds of moving the
same syntactic proxy one notch. The property that would actually fail is *"the selected block raises
on a violation"* — which the file already knows how to express (`raise exception`), and which a
mutation (feed the selector a block whose assertion has been negated, require RED) would prove.

---

# MEDIUM

## M1 — `--expect-absent` is effectively unmutated, which is why B1 survived a "7/7 caught" harness.

`scripts/mutate-live-schema-check.sh` was executed in full: **exit 0, every mutation caught**, r4's
claim reproduces. But of its seven checks, only two are absent-polarity: mutation 1 (empty database →
must pass) and mutation 2 (`drop table workspaces cascade` → must fail). Mutations 3, 4, 5 and 6 —
including **both** r4 additions — are all `--expect-present`.

And mutation 2 has no discriminating power. Measured residue after `drop table workspaces cascade`:

```
FAILED — expected M4 ABSENT; 140 of 161 objects are SURVIVING
  table: 4 · view: 3 · col: 67 · trg: 14 · fn: 13 · type: 1 · idx: 9 · con: 29
```

**140 of 161.** The gate would go red on that state if it checked any single one of the nine kinds —
it is the same coarseness the 29-object gate had. Worth noting separately:
`mutate-live-schema-check.sh:83` labels the result
`"post-cascade residue -> --expect-absent FAILS (triggers survive)"`, and the measured cause is
dominated by 67 columns and 29 constraints. The mutation passes for a reason other than the one
stated.

**Fix direction:** an absent-polarity mutation of the B1 shape — apply the real rollback, leave one
object behind with a drifted definition, require RED.

## M2 — `con:` object names embed a `search_path`-dependent rendering, and `--prod` does not control `search_path`.

`m4_catalog.py:87` uses `conrelid::regclass::text`, which is schema-qualified or not depending on the
session's `search_path`. **MEASURED**, same database, same query, two sessions:

```
set search_path = '';   -> con:public.video_artifacts.art_dig_has_span
reset search_path;      -> con:video_artifacts.art_dig_has_span
```

All 38 `con:` objects (24% of the manifest) change identity. The manifest is derived through
`docker exec … psql -U postgres` (default `"$user", public`); `--prod` connects as `claude_ro`, whose
`search_path` is set by whoever created the role and is not controlled here. In present mode the
mismatch is loud; **in absent mode it is silent** (B1's mechanism — a differently-rendered object is
simply not in `live & manifest`).

**Fix direction:** `format('%I.%I', n.nspname, c.relname)` from the join, or prepend
`set local search_path = pg_catalog;` and qualify explicitly — the key must not depend on the
connection.

## M3 — `--prod` reads `information_schema.columns`, which is privilege-filtered; 70 of 161 objects (43%) are `col:`.

`m4_catalog.py:60-62` sources columns from `information_schema.columns`, which by SQL-standard
definition only shows columns the *current user* holds some privilege on. **MEASURED** on the probe:

```
columns visible to postgres:                                    165
columns visible to a role with SELECT on ONE table:              12
```

The other eight kinds read `pg_catalog`/`pg_policies`/`pg_indexes` directly and are **not** filtered
(measured under the same restricted role: `pol=11 idx=38 fn=44`, unchanged). So the exposure is
confined to `col:` — but that is 43% of the manifest, and the failure is asymmetric in the dangerous
direction: `--expect-present --prod` goes red for the wrong reason (loud), while
`--expect-absent --prod` — the polarity that runs today — passes vacuously for every column
`claude_ro` cannot see.

The manifest is generated as the container's `postgres`; the prod read is as `claude_ro`. Nothing
reconciles the two.

**Fix direction:** read columns from `pg_attribute`/`pg_type`/`pg_attrdef`, which are not
privilege-filtered — and which would also fix the `USER-DEFINED` coarseness noted in L3.

## M4 — `read_only_url` is a second implementation of an existing one, and the two disagree.

`plan-m4-v2-r4-coordinator.md:56` says `--prod` uses "the same mechanism `check-anon-exposure.py`
uses", and `m4_catalog.py:127-130` says it is "deliberately not a second driver". It is a copy:

| | `m4_catalog.py:101-117` | `check-anon-exposure.py:237-247` |
|---|---|---|
| line matched | `re.match(…, line.strip())` | `re.match(…, line)` |
| quote handling | `.strip('"').strip("'")` | `.replace('"', "")` |
| empty result | returns `""` (falsy) | `or None` |

They disagree on an indented assignment, on single quotes, and on a quote inside the URL. The
`docker exec -e PGU=…` command list is duplicated verbatim (`m4_catalog.py:133` /
`check-anon-exposure.py:268`). This is the shape `scripts/check-vocabulary-collisions.py` exists to
catch — two mechanisms for one concern — and it passed, because the collision is in Python names, not
in the schema vocabulary it reads.

## M5 — the `--prod` subject label is a claim, not a measurement.

`check-live-schema.py:289`:

```python
    subject = "PRODUCTION (read-only claude_ro)" if url else f"local container db '{a.database}'"
```

The label is derived from *whether an env var was set*, not from what was connected to. **MEASURED**:
with `CLAUDE_RO_DATABASE_URL` pointed at a local scratch database as the `postgres` role, the gate
printed

```
live schema [PRODUCTION (read-only claude_ro)]: M4 is PRESENT as expected …
```

Nothing checks `current_user`, the host, or that the session is read-only; the docstring's
"Read-only by construction: `claude_ro` holds no write grant" is a property of a role the code never
verifies it is using. Given that the whole point of B3/r4 was that the gate had been reading the
laptop while claiming production, a label that cannot be wrong-in-the-safe-direction matters.

**Fix direction:** one extra row in the catalog read —
`select current_user, inet_server_addr(), current_setting('transaction_read_only')` — and print the
measured values in the subject line.

---

# LOW

## L1 — the production URL, password included, is visible in the host process table.

`m4_catalog.py:133` builds `["docker", "exec", "-i", "-e", f"PGU={url}", container, …]`, and argv is
world-readable. **MEASURED** with a canary password:

```
docker exec -i -e PGU=postgresql://postgres:PWLEAKCANARY@127.0.0.1:5432/… supabase_db_… bash -c psql "$PGU" …
```

Pre-existing (`check-anon-exposure.py:268` does the same) so not a regression, but it is now in a
second place, and r4 introduced that second place. Two things measured and **clean**: the URL is
injection-safe (it is an env var dereferenced as `"$PGU"`; no shell re-evaluation, so metacharacters
are inert), and psql's failure message does **not** leak the password —
`CANNOT RUN — psql: error: connection to server at "127.0.0.1", port 5432 failed: FATAL: role
"baduser" does not exist`.

**Fix direction:** `docker exec -i --env-file /dev/stdin` or write the URL to a `PGPASSFILE`.

## L2 — `forbidden()` matches whole rendered names, so an ADR-0011 survivor that drifted evades it.

`ADR0011_REMOVED` holds `"fn:sync_corrections_to_workspace_video()"` — the *zero-argument rendering*.
The same drift that defeats a `drop function` signature (B1 case B, measured) defeats this too: a
survivor with an added parameter renders as `fn:sync_corrections_to_workspace_video(uuid)` and is not
in the set. Likewise `trg:videos.videos_corrections_sync_ins_trg` matches only that table. Matching on
the bare symbol (`fn:sync_corrections_to_workspace_video` as a prefix, `.<tgname>` as a suffix) would
close it.

## L3 — `col:` digests are coarser than they look, and extra objects are ignored.

`col:` hashes `data_type || is_nullable || coalesce(column_default,'')`. `data_type` is the
information_schema rendering: `USER-DEFINED` for every enum column, `ARRAY` for every array column,
and it carries no length or precision. Measured on the probe, `video_artifacts.kind` and
`video_generations.kind` both report `dt=USER-DEFINED udt=artifact_kind` — so re-typing either to a
*different* enum is invisible to the `col:` digest, and the new `type:` object it would add is
invisible too, because present mode is a subset test (`manifest <= live`, `:126`) that ignores extras.
I could not complete this sabotage end-to-end (blocked by `cannot alter type of a column used by a
view`), so **treat the composed exploit as NOT RUN**; the two ingredients are each measured.
`udt_name` in the digest costs one `||`.

---

# VERIFIED AND NOT DEFECTS

Recorded so round 6 does not spend time here. All measured on `d6688d8`.

- **`pg_get_constraintdef` DOES render `NOT VALID`** — `CHECK ((a > 0)) NOT VALID` before
  `validate constraint`, `CHECK ((a > 0))` after. A constraint weakened by `NOT VALID` **is** caught.
- **`pg_get_triggerdef` DOES render deferrability, timing and level** — measured on the constraint
  trigger: `CREATE CONSTRAINT TRIGGER … AFTER INSERT … NOT DEFERRABLE INITIALLY IMMEDIATE FOR EACH
  ROW …`. `WHEN` and `tgtype` ride in the same string. The trigger digest is the strongest of the nine.
- **Attack #4's premise is wrong: gates 7-8 DO affect the exit code.** They go through `run()`
  (`:26`), which sets `fail=1`; `:86` is `exit "$fail"`. Confirmed by the full-suite run below.
- **The `[ -f supabase/migrations/0027_*.sql ]` filename test fails SAFE in all four directions**
  (file absent/present × applied/unapplied). A missed detection lands on the default `pre` →
  `--expect-absent`, which goes RED the moment M4 is applied. No silent pass is reachable. *(0027 does
  not exist on `d6688d8` — `ls supabase/migrations/0027*` → No such file — so `M4_PHASE` is dormant
  today and the suite defaults to `pre`.)*
- **No new Docker dependency.** Gates 1-3 already require the container; 7-8 add no new class of
  developer failure.
- **`mutate-live-schema-check.sh` reproduces r4's claim exactly** — executed in full, `exit 0`,
  `✅ every mutation caught`, including mutations 5 (7 triggers `tgenabled='D'`) and 6 (guard body
  replaced).
- **`check-live-schema.py --self-test` → 24/24, exit 0.** `gen-m4-manifest.py --check` → `manifest is
  current — 161 objects`, exit 0.
- **The full 8-gate suite in the `pre` phase → exit 1**, red on gates 3 (`check-guard-coverage.py`)
  and 4 (`check-sentinel-meanings.py`) only. Gates 7 and 8 are **green**:
  `7/8 manifest is current — 161 objects`; `8/8 live schema [local container db 'postgres']: M4 is
  ABSENT as expected`. r4 H2's "TRUE AND PRE-EXISTING" disposition holds — the two red gates are the
  same two, and nothing in PR #153 touched them.
- **CRLF and duplicate manifest lines are handled correctly** (see H1).

---

# THE PATTERN, FOR THE FIFTH TIME

| Round | The fix | What it left open |
|---|---|---|
| r2 | extract the code so it can run | the extracted code was still wrong |
| r3 | hand-list → derived manifest | the derived file had no integrity check |
| r3 | selector must find non-comment content | `;` is non-comment content |
| r4 | inventory 29 → 161 **names** | names were never the predicate |
| r4 | manifest asserts its own count + sha256 | **a self-consistent hash cannot detect an edit (H1)** |
| r4 | names → **digests** | **absent mode needed the opposite change (B1)**; **"definition" is not "in force" (B2)** |
| r4 | selector requires an alphanumeric | **`select 1` is alphanumeric (H3)** |
| r4 | the live gate gets a caller | **the caller has no caller (H2)** |
| r4 | add the manifest ratchet as gate 7 | **it cannot run in the phase it exists for (B3)** |

Five of the nine rows are round 4's own fixes. The generalisation r4 wrote — *"a fix that moves a
trust boundary must carry the guarantee across with it"* — is correct and was applied in exactly one
direction each time.

**The r5 version, offered as the round's output:** *every one of these gates is a predicate over a
projection of the database, and the defect is always in what the projection drops.* Names dropped
definitions. Definitions drop enforcement state. `live & manifest` drops the survivor that drifted.
The question that finds the next one is not "is this check correct?" but **"what does `SELECT` not
select?"** — which is a question a script can ask: enumerate the catalog columns that decide whether
a rule executes, and assert each appears in `CATALOG_SQL`.

---

# VERDICT

**NOT CONVERGED.** 3 Blocking, 3 High, 5 Medium, 3 Low.

B1, B2 and B3 must be fixed before M4-β: B1 makes the rollback verification unsound, B2 makes the
"BY DEFINITION" claim untrue for the security layer, and B3 makes the post-phase suite unsatisfiable —
so there is no green path to reporting the milestone done even if the first two were fixed.

⛔ Merging stays a human gate. Applying M4-β to production is a second one.

---

## Hygiene

- Scratch databases created: `m4_r5_probe`, `m4_r5_casc`, and one per sabotage
  (`m4_r5_rlsoff`, `…noforce`, `…secinvoker`, `…searchpath`, `…volatility`, `…grants`, `…viewinv`,
  `…polrestrict`, `…abs_ctl`, `…abs_bug`, `…abs_sig`, `…sig2`, `…rls`). **All dropped** — verified:
  `select datname from pg_database where datname like 'm4_%'` returns nothing.
- Probe role `r5_ro_probe` revoked and dropped.
- The shared `postgres` database is unchanged and **still pre-M4**: `workspaces exists = false`,
  `public tables = 13`.
- `git status --porcelain` is empty apart from this file.
- `docs/reviews/plan-m4-v2-r5-codex.md` was deliberately **not read**, to keep the halves independent.
