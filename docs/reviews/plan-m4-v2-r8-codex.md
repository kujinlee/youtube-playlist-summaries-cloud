<!-- codex-review: model=gpt-5.5 -->

1. 🔴 Blocking — RULE 3’s mutation proof is masked on the exact scratch subject the harness uses.

Premise: “Coverage MOVED, it did not vanish.” The moved mutations rely on `anon_gate()` at `scripts/mutate-live-schema-check.sh:43-48`, and mutations 10/17/22/23 accept any non-zero exit as “RULE 3 FAILS” at `scripts/mutate-live-schema-check.sh:238-241`, `:385-388`, `:413-414`, `:505-508`.

Code evidence:
`check-anon-exposure.py` does have the intended RULE 3 implementation at `scripts/check-anon-exposure.py:227-270` and `:273-286`, but the harness wrapper only checks exit status.

Executed evidence, clean post-M4 scratch built like the mutation template:

```text
scratch=r8_review_67877
live schema [local container db 'r8_review_67877' ...]: M4 is PRESENT as expected — checked all 161 objects...
subject: LOCAL container supabase_db_youtube-playlist-summaries-cloud db 'r8_review_67877'
         22 SECURITY DEFINER function(s) in public, 12 anon-EXECUTable
         money tables TRUNCATE-able by a session role: 0/5 (baseline 5)
         M4 functions present: 13  [39 (function, role) pairs read]
         M4 relations present: 8/8  [24 (relation, role) pairs read]

FAILED — 3 problem(s):

UNLISTED           `exec_sql` is SECURITY DEFINER and anon-EXECUTable...
UNLISTED           `record_correction_spend` is SECURITY DEFINER and anon-EXECUTable...
LOWER THE BASELINE 0 money tables are TRUNCATE-able, baseline says 5...
schema assertions: RE-RUNNABLE subset passed against the live schema, and rolled back clean
dropped=r8_review_67877
```

Consequence: the moved privilege mutations can be “caught” before RULE 3 says anything about the mutated M4 privilege. Observable unit: on a clean M4 scratch database, `check-anon-exposure.py --local --database <db>` already exits non-zero. Mutation 10/17/22/23 therefore do not prove coverage moved; they prove the whole anon-exposure script is red on the harness fixture.

Direction: make `anon_gate` assert the named problem appears and that the clean control is green for the target being mutated. At minimum, split RULE 3 into an isolated mode for mutation harness use, or build the mutation fixture without the unrelated `--no-privileges` inherited function/money-table drift.

2. 🔴 Blocking — `verify-schema.sh` is red in context 1, and the failure is a privilege assertion masked by `art_dig_has_span`.

Premise: “The assertions run in TWO contexts... Is the fix right in BOTH, and does it interact with any OTHER block?” `verify-schema.sh` concatenates all schema files at `docs/superpowers/specs/2026-08-03-stable-blob-addressing/verify-schema.sh:10-12`.

Code evidence:
The failing block calls `record_artifact` as `anon` with a dig slot but no span at `docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema/05_assert.sql:742-751`.

Executed evidence:

```text
M4_PHASE=pre scripts/check-schema-gates.sh

═══ 1/11  schema + assertions (verify-schema.sh) ═══
...
NOTICE:  ok (RLS): the owner still reads their own manifest through the view
DO
ERROR:  new row for relation "video_artifacts" violates check constraint "art_dig_has_span"
DETAIL:  Failing row contains (... vidA, dig:9, gDIG, dig, recorded, k, null, null, ...)
CONTEXT:  SQL statement "insert into public.video_artifacts
    (workspace_id, video_id, slot, generation_id, kind, state, blob_key,
     start_sec, end_sec)
...
SQL statement "SELECT record_artifact(ws,'vidA','dig:9','gDIG','dig'::artifact_kind,'k')"
PL/pgSQL function inline_code_block line 5 at PERFORM
❌ schema FAILED
```

The same gate then produced broad `RED(other)` failures in mutation testing, also mostly `art_dig_has_span`:

```text
23/63 mutations behaved as expected (RED, or GREEN where documented as subsumed)
baseline restored: STILL BROKEN ❌
❌ FAILED: docs/superpowers/specs/2026-08-03-stable-blob-addressing/mutate-schema.py
```

Consequence: gate 1/11 is not green, contrary to the round’s operating premise that only gates 3 and 4 are red by plan. Observable unit: `verify-schema.sh` exits 1 before reaching the bottom of `05_assert.sql`; mutation gate 2 loses discriminating power because one early malformed fixture dominates many cases.

Direction: make the anon `record_artifact` negative violate exactly privilege and nothing else: use a valid dig span/blob key, or use a summary/model fixture whose constraints are already satisfied. Then rerun `verify-schema.sh` and `mutate-schema.py`.

3. 🟠 High — ADR-0012’s “mutation 19 fails on a regressed revoke” claim is false after the digest shrink.

Premise quoted: `docs/adr/0012-revoke-before-grant-is-schema-wide.md:78-81` says mutation 19 asserts production-shaped M4 must pass and “A regressed revoke breaks that agreement and the mutation goes red.” But mutation 19 only runs `check-live-schema.py --expect-present` at `scripts/mutate-live-schema-check.sh:532-555`.

Executed evidence, production-shaped scratch with only `service_role` removed from the `slot_kind(text)` revoke:

```text
scratch_good=r8_prodshape_good_70384
scratch_bad=r8_prodshape_bad_70384
-- gate on bad regressed revoke --
live schema [local container db 'r8_prodshape_bad_70384' ...]: M4 is PRESENT as expected — checked all 161 objects...
check_live_exit=0
-- direct capability on bad --
true
-- assertions on bad --
NOTICE:  ok: service_role recorded a paid artifact through the RPC, and the row is there
ERROR:  ASSERTION FAILED — service_role wrote video_artifacts DIRECTLY. record_artifact is not the only door...
assert_exit=1
dropped=r8_prodshape_good_70384
dropped=r8_prodshape_bad_70384
```

