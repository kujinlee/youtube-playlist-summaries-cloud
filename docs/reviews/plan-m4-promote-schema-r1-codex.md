<!-- codex-review: model=gpt-5.5 -->

Verified: the headline claim is true. `01_workspaces.sql:36-48` adds `workspace_id` to `playlists`, `videos`, and `jobs`, backfills each, then sets each `NOT NULL`.

**Blocking**
- `docs/superpowers/plans/2026-08-25-m4-promote-the-schema.md:48` claims M4a is “New objects only,” but `03_generations.sql` attaches triggers to live tables: `profiles` at `03_generations.sql:152-154`, `playlists` at `198-203`, `videos` at `204-209` and `253-262`, and `jobs` at `210-215`. That changes live write behavior immediately. M4a is not new-objects-only or cleanly reversible by `drop` of new tables.

- The M4a/M4b split is not executable as written. T2 says to create `workspace_videos`/`video_generations` with every `playlists`/`videos`/`jobs` reference removed, but the schema’s own objects depend on the new live-table columns. `workspace_videos` is backfilled from `videos.workspace_id` at `03_generations.sql:89-95`; the FK at `96-97` references `videos(workspace_id, video_id)`; triggers use `new.workspace_id` and are declared `update of ... workspace_id` at `201-214`; the corrections trigger reads `new.workspace_id` at `230-233`. `0027` cannot contain those pieces before M4b, and omitting them means it is no longer promoting the accepted schema.

- T3’s “all six green, against the migrations” is mechanically false as scoped. `scripts/check-schema-gates.sh:29-33` still runs `docs/.../verify-schema.sh` and `mutate-schema.py`, and those are hardwired to the spec schema: `verify-schema.sh:8-10`, `mutate-schema.py:25-27`, `mutate-schema.py:880-884`. Repointing only `check-guard-coverage.py` and `check-sentinel-meanings.py` does not make the six gates test migrations. The plan’s gate at `2026-08-25-m4-promote-the-schema.md:100` is refuted by the scripts.

- Repointing `check-guard-coverage.py` to M4a migrations before M4b will fail or silently change the subject. Its inventory explicitly expects M4b guards including `videos_workspace_video_fk`, `videos_workspace_id_fkey`, `jobs_workspace_id_fkey`, `jobs_workspace_owner_fk`, `playlists_workspace_id_fkey`, and trigger functions on live tables at `scripts/check-guard-coverage.py:111-150`. Those do not exist in a clean “new tables only” M4a.

**High**
- T1’s falsifiers are incomplete. The plan checks orphaned `videos`/`playlists`/`jobs` rows at `2026-08-25-m4-promote-the-schema.md:80-86`, but `SET NOT NULL` can also be defeated by concurrent writes between `ADD COLUMN`, backfill, and `SET NOT NULL` if the migration is not a single transaction holding locks until commit. The plan never requires an explicit transaction/lock strategy, `lock_timeout`/`statement_timeout` handling, or a write-quiescence check. That is material production risk.

- T1 contains a stale premise: “`jobs.playlist_id` is nullable in some paths” at `2026-08-25-m4-promote-the-schema.md:85`, but current shipped migration `0009_job_playlist_identity_and_worker_persistence.sql:4` adds `playlist_id uuid not null`. The query is harmless, but the plan is reasoning from an outdated schema fact.

- T6’s “`video_artifacts_inflight_uq` is NOT deleted in M4” is not what promoting the current spec does. In `04_artifacts.sql`, the index “stood here” and is absent by design at `04_artifacts.sql:269-288`; `record_artifact` is created and granted to `service_role` at `04_artifacts.sql:354-360` and `628-633`. ADR-0007 says the deletion is safe only with the `doc_key` re-key at `0007-artifacts-are-an-append-only-log.md:163-170`. No application caller lowers the probability, but M4 still exposes the post-deletion artifact protocol.

**Medium**
- The plan names “two FKs” at `2026-08-25-m4-promote-the-schema.md:31`, but only cites the `videos` FK. The second is `jobs_workspace_owner_fk` at `01_workspaces.sql:50-51`. This matters because the blast-radius section is supposed to be the production-data inventory.

- `05_assert.sql` depends on M4b behavior, not just new objects. It reads `videos.workspace_id` at `05_assert.sql:893-911`, asserts unchanged inserts derive `videos.workspace_id` and `jobs.workspace_id` at `1843-1859`, and tests playlist/video disagreement at `1862-1927`. T4 cannot give `05_assert.sql` a meaningful M4a home without splitting assertions or accepting that M4a gates are testing future M4b state.

**Low**
- The plan says M4a is reversible by `drop` at `2026-08-25-m4-promote-the-schema.md:48`, but even ignoring live-table triggers, it creates functions, enum types, policies, grants, views, and RLS state across `03_generations.sql` and `04_artifacts.sql`. That rollback statement is too casual for production review.

Verdict: **NOT CONVERGED**.
