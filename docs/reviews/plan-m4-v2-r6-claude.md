# M4 v2 — ROUND 6, the CLAUDE half

**Subject:** `ac56e20` on `docs/m4-round5` — the round-5 fixes (`git diff ceb5875..ac56e20`).
**Independence:** I did not read `docs/reviews/plan-m4-v2-r6-codex.md`. It had already landed as
`251f5b9` while I worked; I confirmed only that `git diff --stat ac56e20..HEAD -- scripts/ .claude/
docs/superpowers/specs/m4/` is **empty**, so every measurement below is a measurement of `ac56e20`'s
scripts. Rounds 1–5 were read.

**2 Blocking · 2 High · 2 Medium · 2 Low. NOT CONVERGED.**

Everything below was executed against real Postgres 17.6 databases built for the purpose, plus two
read-only reads of production. Every sabotage states the catalog delta it caused **before** the
verdict is quoted, because r5 shipped one that changed nothing.

---

## The one-sentence version

> **The round-5 fix put `relacl` in the digest. Production's `pg_default_acl` grants a role the
> container does not have. So `check-live-schema.py --prod --expect-present` — the plan's Step 7,
> the single instrument that certifies the production cutover — cannot pass, and will print
> "A PARTIALLY APPLIED M4 IS THE DANGEROUS STATE" over a migration that applied perfectly.**

It is the same shape r5 found and r5's own fix reproduced: the fix moved the predicate to a wider
projection without asking whether the two subjects being compared can ever agree on the wider part.

---

# BLOCKING

## B1 — `relacl`/`proacl` in the digest makes `--prod --expect-present` unsatisfiable at M4-β

### Premise (quoted)

`scripts/m4_catalog.py:86-91` — the enforcement list the round is built around:

```python
ENFORCEMENT_COLUMNS = (
    "relrowsecurity", "relforcerowsecurity", "relacl", "relpersistence", "reloptions",
    "prosecdef", "proconfig", "provolatile", "prokind", "proacl",
    …
```

`scripts/m4_catalog.py:115-119` puts `relacl` in the table digest and `:153-157` puts `proacl` in the
function digest.

The manifest those digests are compared against is derived here — `scripts/gen-m4-manifest.py:135-139`:

```python
    clone = subprocess.run(
        ["docker", "exec", "-i", CONTAINER, "sh", "-c",
         f"pg_dump -U postgres -d {source} --schema-only --no-owner --no-privileges "
         f"| psql -U postgres -d {SCRATCH} -q"],
```

`--no-privileges` drops `ALTER DEFAULT PRIVILEGES` along with everything else. So every object in the
manifest carries the ACL that Postgres assigns when **no default privileges exist**. No real database
is in that state.

### Executed evidence

**1. The local container's `postgres` database carries default privileges for `public` tables:**

```
$ … -c "select d.defaclrole::regrole, n.nspname, d.defaclobjtype, d.defaclacl from pg_default_acl …"
postgres|public|r|{postgres=arwdDxtm/postgres,anon=Dxtm/postgres,authenticated=Dxtm/postgres,service_role=Dxtm/postgres}
```

**2. Two clones of the same database, one built exactly as the generator builds it:**

```
$ pg_dump … --no-owner --no-privileges | psql -d m4_r6c_nopriv     # what the generator does
$ pg_dump … --no-owner                 | psql -d m4_r6c_withpriv   # what a real database is
$ … "select count(*) from pg_default_acl … where nspname='public' and defaclobjtype='r'"
m4_r6c_nopriv   : 0
m4_r6c_withpriv : 1
```

M4 applied to both from the same `build-m4-schema.py --quiet` output, both `rc=0`. The ACLs diverge:

```
--- m4_r6c_nopriv ---
workspaces | {postgres=arwdDxtm/postgres,service_role=arwd/postgres,authenticated=r/postgres,anon=r/postgres}
--- m4_r6c_withpriv ---
workspaces | {postgres=arwdDxtm/postgres,anon=rDxtm/postgres,authenticated=rDxtm/postgres,service_role=arwdDxtm/postgres}
```

**3. The gate, run on both:**

