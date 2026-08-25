<!-- codex-review: model=gpt-5.5 -->

Blocking: none.

High: none.

Medium
- `docs/superpowers/plans/2026-08-25-m4-promote-the-schema.md:110-113`, `:151-159` overstates what the T1 row counts prove. `playlists=3 videos=12 jobs=15` bounds the rewrite/backfill work after locks are acquired; it does not bound time to acquire `ACCESS EXCLUSIVE` locks on the live tables changed by `01_workspaces.sql:36-48`. The chosen `lock_timeout` strategy is still defensible: failing fast is better than letting a migration sit queued behind a worker transaction and block later app/worker traffic. But the inference should be “try without maintenance, abort safely, and have a fallback/pause-worker runbook if lock acquisition fails,” not “maintenance window unnecessary.”

Low
- `docs/superpowers/plans/2026-08-25-m4-promote-the-schema.md:84-85` says the T1 SQL is “in a file,” but `find scratchpad docs supabase scripts -iname '*m4*' -o -iname '*0027*' -o -iname '*prod*measure*'` found no measurement SQL file beyond the plan/reviews. I re-ran the read-only production measurement via Node `pg` because local `psql` is absent; the figures match the plan exactly: `workspace_id_exists=0`, conflicts `0`, non-empty corrections `1`, dup groups `0/0`, orphans `[0,0,0]`, counts `3/12/15`, pgcrypto `1`, digest `2`. So this is reproducibility hygiene, not a refutation of the numbers.

- Prior residue, not a new T1 defect: `docs/superpowers/plans/2026-08-25-m4-promote-the-schema.md:77-80` still uses `check-docs` as T0’s gate for correcting the append-only spine. `scripts/check-docs.py:447-472` only checks the advisory count in `docs/roadmap-to-launch.md`; it does not read the M4 spine. This was already called in r3 M1, and v4 did not fix it.

T1 query verdict: correct. `01_workspaces.sql:28-33` seeds `workspaces.id = owner_id`; `01_workspaces.sql:36-42` derives playlist workspace by owner and video workspace by playlist. Existing `0001_core_schema.sql:23-32` also enforces `videos.owner_id` matches the playlist owner. Grouping pre-M4 by `(owner_id, video_id)` therefore reproduces post-M4 `(workspace_id, video_id)` for this slice.

Assertion verdict: sufficient and expressible. Mechanism is a plain PostgreSQL `DO $$ ... IF EXISTS (...) THEN RAISE EXCEPTION ... END IF; END $$;` block placed after `01_workspaces.sql` has acquired the live-table locks and immediately before `03_generations.sql:89-95`. `RAISE EXCEPTION` aborts the migration transaction. The check should use the same `(owner_id, video_id)` collision query from T1.

Prior confirmations: I found no new v4 breakage of the main prior fixes. v4 keeps one migration file for `01/03/04`, excludes `05_assert.sql`, names the gate rewrites, switches M4-alpha to local seeded Supabase, adds the `workspaces` revoke, and makes T7 repo-wide.

CONVERGED.
