<!-- codex-review: model=gpt-5.5 -->

**Blocking**

1. `service_role` function EXECUTE is outside the live-schema digest, so the gate can pass over an RPC outage.

Premise:
`scripts/m4_catalog.py:153-155`:
```py
REL_GRANTEES = ("public", "anon", "authenticated", "service_role")
FN_GRANTEES = ("public", "anon", "authenticated")
REL_PRIVS = ("SELECT", "INSERT", "UPDATE", "DELETE")
```
`scripts/m4_catalog.py:210-216` says `service_role` is deliberately absent from function privilege checks.
`04_artifacts.sql:631-633` grants `record_artifact(...)` to `service_role`.

Executed evidence:
```text
fnsvc_before_rc=0
M4 is PRESENT as expected — checked all 161 objects ...

fnsvc_measure:
t
f

fnsvc_gate_rc=0
M4 is PRESENT as expected — checked all 161 objects ...
```
Then the actual RPC path as `service_role`:
```text
ERROR:  permission denied for function record_artifact
```

Consequence: removing the one grant that lets the worker/server call `record_artifact` is a production write outage, and `check-live-schema.py --expect-present` still exits 0.

**High**

2. `service_role` direct `INSERT` on `video_artifacts` is granted but unusable because `slot_kind()` is not executable by `service_role`.

Premise:
`04_artifacts.sql:118` uses `slot_kind(slot)` in `art_slot_kind`.
`04_artifacts.sql:634` revokes `slot_kind(text)` from `public, anon, authenticated` and grants it to nobody.
`04_artifacts.sql:655-656` grants `INSERT` on `video_artifacts` to `service_role`.

Executed evidence:
```text
role=service_role, bypassrls=true
...
INSERT 0 1              -- workspace_videos
INSERT 0 1              -- video_generations
ERROR:  permission denied for function slot_kind
```
Catalog proof:
```text
slot_kind|f|f|f
record_artifact|t|f|f
```

Consequence: the post-M4 grant set says `service_role` can insert into `video_artifacts`, but a direct insert fails before the row can be written. The RPC path works because `record_artifact` is `SECURITY DEFINER`; raw DML does not.

3. `proargdefaults` exclusion is false: changing only a function default changes behavior and the gate stays green.

Premise:
`scripts/check-catalog-coverage.py:112-115` excludes `proargdefaults` because “a change to a default’s VALUE changes the identity arguments.”

Executed evidence:
```text
defaults_before_rc=0
M4 is PRESENT as expected — checked all 161 objects ...

pg_get_function_identity_arguments:
p_ws uuid, ... p_md_hash text, p_card jsonb, ...

pg_get_function_arguments after mutation:
... p_md_hash text DEFAULT 'r7-default'::text ...

defaults_gate_rc=0
M4 is PRESENT as expected — checked all 161 objects ...
```
Behavior changed:
```text
record_artifact_9_args=recorded
stored_md_hash=r7-default
```

Consequence: the manifest can certify the function “by definition” while omitted-argument calls write different data.

4. `TRUNCATE` on M4 tables is invisible to both the M4 digest and `check-anon-exposure.py`.

Premise:
`scripts/m4_catalog.py:155` limits relation privileges to `SELECT, INSERT, UPDATE, DELETE`.
`scripts/check-anon-exposure.py:65-68` limits the TRUNCATE ratchet to five non-M4 money tables.

Executed evidence:
```text
truncate_before_rc=0
M4 is PRESENT as expected — checked all 161 objects ...

truncate_measure:
f
t

truncate_gate_rc=0
M4 is PRESENT as expected — checked all 161 objects ...
```
`check-anon-exposure.py --local`:
```text
money tables TRUNCATE-able by a session role: 5/5 (baseline 5)
Anon exposure OK ...
```

Consequence: `grant truncate on video_artifacts to anon` changes the catalog and gives anon the operation this schema’s own comments identify as bypassing RLS and row triggers, but both gates stay green.

**Medium**

5. `check-catalog-coverage.py` does not fail closed if `CATALOGS` omits a catalog the digest reads.

Premise:
`scripts/check-catalog-coverage.py:43-44` hand-lists the catalogs.
`scripts/check-catalog-coverage.py:196-199` enumerates only that tuple.

Executed evidence, in-memory monkeypatch only:
```text
catalogs= ('pg_class', 'pg_proc', 'pg_attribute', 'pg_index', 'pg_policy', 'pg_constraint', 'pg_trigger', 'pg_type')
rows= 195 counts= {'DIGESTED': 68, 'EXCLUDED': 127, 'UNCLASSIFIED': 0} bad= [] exit_would_be= 0
```

Consequence: removing `pg_rewrite` from `CATALOGS` makes the new coverage gate green while no longer checking the catalog added for rewrite-rule sabotage.

**Verified And Not Defects**

- M4 creates no public sequences; `information_schema.sequences` returned no public rows. The M4 columns use `gen_random_uuid()` defaults, not `serial`/`identity`.
- `service_role` relation grants after M4 are exactly SELECT/INSERT/UPDATE/DELETE on the five tables and SELECT on the three views. No REFERENCES/TRIGGER grants remain:
```text
has_refs=false/false
has_trigger=false/false
```
- The intended RPC path works before revoking EXECUTE:
```text
record_artifact=recorded
rows=1/1
collectable_select=1
```
- `video_generations_collectable` SELECT plus non-current GC update/delete works as `service_role`:
```text
collectable_contains=1
noncurrent_collect_update=true
delete_generation_remaining=0
```
- Grant to an unlisted role is invisible, measured:
```text
f -> t
otherrole_gate_rc=0
```
I do not count that as a defect by itself; `m4_catalog.py:131-149` states this is the price of environment-invariance. The missing `service_role` function grant and TRUNCATE cases above are different because they affect named M4 behavior/security.
- `digested_columns()` did not count any catalog column solely from SQL comments:
```text
catalog_column_tokens_only_in_comments= []
```
- Pre-M4 absent mode passed locally and on production:
```text
absent_local_rc=0
absent_prod_rc=0
```
- `has_m4(catalog, manifest=None)` still fails open for function-only survivors:
```text
has_m4_fn_only_no_manifest= False
has_m4_fn_only_with_manifest= True
```
Not a current-path defect because the committed manifest exists here, but it remains the fallback’s real bound.
- Gates 3 and 4 are still the only red schema gates. `M4_PHASE=pre ./scripts/check-schema-gates.sh` failed at `check-guard-coverage.py` and `check-sentinel-meanings.py`; gates 5-9 were green.
- `mutate-live-schema-check.sh` passed all 20 mutations, including mutation 19’s production-shaped default privileges.
- `run-schema-assertions.sh --self-test` passed 12/12. The real `05_assert.sql` selector is NOT RUN because the file has no `@RE-RUNNABLE` marker:
```text
assert_print_real_rc=2
CANNOT RUN — no @RE-RUNNABLE block with EXECUTABLE SQL ...
```
- `gen-m4-manifest.py --self-test` passed 4/4.
- Roadmap/task-order checks passed:
```text
roadmap_rc=0
plan_order_rc=0
```

**Hygiene**

Created and dropped:
`r7_codex_48600_svc`, `r7_codex_48600_otherrole`, `r7_codex_48600_truncate`, `r7_codex_48600_otherrole2`, `r7_codex_48600_truncate2`, `r7_codex_48600_fnsvc`, `r7_codex_48600_defaults`.

Created and dropped role:
`r7_codex_48600_writer`.

Final checks:
```text
remaining_dbs:
remaining_role:
```

NOT CONVERGED.