```
$ python3 ./scripts/check-live-schema.py --database m4_r6c_nopriv --expect-present
live schema [local container db 'm4_r6c_nopriv' — postgres@local-socket/…]: M4 is PRESENT as expected
  — checked all 161 objects, BY DEFINITION not just by name
exit=0

$ python3 ./scripts/check-live-schema.py --database m4_r6c_withpriv --expect-present

⛔ AND 8 object(s) EXIST BUT DO NOT MATCH THEIR DEFINITION —
   the name is there and the behaviour is not. A DISABLED trigger, a `create or replace`d
   function body, or a constraint weakened to `check (true)` all look like this:

      ✗ table:video_artifact_sources
      ✗ table:video_artifacts
      ✗ table:video_generations
      ✗ table:workspace_videos
      ✗ table:workspaces
      ✗ view:video_artifacts_current
      ✗ view:video_generations_collectable
      ✗ view:video_summary_current

⚠ A PARTIALLY APPLIED M4 IS THE DANGEROUS STATE: the guard triggers are what
  make the artifact tables append-only. …
exit=1
```

**4. Production is worse, and I read production to establish it.** A read-only probe through the
repo's own `psql_cmd`/`psql_env` (session `read only`, URL never in argv):

```
identity|claude_ro|postgres|on|pg_catalog
defacl|postgres|r|{postgres=arwdDxtm/postgres,anon=arwdDxtm/postgres,authenticated=arwdDxtm/postgres,service_role=arwdDxtm/postgres,claude_ro=r/postgres}
defacl|postgres|f|{postgres=X/postgres,anon=X/postgres,authenticated=X/postgres,service_role=X/postgres}
ntables|13
```

Two things follow.

* Production's default **function** ACL grants `service_role=X`, which the local one does not. The M4
  spec revokes from `public, anon, authenticated` and says nothing about `service_role`
  (`/tmp/r6c-m4.sql:70, 97, 195, 233, 578, 1226, 1398, 1635, 1674, 1713, 1738, 1816` — twelve
  functions), so on production those twelve keep `service_role=X` and the manifest's does not have it.
* Production's default **table** ACL contains **`claude_ro=r/postgres`**. `claude_ro` is a role that
  **does not exist in the container at all**. No manifest generated on any developer machine can ever
  contain it.

**5. A production-shaped database, built by installing production's measured default privileges and
then applying M4:**

```
f -> {postgres=X/postgres,anon=X/postgres,authenticated=X/postgres,service_role=X/postgres}
r -> {postgres=arwdDxtm/postgres,anon=arwdDxtm/postgres,authenticated=arwdDxtm/postgres,service_role=arwdDxtm/postgres}
M4 applied rc=0

$ python3 ./scripts/check-live-schema.py --database m4_r6c_prodshape --expect-present
⛔ AND 20 object(s) EXIST BUT DO NOT MATCH THEIR DEFINITION —
      ✗ fn:art_summary_has_no_source()          ✗ fn:corrections_hash_of(p_corrections text)
      ✗ fn:ensure_workspace_for_profile()       ✗ fn:forbid_collecting_current()
      ✗ fn:no_corrections_hash()                ✗ fn:resolve_workspace_from_playlist()
      ✗ fn:slot_kind(p_slot text)               ✗ fn:video_artifact_sources_append_only()
      ✗ fn:video_artifact_sources_insert_once() ✗ fn:video_artifacts_append_only()
      ✗ fn:video_artifacts_generation_complete()✗ fn:video_generations_freeze()
      ✗ table:video_artifact_sources … (5 tables) … ✗ view:video_summary_current (3 views)
exit=1
```

**20 is a lower bound** — this simulation could not add `claude_ro` (creating a cluster role is not
mine to do), and that grantee makes five more digests unmatchable.

### The cascade — this is not one red gate

`scripts/run-schema-assertions.sh:176-180` gates itself on the same predicate:

```bash
if ! python3 "$REPO/scripts/check-live-schema.py" --database "$DB" --expect-present >/dev/null 2>&1; then
  echo "CANNOT RUN — 0027 is not applied to database '$DB', …
```

Measured against the fully-applied `m4_r6c_withpriv`:

```
$ PGDATABASE=m4_r6c_withpriv ./scripts/run-schema-assertions.sh
exit=2
CANNOT RUN — 0027 is not applied to database 'm4_r6c_withpriv', so every assertion would be vacuous
or hard-red for the wrong reason. Treat this as NOT RUN.
```

So at M4-β: gate 8 red, gate 8's downstream assertion harness NOT RUN, both reporting a cause that is
false. `M4_PHASE=post ./scripts/check-schema-gates.sh` can never go green. That is the **fourth**
unsatisfiable milestone this plan has shipped — and the third one *introduced by the fix for the
previous one*. (Gate 7 is unaffected: `derive()` clones with `--no-privileges` in both phases, so it
stays inside the stripped world and stays green. The blast radius is exactly the gates that read a
real database.)

### Consequence, stated operationally

