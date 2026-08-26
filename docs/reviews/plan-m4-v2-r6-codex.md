<!-- codex-review: model=gpt-5.5 -->

**Blocking**

1. `ENFORCEMENT_COLUMNS` still misses a function execution flag: `pg_proc.proisstrict`.

Premise:
[scripts/m4_catalog.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/m4_catalog.py:86) lists function enforcement columns as `prosecdef`, `proconfig`, `provolatile`, `prokind`, `proacl`.
[scripts/m4_catalog.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/m4_catalog.py:153) digests only `prosrc`, `prosecdef`, `provolatile`, `prokind`, `proconfig`, `proacl`.

Executed evidence:
```text
select ... p.proisstrict ... where proname='record_artifact';
...|false

alter function record_artifact(..., timestamp with time zone) strict;

select ... p.proisstrict ... where proname='record_artifact';
...|true

python3 scripts/check-live-schema.py --database codex_r6_strict --expect-present
live schema [local container db 'codex_r6_strict' ... read_only=on]:
M4 is PRESENT as expected — checked all 161 objects ...
gate_after=0
```

Catalog search confirmed Postgres offers this column and the code never reads it:
```text
pg_proc columns include: proisstrict boolean
rg proisstrict ... => no script hit
```

Consequence: a function body can stop executing for NULL-bearing calls without any manifest digest change. This is exactly the “rule executes” class round 5 claimed to close.

**High**

2. `symbol_of()` still lets renamed M4 survivors pass absent mode.

Premise:
[scripts/m4_catalog.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/m4_catalog.py:293) strips digest and function arguments, but not object lineage.
[check-live-schema.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-live-schema.py:189) treats a survivor as M4 only when its current `symbol_of()` matches a manifest symbol.

Executed evidence:
```text
alter function video_artifacts_append_only() rename to video_artifacts_append_only_old;

select proname, prosecdef, proconfig ...
video_artifacts_append_only_old | t | search_path=""

psql ... < rollback_0027_stable_blob_addressing.sql
NOTICE: function video_artifacts_append_only() does not exist, skipping

select proname, prosecdef, proconfig ...
video_artifacts_append_only_old | t | search_path=""

python3 scripts/check-live-schema.py --database codex_r6_rename --expect-absent
live schema [local container db 'codex_r6_rename' ... read_only=on]:
M4 is ABSENT as expected — checked all 161 objects ...
gate_absent_after=0
```

Consequence: rollback verification can certify M4 absent while a renamed M4 `SECURITY DEFINER` function remains in `public`.

**Verified And Not Defects**

- `gen-m4-manifest.py --self-test`: passed `4/4`; post-M4 baseline rollback path produced the same 161-object manifest.
- `run-schema-assertions.sh --self-test`: passed `9/9`; comment-only, semicolon, `select 1`, string-literal marker, and live red/green cases behaved as intended.
- `mutate-live-schema-check.sh`: all 16 mutations caught; no `m4_gate_mut*` DBs left.
- ACL hypothesis: simulated default `SELECT` privileges matched M4’s explicit ACLs and passed. Simulated broader `anon=arwd` default privilege made `table:workspaces` differ and the gate failed, which is correct. Actual prod post-M4 ACL comparison is NOT RUN because prod is currently pre-M4; `--prod --expect-absent` passed read-only.
- Read-only catalog sessions did not break generator self-test or manifest `--check`.
- Gates 3 and 4 are pre-existing: archived `ceb5875` and current tree both failed `check-guard-coverage.py` with 10 problems and `check-sentinel-meanings.py` with 5 problems.
- Hook matcher covers `supabase/migrations/0027_*.sql` and `supabase/rollback/rollback_0027_*.sql`; unrelated `app/page.tsx` produced no banner.

**Hygiene**

Created and dropped: `codex_r6_strict`, `codex_r6_rename`, `codex_r6_aclprod`, `codex_r6_aclupdate`, `codex_r6_partialsrc`. Final DB check for `codex_r6_%`, `m4_gate_mut%`, `m4_manifest_gen`, `m4_manifest_gen_post`, `m4_assert_selftest`: `<none>`. Git worktree remained clean.

**NOT CONVERGED**
