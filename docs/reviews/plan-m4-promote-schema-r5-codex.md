<!-- codex-review: model=gpt-5.5 -->

Primary answer: **yes. v5’s own fixes introduced a new Blocking defect in T9.** The rollback task’s lossless proof is stated at the wrong layer, and its proposed gate does not prove the property it claims.

**Blocking**

1. **T9’s lossless rollback claim is false as written, and the gate proves the wrong thing.**

`docs/superpowers/plans/2026-08-25-m4-promote-the-schema.md:307-310` says every column and row `0027` creates is a function of state that predates it, and that T7’s `record_artifact` grep tests this. That is not true once 0027 has applied and the app continues normal writes.

Existing app paths write to trigger source tables:

- `lib/storage/supabase/supabase-metadata-store.ts:202-205` upserts `playlists`.
- `lib/storage/worker-persistence.ts:9-11` calls `reserve_video_slot`.
- `supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:94-96` inserts `videos`.
- `lib/job-queue/enqueuer.ts:50-52` calls `enqueue_job`.
- `supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:26-27` inserts `jobs`.

0027 then indirectly writes M4 state from those paths:

- `03_generations.sql:141-154` creates `workspaces` for new `profiles`.
- `03_generations.sql:156-215` derives `workspace_id` for `playlists`, `videos`, and `jobs`, and inserts `workspace_videos`.
- `03_generations.sql:227-262` syncs corrections into `workspace_videos`.

The requested negative search was run:

`rg -n "record_artifact|video_artifacts_current|video_summary_current" lib app worker --glob '*.ts' --glob '*.tsx'`

It returned no matches. That proves only “no direct artifact caller.” It does **not** prove “nothing in `lib/ app/ worker/` writes any M4-created state,” because existing callers write through triggers. T9 can probably be repaired by changing the property to “all M4 state is derivable from surviving base rows and no `record_artifact`/artifact-current caller exists yet,” but v5’s current falsifiable sentence is false.

The rollback can be written, but only carefully: drop views before their base tables, drop live-table FKs/columns before `workspaces`, and drop child tables before parents. `0028 applies and schema gates go RED` only proves removal, not losslessness.

**High**

1. **T6 names the right repo command, but the one-transaction property for `db push --linked` is NOT VERIFIED.**

`docs/superpowers/plans/2026-08-25-m4-promote-the-schema.md:270-283` names `supabase db push --linked` and says the one-transaction guarantee is tied to that batching behavior. The command is correct for this repo: `docs/deploy.md:30-31` uses `supabase db push`, and CLI `2.115.0` help confirms `db push --dry-run` and `--linked`.

But the previous wire-level proof cited in r4 was for the migration runner path, not specifically `db push --linked` (`docs/reviews/plan-m4-promote-schema-r4-claude.md:37-39`). I verified CLI help, not a remote push, so the production atomicity claim remains **NOT VERIFIED**. The plan is right that `psql -f` without `--single-transaction` and dashboard paste do not provide that guarantee.

**Medium**

1. **T1’s pgcrypto CASE still has a search-path hole.**

`docs/superpowers/specs/m4/t1-blast-radius.sql:69-81` allows any `digest` in either `public` or `extensions`. But `corrections_hash_of` resolves unqualified `digest` with `set search_path = public, extensions` (`03_generations.sql:37-45`). If `public.digest(text,text)` exists alongside `extensions.digest(text,text)`, the function resolves `public` first and T1 still passes. The assertion must test the exact function resolved under the pinned search path, not just an allowlist membership.

Production today is clean: read-only measurement returned `pgcrypto` in `extensions`, with `extensions.digest(bytea,text)` and `extensions.digest(text,text)` only. So this is a gate-hole, not a current prod failure.

**Low**

1. **T1’s plan table is stale after the v5 SQL rewrite.**

The committed SQL now reports namespaces and a verdict (`docs/superpowers/specs/m4/t1-blast-radius.sql:47-81`), but the plan table still says `installed=1, callable=2` at `docs/superpowers/plans/2026-08-25-m4-promote-the-schema.md:143`. That is the old count-shaped claim r4 rejected.

2. **`supabase migration down` characterization is only help-verified.**

CLI `2.115.0` help says `migration down` “Resets applied migrations up to the last n versions” and accepts `--linked`. I did not execute it. So v5 is right to warn against it, but “drop-and-recreate” remains inferred from CLI wording, not executed.

**DID v5's OWN FIXES INTRODUCE DEFECTS?**

**Yes.** T9 is a new v5 fix, and it introduced a new Blocking defect: it claims rollback losslessness is proven by a direct `record_artifact` grep, while 0027’s triggers write M4-created state from existing app paths. The property may be salvageable with a better statement and a stronger gate, but v5’s current proof is false.

T10 did not introduce the alleged checkbox defect: `npm run test:integration` does exercise trigger-bearing paths, including `worker-persistence-rpcs.test.ts:17-18`, `:58-60`, and `job-queue-schema.test.ts:88-90`.

T2’s new order is achievable; T4-before-T2 is a decision dependency, not an unsatisfiable dependency.

T3 names the complete five-table set. `check-anon-exposure.py`’s current `MONEY_TABLES` does not include them yet, but the `c.relname = any(...)` mechanism can support the planned extension.

NOT CONVERGED