`docs/superpowers/plans/2026-08-25-m4-promote-the-schema-v2.md:996` is Step 7, immediately after
`supabase db push --linked`:

```bash
python3 scripts/check-live-schema.py --prod --expect-present
```

An operator running the plan literally applies an irreversible production migration, runs the one
instrument that is supposed to confirm it, and is told that **twenty objects exist but do not match
their definition** and that *"a partially applied M4 is the dangerous state … a schema with the tables
and without their guards accepts writes the design forbids."* The documented response to that is the
rollback. The gate built to prevent a bad cutover would, on its first real use, argue for undoing a
good one.

### Why five rounds did not see it

Because **nothing has ever run `--expect-present` against a database that has default privileges.**

* `gen-m4-manifest.py:137` — `--no-privileges`.
* `mutate-live-schema-check.sh:82-84` — `--no-privileges`, and every one of the 16 mutations clones
  that template.
* `gen-m4-manifest.py:238` (`--self-test`, the r5 B3 "post-phase proof") — `--no-privileges`.
* `run-schema-assertions.sh:144-146` (`--self-test`) — `--no-privileges`.
* The only polarity ever pointed at production is `--expect-absent`, which compares **symbols** and
  therefore cannot see a digest at all. I re-ran it:

```
$ python3 ./scripts/check-live-schema.py --prod --expect-absent
live schema [--prod — claude_ro@2600:1f18:…/postgres, read_only=on]: M4 is ABSENT as expected — …
exit=0
```

The gate whose entire purpose is certifying the production cutover has never been exercised, and
**cannot be exercised**, in the polarity it will be used in.

### Fix direction

Not "drop ACLs from the digest" — r5 B2's `revoke select …; grant insert to anon` case is real and
mutation 10 proves the gate catches it. Two candidates, and I would take the first:

1. **Digest the ACL M4 *asserts*, not the ACL Postgres *assembles*.** Compare the privileges the
   spec's own `grant`/`revoke` statements name, per grantee, and ignore grantees the spec never
   mentions. `has_table_privilege(grantee, rel, priv)` over the spec's grantee list is a projection
   that is invariant to `pg_default_acl` and still fails on mutation 10.
2. Derive the manifest on a baseline that carries the target's default privileges — but this cannot
   work for `claude_ro`, so it only narrows the problem.

Whichever is chosen, **the gate must be proven `--expect-present`-green against a database whose
`pg_default_acl` matches production's measured value**, or the fix is unexercised in exactly the way
this round is about.

---

## B2 — `ENFORCEMENT_COLUMNS` is an include-list assembled from r5's sabotage list; `attacl` is its missing sibling

### Premise (quoted)

`scripts/m4_catalog.py:83-91`:

```python
# ⭐ EVERY ENFORCEMENT COLUMN, ASSERTED BY THE SELF-TEST TO STILL BE IN `CATALOG_SQL`.
ENFORCEMENT_COLUMNS = (
    "relrowsecurity", "relforcerowsecurity", "relacl", "relpersistence", "reloptions",
    …
    "attnotnull", "attidentity", "attgenerated", "tgenabled",
)
```

and the column branch, `scripts/m4_catalog.py:135-138`:

```sql
select 'col:' || c.relname || '.' || a.attname || '@' || md5(
         format_type(a.atttypid, a.atttypmod) || a.attnotnull::text ||
         coalesce(pg_get_expr(d.adbin, d.adrelid), '') ||
         a.attidentity::text || a.attgenerated::text)
```

Three `pg_attribute` columns are read. `attacl` is not one of them. Column-level privileges are an
**independent and sufficient** grant path in Postgres: `INSERT` on named columns is enough to insert.

The r5 B2 list in the same file names `relacl → the table opens up`. `attacl` is the same privilege
in the adjacent catalog column. Its absence is the signature of an include-list built by enumerating
the sabotages that had already been run — which is hypothesis 1 of this round, and it is confirmed.

### Executed evidence

