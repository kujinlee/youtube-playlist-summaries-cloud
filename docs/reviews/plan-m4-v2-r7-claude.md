# M4 v2 — ROUND 7, the CLAUDE half

Subject: the round-6 fixes, merged as `74f450b` on `master` (PR #154). Diff reviewed: `d6688d8..74f450b`.

Everything below was executed against throwaway databases cloned from a **production-shaped** base
(`pg_dump --schema-only --no-owner`, privileges retained, so `pg_default_acl` for `public` survives).
Baseline was proven GREEN before any sabotage:

```
python3 scripts/check-live-schema.py --database m4_r7c_tpl --expect-present
gate_baseline_exit=0
live schema [local container db 'm4_r7c_tpl' — postgres@local-socket/m4_r7c_tpl, read_only=on]:
M4 is PRESENT as expected — checked all 161 objects, BY DEFINITION not just by name
```

**Counts: 2 Blocking · 1 High · 4 Medium · 5 Low. NOT CONVERGED.**

The headline: **HYPOTHESIS 1 is clean and I could not break it** — but round 6 did do it again, in the
place round 6 itself named. Both Blockings are the same shape as r5 B2 and r6 B: *a catalog property
that decides what the body does, excluded from the digest with a written reason that is measurably
false.*

---

## ⛔ Blocking 1 — `proargdefaults` is excluded with a FALSE reason, and `record_artifact` has SEVEN defaults

**Premise.** `scripts/check-catalog-coverage.py:112-115`:

```python
(r"^(prosupport|probin|proargdefaults)$",
 "a planner support function, a C-language shared-object path, and the internal node tree of "
 "argument defaults. M4 ships no C functions; a change to a default's VALUE changes the "
 "identity arguments, which are the manifest key"),
```

The load-bearing clause is *"a change to a default's VALUE changes the identity arguments"*. It is false.
`scripts/m4_catalog.py:290` keys functions on `pg_get_function_identity_arguments(p.oid)`, which renders
**types only** — no names, no defaults.

**Executed — the property itself:**

```
create function public.pf(a int, b int default 1) ...
  pg_get_function_identity_arguments -> a integer, b integer
create or replace function public.pf(a int, b int default 99) ...
  pg_get_function_identity_arguments -> a integer, b integer     <- UNCHANGED
  pg_get_function_arguments          -> a integer, b integer DEFAULT 99
  select pf(1)                       -> 100                      <- BEHAVIOUR CHANGED
```

**Executed — on M4's own paid write path.** `record_artifact` carries **7 defaulted parameters**:

```
proname         | pronargs | pronargdefaults
record_artifact |    13    |        7
p_source_generation_id text DEFAULT NULL::text, p_start_sec integer DEFAULT NULL::integer,
p_end_sec integer DEFAULT NULL::integer, p_md_hash text DEFAULT NULL::text,
p_card jsonb DEFAULT NULL::jsonb, p_doc_version_major integer DEFAULT NULL::integer,
p_produced_at timestamptz DEFAULT NULL::timestamptz
```

**The sabotage MOVED THE CATALOG** (this is checked first, per the round-5 vacuous-mutation lesson) —
`create or replace` of the function with `prosrc` byte-identical and exactly one default changed:

```
m4_r7c_tpl       proargdefaults=62400626b984851604f80f74f9243489  prosrc=22532474b1f5f5e097d36ac091477099
m4_r7c_defaults  proargdefaults=2db5f71fc86f2c4054f3815a7d61ddfc  prosrc=22532474b1f5f5e097d36ac091477099
identity_args IDENTICAL in both
```

**The gate:**

```
python3 scripts/check-live-schema.py --database m4_r7c_defaults --expect-present
gate_after_default_mutation_exit=0
M4 is PRESENT as expected — checked all 161 objects, BY DEFINITION not just by name
```

**Consequence, in observable units — two shapes, both measured.**

*(a) The paid write records a different row.* Same call, same arguments, on the two databases:

```
-- m4_r7c_tpl       Failing row contains (…, complete, null, null,  2026-08-26 …)
-- m4_r7c_defaults  Failing row contains (…, complete, null, 7,     2026-08-26 …)
                                                              ^ p_doc_version_major
CONTEXT: insert into public.video_generations (…, doc_version_major, produced_at) …
         PL/pgSQL function public.record_artifact(…) line 83
```

`doc_version_major` is the **first** ordering key of `video_summary_current`
(`ORDER BY … g.doc_version_major DESC NULLS LAST, …`), i.e. it decides which paid generation is
current. It is also constrained: `gen_major_is_summary_only` requires it to be NULL for every
non-summary kind, so a non-NULL default makes **every `dig` / `digDeeper` / `model` / `render`
recording raise** — paid work completes, the recording fails, the money is gone.

*(b) Completely silent.* Mutating `p_produced_at`'s default instead — `NULL` → `'2000-01-01'`, where
the body does `coalesce(p_produced_at, now())` — the same call succeeds on both and writes different
data:

```
########## m4_r7c_tpl ##########      recorded    gen-9|2026-08-26 04:00:55.28632+00
########## m4_r7c_prodat ##########   recorded    gen-9|2000-01-01 00:00:00+00
gate_exit=0   M4 is PRESENT as expected — checked all 161 objects
```

`produced_at DESC NULLS LAST` is the third currency key. No error, no gate.

**Why this is round 6 repeating itself.** r6's own fix added `proisstrict` because *"a function body
can stop executing for NULL-bearing calls without any manifest digest change"*. An argument default
**is what makes a call NULL-bearing**. The two live one line apart in `pg_proc` and one was added
while the other was excused with a false sentence. `check-catalog-coverage.py:29-31` predicts this
exactly: *"It cannot prove an excluded column is correctly excluded — a wrong reason here is a real
defect that this script will happily report as green."* This is that defect.

**Fix shape.** Digest `pg_get_function_arguments(p.oid)` (which renders defaults) alongside the
identity arguments, or digest `pg_get_expr`-rendered defaults; delete the false clause; add a
mutation. `pg_get_functiondef` would cover it in one string but also re-imports the ACL text r6 B1
removed, so prefer `pg_get_function_arguments`.

---

## ⛔ Blocking 2 — `REL_PRIVS` omits TRUNCATE, and the ONE written fallback covers none of the M4 tables

**Premise.** `scripts/m4_catalog.py:153-155`:

```python
REL_GRANTEES = ("public", "anon", "authenticated", "service_role")
FN_GRANTEES  = ("public", "anon", "authenticated")
REL_PRIVS    = ("SELECT", "INSERT", "UPDATE", "DELETE")
```

and the justification at `scripts/m4_catalog.py:140-144`:

```
#     (anon TRUNCATE/REFERENCES/TRIGGER/MAINTAIN      -                 Dxtm     ✗ diverge — excluded)
#
# The privileges that diverge are exactly the ones the M4 spec never mentions, and they are already
# covered by `check-anon-exposure.py`, which ratchets them against a recorded per-environment
# baseline — the right home, …
```

**Both halves of that sentence are false.**

*"the M4 spec never mentions"* — the spec mentions TRUNCATE at length, and names it as the reason the
revoke exists. `docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema/04_artifacts.sql:646-655`:

```
-- ⚠ ROUND 6 H4 — REVOKE FIRST. MEASURED: `anon` TRUNCATEd this table to 0 rows.
-- … TRUNCATE fires neither RLS nor a ROW trigger — so it walks straight past both the policy
-- below and the append-only trigger, which is this design's central invariant.
revoke all on video_artifacts from public, anon, authenticated, service_role;
```

*"already covered by check-anon-exposure.py"* — `scripts/check-anon-exposure.py:67-68`:

```python
MONEY_TABLES = ("spend_ledger", "ledger_audit", "serve_owner_budget",
                "serve_model_charge", "guardrail_config")
```

**None of the five M4 tables is in it.** RULE 2 (the TRUNCATE ratchet) reads only those five; RULE 1
reads `security definer` functions. Nothing in the repo ratchets TRUNCATE on `video_artifacts`.

**Executed.** `grant truncate on public.video_artifacts, public.video_artifact_sources to anon, authenticated;`

```
relacl BEFORE: {postgres=arwdDxtm/postgres,service_role=arwd/postgres,authenticated=r/postgres,anon=r/postgres}
relacl AFTER : {postgres=arwdDxtm/postgres,service_role=arwd/postgres,authenticated=rD/postgres,anon=rD/postgres}

python3 scripts/check-live-schema.py --database m4_r7c_h2trunc --expect-present
GATE_EXIT=0
M4 is PRESENT as expected — checked all 161 objects, BY DEFINITION not just by name
```

and the privilege is real:

```
rows before|1
set role anon;  ->  anon
truncate public.video_artifacts, public.video_artifact_sources;  ->  TRUNCATE TABLE
rows after anon TRUNCATE|0

-- the same role, the verb the digest DOES cover:
set role anon; delete from public.video_artifacts;
ERROR:  permission denied for table video_artifacts
```

**Consequence.** The anonymous role empties the table that decides which paid render is current —
past RLS, past the append-only trigger — and the live-catalog gate reports 161/161 PRESENT, exit 0.
The digest covers the four verbs that are already refused and not the one that is not.

**Why this is reachable, not theoretical.** `check-anon-exposure.py:16-18` records that this repo's
platform runs `grant all on all tables in schema public`, and that 26 of 30 prod functions arrived
anon-executable that way. Production's default ACL, measured read-only today, is
`postgres|public|r → {…, anon=arwdDxtm, authenticated=arwdDxtm, service_role=arwdDxtm, claude_ro=r}`.
A single `grant all` re-run after M4-β restores anon's `D` and nothing goes red.

**Fix shape.** Add `TRUNCATE` (and, cheaply, `REFERENCES`/`TRIGGER`) to `REL_PRIVS` — they are
`has_table_privilege` calls, environment-invariant in exactly the way `SELECT` is, because M4
explicitly revokes them. Or add the five M4 tables to `MONEY_TABLES` and make the m4_catalog comment
true. Do not leave the comment asserting a coverage that does not exist.

---

## High 1 — a grantee outside `REL_GRANTEES` is invisible, and production really has a fifth one

**Premise.** `REL_GRANTEES` is four hand-chosen names (`m4_catalog.py:153`). `_guard()`
(`m4_catalog.py:178-187`) makes a *missing* role loud; nothing makes an *extra* role visible.

**Executed.**

```
create role m4_r7c_ro login;
grant select, insert, update, delete on public.video_artifacts to m4_r7c_ro;

relacl: {postgres=arwdDxtm/postgres,service_role=arwd/postgres,authenticated=r/postgres,
         anon=r/postgres,m4_r7c_ro=arwd/postgres}

python3 scripts/check-live-schema.py --database m4_r7c_h2role --expect-present
GATE_EXIT=0   M4 is PRESENT as expected — checked all 161 objects
```

**This is not hypothetical.** Measured against production, read-only, today:

```
defacl|postgres|r|{postgres=arwdDxtm/postgres,anon=arwdDxtm/postgres,authenticated=arwdDxtm/postgres,
                   service_role=arwdDxtm/postgres,claude_ro=r/postgres}
roles|anon,authenticated,claude_ro,postgres,service_role
acl|videos|{…,claude_ro=r/postgres}
```

Every table `postgres` creates in `public` on production gets `claude_ro` in its ACL automatically,
and M4's revoke list does not name it — so post-M4 every one of the five M4 tables will carry a
grantee the digest structurally cannot see. Today that grantee holds `r` and that is correct; the
point is that it holding `arwd` tomorrow would be equally invisible.

**Honest bound, because the prompt asked for the judgement.** For row verbs the damage is bounded by
RLS — executed: the extra role saw `0` rows through `force row level security` with no policy naming
it, and its INSERT was refused. So this is *closer* to "the unavoidable price of environment
invariance (r6 B1)" than Blocking 2 is. **But the price is nowhere stated.** The only sentence in the
codebase that addresses what falls outside the projection is the one quoted in Blocking 2, and it is
false. A reader auditing `REL_GRANTEES` today is told the residue is covered elsewhere; it is not.
That, not the RLS-bounded write, is why this is High: the gap is undocumented *and* misdocumented.

**Fix shape.** State the bound where `REL_GRANTEES` is defined — "a grant to any role not in this
tuple is invisible to this digest, and the compensating control is X" — and make X exist. The cheap X:
digest the **count** of grantees outside the tuple (environment-invariant only if production's
default ACL is stable, so probably better as a per-environment ratchet in `check-anon-exposure.py`).

---

## Medium 1 — nothing asserts the application's own credential still works after M4

HYPOTHESIS 1 was the highest-stakes hypothesis and **the schema is correct**. I could not break it.
But the proof below is the first time it has been executed, and nothing in the repo re-runs it.

The revokes now strip `service_role` down to `arwd` on all five tables (measured post-M4:
`service_role=arwd/postgres`), removing `D` TRUNCATE, `x` REFERENCES, `t` TRIGGER, `m` MAINTAIN that
production's default ACL hands out. Executed as `set role service_role` on a production-shaped M4
database — the four writes M4 makes riskiest, because M4 adds `workspace_id uuid NOT NULL references
workspaces(id)` plus six `BEFORE` triggers to the three **live** tables the app writes every day:

```
insert into public.playlists …  ->  id | workspace_id  (1 row)   INSERT 0 1
insert into public.videos    …  ->  vid001 | 1111…      INSERT 0 1
   workspace_videos rows created by the definer trigger | 1
insert into public.jobs      …  ->  workspace_id 1111…  INSERT 0 1
update public.videos set data=… ->  UPDATE 1
update public.videos set playlist_id=… (fires the re-derivation) -> UPDATE 1
delete from public.jobs / public.videos -> DELETE 1 / DELETE 1
ALL LIVE WRITES SUCCEEDED AS service_role
```

Sub-questions the prompt named, all executed and all clean:

* **Sequences** — M4 creates none. `relkind='S'` in `public`: 1 before, 1 after. No `serial`, no
  `identity` (`attidentity` is digested anyway).
* **REFERENCES / TRIGGER** — moot for this credential: `create table public.sr_fk_probe (…)` as
  `service_role` fails at `permission denied for schema public`. It cannot create objects at all.
* **EXECUTE on trigger functions** — `service_role` has **no** EXECUTE on any of the 12 definer
  functions (`proacl = {postgres=X/postgres}`), and every trigger still fired. Postgres does not
  check EXECUTE when a trigger fires. `record_artifact` is the one function granted to it (`t`).
* **The views** — all three are `{security_invoker=true}`; `service_role` selected all three
  successfully, including `video_generations_collectable` (granted to `service_role` only), which is
  what the GC path needs.

**The finding is the absence, not a defect:** the revoke lists are hand-maintained, and the mutation
harness's mutation 19 proves *the gate* survives a production-shaped database, never that *the
application's credential* survives the schema. One more name on one revoke line, or one missing
`grant`, ships as a production outage on the first write with every gate green.

**Fix shape.** A small `set role service_role` smoke block in `05_assert.sql` (or a Task-9 step)
performing exactly the six statements above. It is ten lines and it is the only thing that would have
gone red if r6 had got the revoke wrong.

---

## Medium 2 — `check-catalog-coverage.py`'s "DIGESTED" means "the name appears in the query text"

**Premise.** `scripts/check-catalog-coverage.py:135-137`:

```python
def digested_columns(sql: str = CATALOG_SQL) -> set[str]:
    """Every catalog column name that literally appears in the digest query. PURE."""
    return set(re.findall(r"\b[a-z]{2,}[a-z_]*\b", sql))
```

`classify()` checks `column in digested` **first**, so any column whose name appears anywhere in
`CATALOG_SQL` — in a `WHERE` clause, a `JOIN`, a select-list prefix, or a comment — is reported
DIGESTED without its value being in any `md5()`.

**Executed.** I extracted the nine `md5(...)` argument regions by paren depth and re-classified the
203 enumerated columns:

```
md5() regions found: 9
Columns reported DIGESTED that are NOT inside any md5() argument:  21
  pg_class.relkind        -> would be UNCLASSIFIED
  pg_attribute.attnum     -> would be UNCLASSIFIED
  (+19 that would be EXCLUDED anyway: relname, relnamespace, proname, pronamespace, prolang,
   attrelid, attname, attisdropped, indexrelid, polname, conname, connamespace, conrelid,
   tgrelid, tgname, tgisinternal, typname, typnamespace, typtype)
```

**The comment sub-hypothesis does NOT fire today** — I stripped `--` comments from `CATALOG_SQL` and
re-classified: **zero** columns changed verdict. So no column is currently excused by prose alone.

**Consequence.** Two columns (`relkind`, `attnum`) are passed by the oracle rather than by the
EXCLUDED list, so no human ever wrote down why they are safe. Both happen to be genuine filters that
cannot change enforcement, so there is no live gap — but the script exists precisely because
*"the list was never the mechanism"* (its own line 11), and its replacement oracle over-counts by
10%. A future Postgres column whose name collides with a filter token or an alias would be silently
classified DIGESTED. The higher-order point is Blocking 1: the real hole is in the **reasons**, which
this script explicitly says it cannot check, and three of them are wrong (B1, L2, L3).

**Fix shape.** Compute `digested_columns` over the `md5()` regions only, then add `relkind`, `attnum`
to a `FILTER` exclusion with the reason.

---

## Medium 3 — the plan's mutation and self-test counts are round 5's, not round 6's

`docs/superpowers/plans/2026-08-25-m4-promote-the-schema-v2.md:396`:

> **Proven, not asserted** — `scripts/mutate-live-schema-check.sh`, **16/16 caught**:

and `:415`:

> Self-test **53 cases**, including every enforcement column and both r5 B1 survivor shapes.

**Executed:**

```
./scripts/mutate-live-schema-check.sh    MUTATION_HARNESS_EXIT=0
  mutations RUN by the harness: 20        checks reported (✓ lines): 21
  ✅ every mutation caught — check-live-schema.py is load-bearing

python3 scripts/check-live-schema.py --self-test    67/67 self-test cases passed
```

Round 6 added mutations 16-20 (STRICT, column-level grant, rewrite rule, production-shaped control,
renamed survivor) to the harness and left the plan's table at 1-15 — which also still contains a
duplicated row number (`| 2 | drop table … cascade residue |` appears after row 15). The plan is the
artifact a human ticks the gates off against; an undercount there is the failure mode the plan's own
`⟳ r5 M (codex)` note describes for the gate list ("a reader ticking nine items off a script that
prints eight resolves the difference by assuming they missed one").

---

## Medium 4 — the roadmap STATUS block is stale in the commit that added it

`docs/superpowers/plans/2026-08-22-append-only-generations-roadmap.md:221-224`, added by `74f450b`:

```
> | Open | branch `docs/m4-round5`, commit `ac56e20` — the round-5 fixes |
> | Review rounds | **5, none converged.** ⚠ Phase 6 fired at round 4 and has **not run** |
> | Next | round 6 on the round-5 fixes, then Tasks 1-2 …
```

The same commit merges `docs/reviews/plan-m4-v2-r6-codex.md` and `-r6-claude.md` and the round-6
fixes. So the block says "next: round 6" in the commit that completed round 6, points "Open" at a
branch that is merged, and lists "Merged so far: #150 · #152 · #153" without #154. `dev-process.md`
makes the roadmap the compaction-proof source of truth and requires the status line to be updated at
the milestone boundary; this one was written one round behind at birth.

**Also worth a decision, not a fix:** the block says *"Phase 6 fired at round 4 and has not run."*
This is round **7**. Three further rounds have gone by, each finding that the previous round's fix
was the defect, which is the exact trigger `dev-process.md` says Phase 6 exists for.

---

## Low

**L1 — the hook says EIGHT gates; the runner prints nine.** `.claude/hooks/check-schema-gates.sh:51`
still reads `║  EIGHT gates. 1-6 rebuild the schema from the SPEC FILES … 7-8 read a LIVE DATABASE`,
while `scripts/check-schema-gates.sh` was renumbered to `1/9 … 9/9` in the same commit. Executed:
`./scripts/check-schema-gates.sh` prints `═══ 9/9 live catalog matches M4_PHASE=pre ═══`. The
runner's own section comment `scripts/check-schema-gates.sh:83` also still says `# 8. Does the
DEPLOYED catalog match` above the `9/9` invocation. One-site fix, identical sibling one file away —
the shape `04_artifacts.sql:626` calls "the habit that produced B1".

**L2 — the `attmissingval` exclusion reason is false.** `check-catalog-coverage.py:93-96` says
`attmissingval` "is the value existing rows read for a column added with a default, which
pg_get_expr on the default already covers". Executed:

```
alter table t add column c text default 'FASTDEFAULT';
alter table t alter column c drop default;
attmissingval still present: {FASTDEFAULT}  |  pg_get_expr(default) = <none>
existing row reads: FASTDEFAULT
new row reads: <null>
```

`pg_get_expr` does not cover it. No live gap — M4 adds `workspace_id` to `videos`/`playlists`/`jobs`
**without** a default, so no missing value exists — but it is a wrong reason over a set that is
empty today and need not stay empty.

**L3 — the `indisreplident` exclusion reason is false.** `check-catalog-coverage.py:108-111` says
replica identity and clustering "affect logical replication and row order on disk, **neither of which
can admit or reject a write**". Executed:

```
alter table r replica identity nothing;  create publication p_test for table r;
update r set v='x';   ERROR: cannot update table "r" because it does not have a replica identity and publishes updates
delete from r;        ERROR: cannot delete from table "r" because it does not have a replica identity and publishes deletes
```

The generalisation is wrong. Live exposure is nil today: `supabase_realtime` has `puballtables=f`
and no M4 table is in it, and all M4 tables are `relreplident='d'`, which **is** digested. Rewrite
the reason to say *that* rather than the false general claim.

**L4 — two EXCLUDED entries describe columns they never classify.** `relispartition` sits in the
"a FILTER, not a property: CATALOG_SQL's WHERE clauses use these" rule
(`check-catalog-coverage.py:88-90`) but is actually **digested** (`c.relispartition::text` in the
table branch), and appears in no `WHERE`. `polroles` sits in the "rendered in full by pg_get_indexdef /
pg_get_constraintdef / pg_get_triggerdef / pg_get_expr" rule (`:69-74`) but is rendered by **none**
of those — it is covered by the policy branch's own `string_agg(r.rolname …)`. Both are harmless
because `classify()` returns DIGESTED before reaching them; both mislead anyone auditing the reasons,
which is the one job the file says a human must do.

**L5 — `has_m4`'s fallback is reachable on an EMPTY manifest, not only a missing one.**
`scripts/gen-m4-manifest.py:131` is `if manifest:`, and `read_committed()` (`:224-228`) returns an
**empty set** for a file that exists but holds only comments — falsy, so it degrades to the
two-marker probe `("table:workspaces", "table:video_generations")` that r6 M1 replaced.
`check-live-schema.load_manifest` raises on an empty manifest for exactly this reason; the generator's
reader does not. **Not fail-open today**: the missing-file path is also fail-closed by accident, since
the schema is non-idempotent, so re-applying M4 over a wrongly-negative baseline raises at
`applied.returncode != 0` — which is the accident the `has_m4` docstring itself flags as "one line of
`create or replace` away from being gone". Make `read_committed` raise on empty, or use
`if manifest is not None:`.

---

## VERIFIED AND NOT DEFECTS — round 8 need not re-run these

**HYPOTHESIS 1 (the whole of it, executed as `set role service_role` on a production-shaped M4 database)**

* All six live-table writes the app performs succeed post-M4 (playlists/videos/jobs insert, videos
  update ×2, deletes). Quoted in Medium 1.
* `service_role` retains `arwd` on all five tables and `r` on all three views, which is everything the
  app and the GC path need. `video_generations_collectable`'s `service_role`-only grant is correct.
* No sequences and no identity columns are created by M4 (`relkind='S'` count 1 → 1), so the
  "`revoke all on <table>` does not touch a sequence" hazard has no subject.
* `REFERENCES`/`TRIGGER`/`MAINTAIN` loss is moot for `service_role`: it holds no `CREATE` on schema
  `public` (`permission denied for schema public`). Migrations run as `postgres`, which is untouched
  by every revoke.
* Trigger firing does **not** check `EXECUTE`: all 12 definer functions show
  `has_function_privilege('service_role', …) = f` and every trigger fired.
* **The `workspaces` revoke r6 added is load-bearing, and the r6 comment's production measurement is
  correct.** Production's `postgres|public|r` default ACL is
  `{postgres=arwdDxtm, anon=arwdDxtm, authenticated=arwdDxtm, service_role=arwdDxtm, claude_ro=r}` —
  without that revoke, `anon` would have shipped with INSERT/UPDATE/DELETE on the tenancy root.

**HYPOTHESIS 4 — no false positive from the `fn:` digest match, on three real subjects**

```
--database postgres    --expect-absent   EXIT=0   M4 is ABSENT as expected
--database m4_r7c_pre  --expect-absent   EXIT=0   M4 is ABSENT as expected
--prod                 --expect-absent   EXIT=0   claude_ro@2600:…/postgres, read_only=on
                                                  M4 is ABSENT as expected
```

and directly: of 31 pre-M4 `public` functions, **zero** share a digest with any of the 13 manifest
function digests. `--expect-absent` does not cry wolf.

**HYPOTHESIS 3 — the comment sub-hypothesis does not fire.** Stripping `--` comments from
`CATALOG_SQL` and re-classifying all 203 columns changes **zero** verdicts. The over-broad-regex
sub-hypothesis produced only L4 (two misdescribed-but-harmless entries); `.*relid` matches nothing
that is not an OID. `atthasdef`'s and `relam`'s reasons hold.

**HYPOTHESIS 6**

* `run-schema-assertions.sh`'s new comment stripping has **no false negative**: I applied the exact
  three-`sed` pipeline to all 60 `do $$ … $$;` blocks in `05_assert.sql`; the `FAILS_LOUDLY` pattern
  survived in 57. The three misses (blocks 39, 45, 49) are **seed/setup blocks with no assertion at
  all** — they contain `raise notice`, not `raise exception`. Note separately that `05_assert.sql`
  carries **zero** `@RE-RUNNABLE` markers today, so against the real corpus the script is a
  fail-closed CANNOT RUN, as its own header states.
* **Gates 3 and 4 are still the only red ones and are pre-existing.** `./scripts/check-schema-gates.sh`
  → `10 problem(s) — guard coverage NOT met`, `5 problem(s) — sentinel meanings NOT met`, matching
  round 6 exactly. `git diff --stat d6688d8..74f450b -- scripts/check-guard-coverage.py
  scripts/check-sentinel-meanings.py` is **empty**; neither script nor its classification inputs were
  touched. Gates 7/8/9 are green (`203 columns … 73 digested, 130 excluded`; `manifest is current —
  161 objects`; `M4 is ABSENT as expected`).
* All self-tests pass: `check-catalog-coverage 11/11`, `check-live-schema 67/67`,
  `gen-m4-manifest 4/4`, `check-anon-exposure 22/22`, `run-schema-assertions 12/12`.
* Mutation harness: `MUTATION_HARNESS_EXIT=0`, 20 mutations / 21 checks, all caught.

**HYPOTHESIS 5 — what the harness still cannot express.** The honest answer this round is not
mutation 19's missing `claude_ro`; it is that **all three of my findings are mutations the harness has
no vocabulary for**, and the reason is the one its own header names ("what did the last
counter-example have that my check missed?"):

| Cannot express | Found as |
|---|---|
| a change to an argument DEFAULT | Blocking 1 |
| a grant of a verb outside `REL_PRIVS` (mutation 10 grants exactly the four covered verbs) | Blocking 2 |
| a grant to a grantee outside `REL_GRANTEES` | High 1 |

Also still unreachable, and unchanged from r6: mutation 19 installs default privileges but cannot
create `claude_ro`, so no local harness can produce the ACL shape production actually has — now
measured to be `{…, claude_ro=r/postgres}` on **every** `public` table. And `check-anon-exposure.py`
hard-codes database `postgres` (`:265`), so it can never be pointed at a scratch database — its
`--local` arm cannot be mutation-tested at all.

---

## Hygiene

Databases created, all cloned from a scratch base, all dropped:
`m4_r7c_pre`, `m4_r7c_tpl`, `m4_r7c_h1`, `m4_r7c_defaults`, `m4_r7c_prodat`, `m4_r7c_h2role`,
`m4_r7c_h2fn`, `m4_r7c_h2trunc`, `m4_r7c_excl`. One cluster role created and dropped: `m4_r7c_ro`.
The mutation harness's own `m4_gate_mut_$$` databases self-clean via its `trap`.

```
select datname from pg_database where datname like 'm4_%' or datname like 'codex%';   -> <none>
select rolname from pg_roles   where rolname like 'm4_r7c%';                          -> <none>
```

**The shared `postgres` database was never written and is still PRE-M4:**

```
select count(*) from pg_tables where schemaname='public';                        -> 13
select count(*) from pg_tables where schemaname='public' and tablename='workspaces'; -> 0
```

Production was read **read-only only** — `check-live-schema.py --prod --expect-absent` and one
`pg_default_acl`/`relacl` query, both under `set session characteristics as transaction read only`.

Repo: the only file I created or modified is this one,
`docs/reviews/plan-m4-v2-r7-claude.md`, on branch `docs/m4-round7`. ⚠ `git status` at cleanup time
also showed `D docs/reviews/plan-m4-v2-r7-codex.md` and `M scripts/codex-review.py` — **neither is
mine**; they belong to the concurrently running Codex half sharing this worktree, and I left both
untouched. The coordinator should confirm the Codex half did not lose its own output file.

---

**NOT CONVERGED**