Consequence: mutation 19 no longer mechanises ADR-0012. The assertion suite catches this particular regressed revoke, but the ADR’s stated instrument does not. Observable unit: `check-live-schema.py` exits 0 while `service_role` retains `EXECUTE` on `slot_kind(text)`.

Direction: change ADR-0012 and the harness. Either mutation 19 must run the capability assertions too, or a separate revoke-shape scanner must exist if the convention is meant to be mechanically enforced.

4. 🟠 High — service-role table capabilities are neither digested nor asserted.

Premise quoted: ADR-0013 says `service_role`’s ability to do its job lives in `05_assert.sql` at `docs/adr/0013-capabilities-are-asserted-privileges-are-not-digested.md:55-61`.

Code evidence:
The service-role capability block only proves `record_artifact` works and direct `video_artifacts` insert is refused at `05_assert.sql:782-923`. But the schema explicitly grants direct table DML to `service_role`: `workspaces` at `01_workspaces.sql:28-30`, `workspace_videos` and `video_generations` at `03_generations.sql:68-69` and `:562-563`, `video_artifact_sources` at `04_artifacts.sql:257-259`, and `video_artifacts` at `04_artifacts.sql:670-671`. The sweeper shape is an update of `body_collected` at `05_assert.sql:1952-1967`.

Executed evidence, removing only `UPDATE` on `video_generations` from `service_role`:

```text
scratch=r8_svc_update_gap_71994
-- before privilege --
true
-- after privilege --
false
-- live digest --
... M4 is PRESENT as expected — checked all 161 objects...
check_live_exit=0
-- schema assertions --
schema assertions: RE-RUNNABLE subset passed against the live schema, and rolled back clean
assert_exit=0
dropped=r8_svc_update_gap_71994
```

Capability probe with the role actually set:

```text
scratch=r8_svc_update_denied2_73437
 service_role_can_update_generations
-------------------------------------
 false

SET
ERROR:  permission denied for table video_generations
HINT:  Grant the required privileges to the current role with: GRANT UPDATE ON public.video_generations TO service_role;
update_probe_exit=3
dropped=r8_svc_update_denied2_73437
```

Old digest comparison: at base `74f450b`, `scripts/m4_catalog.py:153` had `REL_GRANTEES = ("public", "anon", "authenticated", "service_role")`, and `:199-203` digested table and column privileges. Current branch has `REL_GRANTEES: tuple[str, ...] = ()` and `FN_GRANTEES: tuple[str, ...] = ()` at `scripts/m4_catalog.py:205-206`.

Consequence: a real service-role capability can disappear with both current instruments green. Observable unit: `service_role` cannot execute even an empty `UPDATE video_generations ... where false`, while `check-live-schema` and the re-runnable assertions exit 0.

Direction: decide whether direct `service_role` DML is a supported capability or residue. If supported, add executable service-role assertions for the direct operations it must perform, especially GC `body_collected` updates and any provenance operations. If not supported, remove the grants instead of leaving them as unmeasured intent.

**What I Checked And Did NOT Find**

| Check | Result |
|---|---|
| Current branch/head | Confirmed `docs/m4-round7` at `563333de44626fa6408d3e7210dd6dd6dff735e6`. |
| Phase 6 #2 review premise | Read `docs/reviews/architecture-review-2026-08-25b.md`; it does recommend fork (a), moving privileges out of the fingerprint. |
| RULE 3 pure self-tests | `python3 scripts/check-anon-exposure.py --self-test` passed `46/46`. I did not find a pure-rule bug for table-level INSERT, column-level INSERT, TRUNCATE, out-of-reach relation SELECT, or M4 function EXECUTE. |
| Local pre-0027 RULE 3 vacuity | `python3 scripts/check-anon-exposure.py --local` printed `M4 relations present: 0/8 ... pre-0027` and exited 0. That is visible, but not falsifying on the real pre-M4 `postgres` DB. |
| Re-runnable assertion harness self-test | `./scripts/run-schema-assertions.sh --self-test` passed `12 of 12`; I did not find a selector bug. Note: this script created its built-in non-`r8_` scratch DB name and dropped it via its trap. |
| Re-runnable service-role blocks alone | On clean post-M4 scratch, `PGDATABASE=r8_review_67877 ./scripts/run-schema-assertions.sh` passed and rolled back clean. I did not find persistence from the self-fixturing block. |
| Catalog coverage | `python3 scripts/check-catalog-coverage.py --self-test` passed `11/11`; `python3 scripts/check-catalog-coverage.py` reported `203 columns across 9 catalogs — 73 digested, 130 excluded`. I did not find an unclassified catalog column in this run. |
| Manifest currentness | `scripts/check-schema-gates.sh` gate 9 reported `manifest is current — 161 objects`. |
| Tracked files | `git status --short` was empty after my probes. |
| Scratch cleanup | I created and dropped `r8_review_67216`, `r8_review_67877`, `r8_prodshape_good_70384`, `r8_prodshape_bad_70384`, `r8_svc_update_gap_71994`, `r8_svc_update_denied_72814`, and `r8_svc_update_denied2_73437`. Final cleanup query found none of those names, and no `m4_assert_selftest_%` DB. Existing `r8_claude_*` databases were already present and I did not touch them. |

NOT CONVERGED. The instrument shrink is not yet proved: the moved RULE 3 mutations are masked on the harness fixture, ADR-0012 names the wrong falsifier, and at least one explicit `service_role` capability is now uncovered.