```
anon INSERT on video_artifacts BEFORE (table-level / column-level): false / false

$ psql -d m4_r6c_attacl -v ON_ERROR_STOP=1 <<'SQL'
grant insert (workspace_id, video_id, slot, generation_id, kind, state, blob_key) on video_artifacts to anon;
grant update (blob_key) on video_artifacts to anon;
SQL
  sabotage rc=0

anon INSERT AFTER (table-level / column-level / update): false / true / update true

attacl rows now present (the catalog column that changed):
video_artifacts.blob_key      -> {anon=aw/postgres}
video_artifacts.generation_id -> {anon=a/postgres}
video_artifacts.kind          -> {anon=a/postgres}
video_artifacts.slot          -> {anon=a/postgres}
video_artifacts.state         -> {anon=a/postgres}
video_artifacts.video_id      -> {anon=a/postgres}
video_artifacts.workspace_id  -> {anon=a/postgres}

relacl UNCHANGED (the column that IS digested):
{postgres=arwdDxtm/postgres,service_role=arwd/postgres,authenticated=r/postgres,anon=r/postgres}

  161-object catalog digest before: 2b34150cf8be92029cafd96b45a00ddd8b1c8bf5465ad6b19faa540ae717a6e7
  161-object catalog digest after : 2b34150cf8be92029cafd96b45a00ddd8b1c8bf5465ad6b19faa540ae717a6e7
  ⚠ THE DIGEST DID NOT MOVE
```

The sabotage is **not vacuous** — `has_column_privilege('anon','video_artifacts','blob_key','insert')`
went `false → true`, and seven `attacl` rows appeared. The gate:

```
$ python3 ./scripts/check-live-schema.py --database m4_r6c_attacl --expect-present
live schema […]: M4 is PRESENT as expected — checked all 161 objects, BY DEFINITION not just by name
  exit=0
```

**The contrast is the finding.** The identical grant, written table-wide, is mutation 10 and goes red:

```
$ psql -d m4_r6c_relacl -c "grant insert on video_artifacts to anon;"
$ python3 ./scripts/check-live-schema.py --database m4_r6c_relacl --expect-present
  table-level grant -> gate exit=1
```

Same privilege, same grantee, same table. One spelling is caught because someone sabotaged it in
round 5; the other is invisible because nobody did.

### Fix direction

Add `attacl` to the column branch and to `ENFORCEMENT_COLUMNS`, and add a mutation. But note that the
*method* is what failed — see the closing section. A list is a list; asking "what does this SELECT not
select?" one more time will produce a sixth answer. The mechanical version is:
`pg_attribute`, `pg_class`, `pg_proc`, `pg_policy`, `pg_index`, `pg_constraint`, `pg_trigger` each
have exactly one `*acl` column and a small set of boolean/`char` flags; a **default-deny** rule
("every `acl` and every flag column of every catalog we read is digested unless it is on a written
exclusion list with a reason") converts an unbounded search into a bounded one. The file already has
the exclusion-list habit (`m4_catalog.py:69-73`); it is the *inclusion* side that is ad hoc.

---

# HIGH

## H1 — a rewrite rule silently swallows every write, and it is not a column, it is a whole catalog

### Premise

`CATALOG_SQL` (`scripts/m4_catalog.py:114-183`) reads nine object kinds. `pg_rewrite` is not among
them. `check-live-schema.py:204` — `return manifest <= live` — means present mode deliberately ignores
extra objects, and the r5 coordinator recorded that as correct: *"a real database legitimately holds
more than M4"* (`plan-m4-v2-r5-coordinator.md:97`).

A `DO INSTEAD NOTHING` rule is an extra object that turns a table off.

### Executed evidence

```
$ psql -d m4_r6c_rule -v ON_ERROR_STOP=1 -c \
    "create rule swallow as on insert to video_artifacts do instead nothing;"
  sabotage sql rc=0
  161-object catalog digest before: 2b34150cf8be92029cafd96b45a00ddd8b1c8bf5465ad6b19faa540ae717a6e7
  161-object catalog digest after : 2b34150cf8be92029cafd96b45a00ddd8b1c8bf5465ad6b19faa540ae717a6e7
  ⚠ THE DIGEST DID NOT MOVE

swallow on video_artifacts ev_type=3 is_instead=true
relhasrules on video_artifacts: true

BEHAVIOURAL PROOF:
insert into video_artifacts (workspace_id, video_id, slot, generation_id, kind, state, blob_key)
values ('00000000-0000-0000-0000-0000000000aa','v1','s1','g1','summary','current','k1');
rows in video_artifacts after the insert: 0

$ python3 ./scripts/check-live-schema.py --database m4_r6c_rule --expect-present
live schema […]: M4 is PRESENT as expected — checked all 161 objects …
  exit=0
```

Every artifact write vanishes. The append-only guard never even runs — the rule rewrites the query
before the trigger would fire. The gate certifies the schema.

### Why this is High and not Blocking

It requires someone to create an object, which is a larger step than flipping a flag, and RLS still
governs who may attempt the write. But it is the counter-example that bounds the L3 disposition: "a
real database legitimately holds more than M4" is true of *most* extra objects and false of
`pg_rewrite` entries on M4's own tables, of `BEFORE` triggers on M4's own tables that the manifest
does not name, and of policies added to M4's tables. The disposition should be narrowed to *"extra
objects that are not attached to a manifest object"*, and `relhasrules` (or a `pg_rewrite` row count
for manifest relations) belongs in the table digest.

