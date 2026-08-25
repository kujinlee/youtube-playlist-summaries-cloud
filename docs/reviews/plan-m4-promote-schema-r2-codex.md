<!-- codex-review: model=gpt-5.5 -->

**REVIEW GAP:** claude — not invoked. A session-level instruction said not to spawn subagents unless asked; I resolved that against `docs/plugins.md` and then failed to act on my own resolution. Not unavailability. The missing half ran as round 3 (`plan-m4-promote-schema-r3-claude.md`), which does not retroactively make this round dual-reviewed.

**Blocking**
- `docs/superpowers/plans/2026-08-25-m4-promote-the-schema.md:136-147` hides a rewrite behind “re-point.” Gate 1 currently concatenates spec SQL inside one rollback transaction (`docs/superpowers/specs/2026-08-03-stable-blob-addressing/verify-schema.sh:8-10`). Gate 2 is worse: it mutates two named spec files (`mutate-schema.py:25-27`), copies the spec schema plus verifier into temp (`mutate-schema.py:875-884`), then runs that copied verifier. A migration gate that applies committed files sequentially is not a path change; it is a new harness with different failure modes and new equivalence obligations. v2 still states “Must read: the migrations” as if this is mechanical.

- `docs/superpowers/plans/2026-08-25-m4-promote-the-schema.md:121-125` permits splitting the promotion across migration files as `workspaces -> workspace_id columns + NOT NULL -> workspace_videos ... -> triggers`. If those are committed sequentially in production, there is a live interval where `videos.workspace_id` and `jobs.workspace_id` are `NOT NULL` but the triggers that derive them do not exist yet. Existing writers omit the column (`supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:26-27`; asserted as unchanged at `schema/05_assert.sql:1843-1859`), and the trigger producer only appears later (`schema/03_generations.sql:156-215`). T1’s “one transaction” wording only saves this if the whole live-table change plus trigger installation is one transaction, not a chain of committed migrations.

**High**
- `docs/superpowers/plans/2026-08-25-m4-promote-the-schema.md:110-114` is not strong enough for a continuously written queue. “Either write quiescence or a re-check” is too weak: a re-check prevents `SET NOT NULL` from succeeding with nulls, but it does not prevent live enqueue/worker paths from failing while locks are held or between committed migration files. The plan needs a single production strategy: either quiesce the app/worker for the full migration window, or prove the migration holds the required table locks until all dependent triggers/FKs are installed.

- `docs/superpowers/plans/2026-08-25-m4-promote-the-schema.md:152-154` is a deferral wearing an instruction. ADR-0007 already says `serve_model_charge` duplicates `jobs` coordination vocabulary and the gate cannot see it (`docs/adr/0007-artifacts-are-an-append-only-log.md:250-258`). “Decide whether it is justified-and-suppressed or a finding” has no required artifact, owner, acceptance criterion, or gate. Before widening, the plan should require either an explicit `ALLOWED` entry with reason or a filed finding that blocks the gate.

**Medium**
- `docs/superpowers/plans/2026-08-25-m4-promote-the-schema.md:193-195` has the right T6 direction, but the measurement is too narrow. Reading `lib/html-doc/serve-doc.ts` proves the current serve path calls `reserve_serve_model` (`lib/html-doc/serve-doc.ts:122-127`) and never calls `record_artifact`; it does not prove “no caller can reach `record_artifact`” repo-wide. The gate should include a repo-wide callable-surface check for `record_artifact`, not just a serve-path read.

- `docs/superpowers/plans/2026-08-25-m4-promote-the-schema.md:146` has a command-refutable `[VERIFIED]` tag. `check-vocabulary-collisions.py:44,88` are not the spec glob. The actual schema constant/glob are `scripts/check-vocabulary-collisions.py:46` and `:96`; line 88 is text inside the `reserv` allowlist explanation.

**Low**
- The new environment split is not itself wrong, but v2 should keep its claim small. `docs/superpowers/plans/2026-08-25-m4-promote-the-schema.md:67-69` correctly says M4-alpha proves DDL/assertions only, not production-data safety. Its extra value over `verify-schema.sh` is only if T3 is rewritten to test committed migration order in a fresh Supabase project; otherwise it buys a project to re-run the same rollback proof under a different name.

NOT CONVERGED.
