<!-- codex-review: model=gpt-5.5 -->

⭐ **Primary Answer**

Yes. v2.1’s own fixes introduced new defects. The biggest new defects are in the rewritten `0028`: it now uses wrong `drop function` signatures for `record_artifact` and `slot_kind`, so the rollback still does not reach the end. The fixed Task 8 seed also now fails because `auth.users` insertion fires `on_auth_user_created`, then the seed inserts the same `profiles.id` again.

**Blocking**

1. `0028` still does not execute verbatim. I built `0001`-`0026`, then temporary post-ADR `01+03+04`, then ran v2.1’s `0028` verbatim in a disposable DB. It fails at `drop type artifact_kind` because two function drops silently skipped:
   - Plan drop: `record_artifact(uuid, text, text, artifact_kind, jsonb, text, text)` at `docs/superpowers/plans/2026-08-25-m4-promote-the-schema-v2.md:649`
   - Actual signature: `record_artifact(uuid, text, text, text, artifact_kind, text, text, int, int, text, jsonb, int, timestamptz)` at `docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema/04_artifacts.sql:354-359`
   - Plan drop: `slot_kind(artifact_kind)` at `docs/superpowers/plans/2026-08-25-m4-promote-the-schema-v2.md:657`
   - Actual signature: `slot_kind(text)` at `docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema/04_artifacts.sql:22`

   Execution output included:
   `NOTICE: function record_artifact(uuid,text,text,artifact_kind,jsonb,text,text) does not exist, skipping`
   `NOTICE: function slot_kind(artifact_kind) does not exist, skipping`
   then:
   `ERROR: cannot drop type artifact_kind because other objects depend on it`.

2. `check-live-schema.py` is not executable as specified. The implementation block imports `argparse, subprocess, sys` at `docs/superpowers/plans/2026-08-25-m4-promote-the-schema-v2.md:329` and defines `verdict()` at `:351-363`, but the plan contains no catalog queries, no argument parser, and no `main`.
   Search command used: `rg -n "information_schema|pg_trigger|pg_proc|pg_type|argparse|parse_args|def main|if __name__" docs/superpowers/plans/2026-08-25-m4-promote-the-schema-v2.md`.

3. Task 9 still invokes the full gate suite after `0027` without `M4_PHASE`, making the plan fail as written. v2.1 says `check-schema-gates.sh` exits 2 if `0027` exists and `M4_PHASE` is unset at `docs/superpowers/plans/2026-08-25-m4-promote-the-schema-v2.md:408-411`, but Task 9 runs `./scripts/check-schema-gates.sh` bare at `:900-903`.

4. Even with `M4_PHASE=post`, the full suite cannot be “all green” after `0027`: Task 4 makes rebuild gates exit 2 when the live gate says M4 is present at `docs/superpowers/plans/2026-08-25-m4-promote-the-schema-v2.md:465-470`, while the gate runner treats any non-zero as failure at `scripts/check-schema-gates.sh:22-27`. The plan warns about this at `docs/superpowers/plans/2026-08-25-m4-promote-the-schema-v2.md:421-423` but does not implement a post-phase skip or alternate suite.

5. Task 2’s `05_assert.sql` sweep is incomplete. It lists five sites at `docs/superpowers/plans/2026-08-25-m4-promote-the-schema-v2.md:218-226`, but search finds a later obsolete shared-corrections assertion:
   - `docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema/05_assert.sql:1913`
   - `docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema/05_assert.sql:1915`

   Search command used: `rg -n "workspace_videos where corrections_hash is null|insert into workspace_videos .*corrections_hash|update workspace_videos set corrections_hash|wv\\.corrections_hash|wv\\.corrections|sync_corrections_to_workspace_video|select corrections from workspace_videos" docs/.../05_assert.sql`.

6. Task 8’s fixed seed corpus fails. Inserting into `auth.users` as specified at `docs/superpowers/plans/2026-08-25-m4-promote-the-schema-v2.md:779-781` fires `on_auth_user_created` at `supabase/migrations/0003_provisioning.sql:10-11`, which inserts `profiles`. The next seed line inserts the same profile again at `docs/superpowers/plans/2026-08-25-m4-promote-the-schema-v2.md:782`. Executed in rollback: duplicate key on `profiles_pkey`.

**High**

1. Task 2’s `05_assert` anchor is non-unique. `insert into workspace_videos (workspace_id, video_id, corrections_hash)` appears twice, including the obsolete NULL-guard assertion at `docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema/05_assert.sql:917-919`. Command used: Python `text.count(...)` over `05_assert.sql`.

2. Task 3 self-test count is stale: it defines 8 checks at `docs/superpowers/plans/2026-08-25-m4-promote-the-schema-v2.md:283-298`, but expects `5/5` at `:370-373`.

**Medium**

none

**Low**

none

**DID v2.1’s OWN FIXES INTRODUCE DEFECTS?**

Yes. Evidence:
- The rewritten `0028` added explicit function drops but two signatures are wrong, so the rollback now fails at the enum drop.
- The fixed seed now includes the required `auth.users` row, but that creates the profile via trigger before the seed’s explicit profile insert, causing a duplicate key.
- The `M4_PHASE` fix introduces a required env var but Task 9 still runs the suite without it, and gates 1-2 still conflict with the post-`0027` world.

**IS THIS PLAN EXECUTABLE AS WRITTEN?**

No. `0028` does not reach the end, `check-live-schema.py` is not a runnable script as specified, Task 9’s suite invocation is structurally red, and Task 8’s seed fails.

NOT CONVERGED