## H2 — `FAILS_LOUDLY` is defeated by adding a comment to the exact example that motivated it

### Premise (quoted)

`scripts/run-schema-assertions.sh:49-51`:

```bash
# The ways an assertion in this corpus can FAIL. Every real one is a `do $$ … raise exception … $$;`.
FAILS_LOUDLY='raise exception|raise_exception|[^a-z_]assert[^a-z_]'
```

and `:66-75`:

```bash
  sql=$(printf '%s\n' "$1" | grep -v '^[[:space:]]*--')
  …
  if ! printf '%s' "$sql" | grep -Eqi "$FAILS_LOUDLY"; then
```

The round-6 prompt asked whether the comment stripping happens first. **It does — and it strips only
WHOLE comment LINES.** A trailing comment, a C-style comment and a string literal all survive into
`$sql`.

### Executed evidence

```
$ printf -- '-- @RE-RUNNABLE\nselect 1; -- this would raise exception if the invariant broke\n' > trailing.sql
$ ASSERT_FILE=trailing.sql ./scripts/run-schema-assertions.sh --print-block
--- trailing: exit=0
select 1; -- this would raise exception if the invariant broke

$ printf -- '-- @RE-RUNNABLE\nselect 1; /* raise exception */\n' > cstyle.sql
--- cstyle: exit=0

$ printf -- "-- @RE-RUNNABLE\nselect 'raise exception' as note;\n" > literal.sql
--- literal: exit=0
```

`select 1;` — **the literal counter-example r5 H3 measured**, and the reason `FAILS_LOUDLY` exists —
is accepted again by appending a comment to it. This is the fifth iteration of the same syntactic
proxy (`anything` → `non-comment` → `;` → alphanumeric → `raise exception`), and the fifth is
defeated by a smaller edit than any of the previous four.

Note also what the file's own history says at `:56`: *"a marker only counts ON A COMMENT LINE, so SQL
text can never steer the selector"* — round 2's lesson, about string literals steering a match. It
was applied to the **selector** and not to the **failure-mechanism check** eight lines below. Same
commit, same file, one direction. That is r5 B1's sentence verbatim (`check-live-schema.py:173-175`).

### Consequence

`05_assert.sql` carries zero `@RE-RUNNABLE` markers today, so this is latent — but Task 8 adds them,
and at that moment the syntactic floor is the only thing standing between a marker block and
`"schema assertions: RE-RUNNABLE subset passed against the live schema"` over an empty assertion set.
The behavioural `--self-test` does **not** cover it: it proves RED/GREEN for two *synthetic* blocks it
writes itself (`:153-160`), never for the block the harness will actually select from `05_assert.sql`.

### Fix direction

Two options; the first is a patch and the second is the property.

1. Strip comments properly (`sed -E 's|--.*$||; s|/\*[^*]*\*/||g'`) and strip single-quoted literals
   before matching. This is a sixth notch on the same proxy.
2. **Ask the database.** The harness already builds an M4 scratch database in `--self-test`. Run the
   *real selected block* against it twice: once as-is (must exit 0) and once with the corpus seeded so
   the invariant is violated (must exit 1). That is the same move that made r5 H3's fix structural
   instead of syntactic, applied to the real block instead of a synthetic one — and it needs the
   corpus to have a "violate this" switch, which is the actual work.

---

# MEDIUM

## M1 — `has_m4()`'s fail-closed guarantee is stated wider than it is, and the real protection is accidental

### Premise (quoted)

`scripts/gen-m4-manifest.py:46`:

```
⚠ It still fails closed if the rollback leaves M4 behind — an incomplete rollback would silently
shrink the manifest, which is the same class of defect one level down.
```

`:111-117`:

```python
M4_MARKERS = ("table:workspaces", "table:video_generations")

def has_m4(catalog: set[str]) -> bool:
    """Does this catalog carry M4? Matched by NAME — objects now carry a digest. PURE."""
```

Two markers, both tables. Everything else M4 creates can survive and `has_m4` returns `False`.

### Executed evidence

A rollback with four `drop` lines commented out, applied to a real M4 database:

```
maimed rollback applied, rc = 0

M4 objects STILL PRESENT after the maimed rollback: 4
    fn:corrections_hash_of(p_corrections text)
    fn:no_corrections_hash()
    fn:slot_kind(p_slot text)
    type:artifact_kind

g.has_m4(catalog)  ->  False
M4_MARKERS = ('table:workspaces', 'table:video_generations')
```

The predicate certifies as pre-M4 a database holding four M4 objects, including the enum every
artifact column is typed on.

**The manifest did not shrink, and the reason is not the guard.** The generator refused:

```
generator REFUSED: the schema did not apply: ERROR:  function "no_corrections_hash" already exists
with same argument types
```

The M4 schema contains **no** `create or replace` and **no** `if not exists`
(`grep -nEi "create (or replace )?(function|view|table|index|trigger)|if not exists" /tmp/r6c-m4.sql`
— 0 hits for either). Re-applying it over any survivor is a hard error. That non-idempotency is what
fails closed; `has_m4` never fires. The day someone writes `create or replace function` for a guard —
the most natural edit in this file — the stated guarantee becomes the only one, and it is a
two-table probe.

**And the correct predicate is already in the repo.** On the same database:

```
$ python3 ./scripts/check-live-schema.py --database m4_r6c_maimed --expect-absent
FAILED — expected M4 ABSENT; 4 of 161 objects are SURVIVING:
  3 functions:
      ✗ fn:corrections_hash_of(p_corrections text)@afa6f206…
      ✗ fn:no_corrections_hash()@51ec59ea…
      ✗ fn:slot_kind(p_slot text)@5cdab623…
  1 type:
      ✗ type:artifact_kind@96f01a3a…
exit=1
```

`survivors()` answers "does this database still have M4?" exactly right, over all 161 objects.
`gen-m4-manifest.py` carries a second, weaker definition of the same question and uses it at the point
where a wrong answer silently shrinks the trust root. That is `check-vocabulary-collisions.py`'s own
subject — *two mechanisms for one concern* — and it is the same shape as the `read_only_url`
duplication this round fixed (`m4_catalog.py:204-212`), in the file that fixed it.

**Fix:** `has_m4(before)` should be `bool(survivors(before, committed_manifest))`, or the module
docstring's claim must be narrowed to what two markers can support.

## M2 — the mutation harness cannot express B1, and its own header asks that question

### Premise (quoted)

`scripts/mutate-live-schema-check.sh:16-26`:

```
# ⭐ WHAT EACH GENERATION OF THIS HARNESS COULD NOT EXPRESS — the defect keeps moving one layer out:
#   r3  it could only DROP things …
#   r4  it could only sabotage PRESENT state …
#   r5  it could only express DEFINITIONS …
# So the question this file has to keep answering is not "does the gate catch my mutation?" but
# **"what kind of defect can this harness not currently write down?"**
```

The r6 answer is: **a database that has default privileges.** `:82-84`:

```bash
if ! docker exec -i "$CONTAINER" sh -c \
      "pg_dump -U postgres -d postgres --schema-only --no-owner --no-privileges | psql -U postgres -d $TPL -q" \
```

Every mutation clones `$TPL`, and `$TPL` is privilege-stripped — the same construction the generator
uses. **The fixture and the subject share one blind spot**, so a 16/16 green report is structurally
incapable of noticing that the manifest's ACLs match nothing real.

### Executed evidence

I ran the harness in an isolated namespace (`PREFIX` rewritten to `m4_r6c_mut`, so it could not
collide with the concurrent reviewer):

```
exit=0
  ✓ empty db -> --expect-absent passes
  ✓ M4 applied -> --expect-present passes (the CONTROL for everything below)
  ✓ post-cascade residue -> --expect-absent FAILS (140/161 objects survive)
  … 16 of 16 …
✅ every mutation caught — check-live-schema.py is load-bearing
```

All 16 reproduce. And the CONTROL on line 97-98 — *"M4 applied → `--expect-present` passes"* — is
precisely the assertion B1 falsifies on any real database. The harness's control is green because its
control database is not shaped like the thing being certified.

**Fix:** one mutation whose template carries production's measured `pg_default_acl`, whose expected
result is **pass**. It is a control, not a sabotage, and it is the one the suite lacks.

---

# LOW

## L1 — every harness uses a fixed scratch database name and drops it with `(force)`

`gen-m4-manifest.py:69` `SCRATCH = "m4_manifest_gen"`; `:212` `m4db = "m4_manifest_gen_post"`;
`run-schema-assertions.sh:97` `SCRATCH="m4_assert_selftest"`; `mutate-live-schema-check.sh:30`
`PREFIX="m4_gate_mut"`.

`gen-m4-manifest.py:131` calls `drop_scratch()` unconditionally at the top of `derive()`, and
`drop_scratch` issues `drop database if exists m4_manifest_gen (force);` — `(force)` terminates other
sessions' connections. `mutate-live-schema-check.sh:39-44`'s `cleanup()` drops **every** database
matching `m4_gate_mut%` on `EXIT`.

Two concurrent runs of gate 7, or of the mutation harness, destroy each other's databases mid-read and
can produce either a spurious CANNOT RUN or — worse — a mutation reported as caught for the wrong
reason. This is not hypothetical: this review round runs two reviewers against one container. I
avoided it by rewriting the names into an `m4_r6c_` namespace, which is why the harness output above
came from a copy rather than from `./scripts/mutate-live-schema-check.sh`.

**Fix:** suffix with `$$`/`os.getpid()`, and scope the mutation harness's `cleanup` to the names this
process created rather than a `LIKE` sweep.

## L2 — the manifest loader's comment rule and its header regexes disagree about leading whitespace

`check-live-schema.py:126`:

```python
    objs = {ln.strip() for ln in text.splitlines() if ln.strip() and not ln.startswith("#")}
```

Content is measured after `strip()`, comment-ness before it. An indented `#` line is admitted as an
object; conversely `re.search(r"^#\s*objects:", text, re.M)` at `:132-133` cannot see an indented
header. Both directions land in the same place — count/digest mismatch, `ValueError`, exit 2 — so this
fails closed and costs only a misleading message ("TRUNCATED or partially written" for a file that is
merely indented). Worth one line because this parser is the trust root.

---

# VERIFIED AND NOT DEFECTS — do not re-run these in round 7

| # | Hypothesis | What I measured | Verdict |
|---|---|---|---|
| 1 | `alter database … set session_replication_role='replica'` would disable every trigger and FK with the digest byte-identical | `ERROR: permission denied to set parameter "session_replication_role"` as the `postgres` role; `pg_db_role_setting` empty afterwards; catalog fingerprint unchanged **because the sabotage never happened** | **Not reachable.** Supabase's `postgres` is not superuser, locally or on prod. Recorded so nobody re-derives it |
| 2 | `survivors()` matches on `symbol_of`, so a legitimate non-M4 object could make `--expect-absent` cry wolf | `manifest symbols ∩ pre-M4 live symbols` on a full pre-M4 clone = **0** of 161. `--expect-absent` exit 0 on that clone and on production | **No false positive today.** ⚠ Latent: the manifest is `after EXCEPT before`, so if M4 ever *modifies* an existing object's digest (e.g. `alter table videos enable row level security`), that object enters the manifest and its symbol then matches the pre-M4 original forever. Nothing enforces "M4 only creates" |
| 3a | `set session characteristics as transaction read only` breaks `gen-m4-manifest.py`, which writes to the database it reads | Writes go through separate `psql` invocations (`gen-m4-manifest.py:97-104`, `:177-180`); `read_catalog` never shares a session with them. `--check` and the post-phase self-test both derive 161 objects, identical to the committed manifest | Not a defect |
| 3b | `search_path = pg_catalog` / the read-only session get lost on the pooler, so `--prod` renders identities differently | Prod URL is Supavisor on **port 5432 (session mode)**. The gate's own identity line proves both settings survived from an earlier statement to a later one in the same invocation: `identity\|claude_ro\|postgres\|on\|pg_catalog` | Not a defect |
| 3c | `pg_get_viewdef` / `pg_get_constraintdef` render differently on prod vs the container | `server_version` = **17.6** on both | Not a defect |
| 5 | A partially applied or erroring rollback produces a SHRUNK manifest that `--check` accepts | The rollback is one transaction (`rollback_0027…sql:41,117`) run under `ON_ERROR_STOP=1`, so partial application cannot commit; and the M4 schema has zero `create or replace` / `if not exists`, so any survivor makes the re-apply a hard error (measured). `--check` compares the rendered FILE, so a shrunk set is exit 1, not a pass | Not a defect **as an accident** — see M1 for the part that is |
| 6a | `run-schema-assertions.sh --self-test` leaves databases behind or collides with the mutation harness | `SCRATCH="m4_assert_selftest"` vs `PREFIX="m4_gate_mut"` — different namespaces; `trap cleanup_st EXIT` drops it | No collision between *those two*; the general name problem is L1 |
| 6b | `FAILS_LOUDLY` has a false NEGATIVE (rejects a real assertion) | `select 1/0;`, `perform 1/0` inside a `do $$ … $$`, and a `case`-expression divide-by-zero are all **rejected** (exit 2, CANNOT RUN) | Fail-closed and documented at `:37`. Not a defect, but note the asymmetry against H2: real failure mechanisms are refused while a fake one in a comment is accepted |
| 7 | Importing `read_only_url` from `m4_catalog` changed `check-anon-exposure.py`'s behaviour | Old regex vs new, on the real `.env.local`: **identical**. `--self-test` 22/22 exit 0; `--local` exit 0; the **`--prod` path** (the one that changed most — argv → environment) exit 0, `12 SECURITY DEFINER function(s) in public, 10 anon-EXECUTable` | Not a defect. `psql_cmd`'s remote form works for this caller |
| 8 | The coordinator's claim that gates 3 and 4 are pre-existing | `check-guard-coverage.py` exit 1, **10 problems**, naming `video_artifacts_paid_uq`; `check-sentinel-meanings.py` exit 1, **5 problems**, naming stale `reserved_by` / `source_generation_id`. Neither script nor any `schema/` spec file appears in `git diff --name-only ceb5875..ac56e20`; both last changed in `342ac2e` (PR #118, 2026-08-19) | **Claim verified independently.** Pre-existing and unrelated |
| — | The round-5 artifacts reproduce | `check-live-schema.py --self-test` **53/53** exit 0 · isolated mutation harness **16/16** exit 0 · gate 7 equivalent: 161 objects, object sets identical, **rendered file identical** · post-phase self-test: pre 161 = post 161 · `--expect-absent` on the shared local `postgres` exit 0 | All reproduce |

---

## The pattern this round adds

The r5 coordinator closed with:

> *"The two fixes in this round that are not of that shape both replaced a proxy with the property
> itself … So the question that finds the next one is not 'is this check correct?' but 'what would I
> have to observe for this check to be lying, and can I make the check observe that instead?'"*

**That question was asked of the check and not of the fixture.** Both B1 and B2 are cases where the
check was made wider and the thing it is compared against was not moved with it:

* B2 — the digest grew to cover `relacl`; the *sabotage catalogue* did not grow to cover `attacl`, so
  the wider check is exactly as wide as the list of attacks someone had already written down.
* B1 — the digest grew to cover ACLs; the *baseline* stayed a `--no-privileges` clone, so the wider
  check compares an ACL against an ACL that no deployed database has.

So the generalisation is one notch out from r5's:

> **A predicate and the artefact it is compared against are two things, and a fix that widens one
> without widening the other produces a check that is simultaneously stricter and less true.** Every
> round here has widened the predicate. Nothing has ever widened the *baseline*: it has been a
> `pg_dump --no-privileges` clone since the manifest was invented, through five rounds and four
> different definitions of what an object *is*.
>
> The falsifier that would have caught both, and costs one database: **run the gate, in the polarity
> the milestone will use it in, against a database built the way the target is built — not the way
> the manifest is built.** If the two constructions differ anywhere, that difference *is* the
> untested surface, and it does not matter how many mutations pass on the wrong side of it.

⚠ **Phase 6 (architecture review) fired at round 4 and has still not run.** This is round 6.

---

## VERDICT

**NOT CONVERGED at round 6.** 2 Blocking, 2 High, 2 Medium, 2 Low.

⛔ **B1 must be fixed before M4-β, not after.** It is not a red gate to be worked around at cutover
time: it makes the plan's Step 7 argue for rolling back a successful production migration, and it
takes gate 8 and the assertion harness down with it.

⛔ Merging stays a human gate. Applying M4-β to production is a second one.

---

## Hygiene

**Databases created (all prefixed `m4_r6c_`, all dropped):**
`m4_r6c_nopriv`, `m4_r6c_withpriv`, `m4_r6c_tpl`, `m4_r6c_pre`, `m4_r6c_srr`, `m4_r6c_attacl`,
`m4_r6c_relacl`, `m4_r6c_rule`, `m4_r6c_maimed`, `m4_r6c_prodshape`, `m4_r6c_post`, `m4_r6c_gen`,
`m4_r6c_gen_post`, and the `m4_r6c_mut*` set created by the isolated mutation harness.

```
$ select datname from pg_database where datname like 'm4_%' order by 1;
(no rows)
```

**The shared `postgres` database is untouched and still PRE-M4:**

```
public tables: 13
workspaces/video_generations present: 0
```

**Repository:** `git status --porcelain` empty apart from this file. No tracked file was modified.

**Production:** two **read-only** reads only — a `pg_default_acl`/`relacl`/`server_version` probe and
`check-live-schema.py --prod --expect-absent`, plus `check-anon-exposure.py --prod`. All ran with
`set session characteristics as transaction read only` (`transaction_read_only = on`, printed above);
nothing was written. The database URL never appeared in `argv`.
