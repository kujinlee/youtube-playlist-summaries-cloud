<!-- codex-review: model=gpt-5.5 -->

**Blocking**

1. Task 9 cannot pass its own gates after `0027` is applied. Task 3 wires the live gate as `--expect-absent` in `check-schema-gates.sh` (`docs/superpowers/plans/2026-08-25-m4-promote-the-schema-v2.md:307`), but Task 9 runs `./scripts/check-schema-gates.sh` after M4-α (`:703-704`). That live gate must fail on the migrated stack. Task 4 also makes `verify-schema.sh` exit 2 when `0027` is already applied (`:350-355`), while `check-schema-gates.sh` treats any non-zero gate as failure (`scripts/check-schema-gates.sh:22-27`). So the required “all green” milestone gate is structurally unsatisfiable.

2. `0028` is not a rollback as written. The drop order fails without `cascade`: `video_generations_collectable` depends on `video_artifacts_current` (`04_artifacts.sql:918-924`), but `0028` drops `video_artifacts_current` first (`plan:479-481`). It also leaves live-table triggers behind: `profiles_ensure_workspace_trg` (`03_generations.sql:152-154`), playlist/video/job resolve triggers (`:198-215`), plus their functions (`:141-190`). It leaves functions and type objects too: `no_corrections_hash` (`:15`), `corrections_hash_of` (`:37`), `artifact_kind` (`:264`), `slot_kind` (`04_artifacts.sql:22`), `record_artifact` (`:354`), and all artifact trigger functions (`:795`, `:990`, `:1071`, `:1101`, `:1136`, `:1176`). Command used to enumerate: `rg -n "^create ...|^alter table .*add constraint|..." docs/.../schema/{01_workspaces,03_generations,04_artifacts}.sql`.

3. ADR-0011 is not implemented across the assertion layer. The plan removes `workspace_videos.corrections` and `corrections_hash` in schema, but `05_assert.sql` still asserts those columns and the sync trigger: `workspace_videos where corrections_hash is null` (`05_assert.sql:62`), insert into `workspace_videos (... corrections_hash)` (`:119`), update `workspace_videos set corrections_hash` (`:819-821`), anti-drift checks reading `wv.corrections_hash, wv.corrections` (`:899-905`), and sync function inventory (`:1315-1319`). Task 8 says `05_assert.sql` gets “classification comments only” (`plan:571`), so these break after Task 1/2. Search command used: `rg -n "corrections|corrections_hash|mdCorrectionsHash" docs/.../schema supabase/migrations scripts lib app worker --glob "*.sql" --glob "*.py" --glob "*.ts" --glob "*.tsx"`.

4. Task 2’s own proof command is false as written. It says `grep -rn "corrections_hash" .../schema/` should find only the two function definitions in `03` (`plan:180-184`), but the command includes `05_assert.sql`, which currently has many `corrections_hash` references (`05_assert.sql:62`, `:65`, `:119`, `:820`, `:899`, `:917`, etc.). This is the repeated “fixed at one of two sites” defect, now across schema and assertions.

5. Task 8’s seed corpus does not satisfy `0001_core_schema.sql`. `profiles.id` references `auth.users(id)` (`supabase/migrations/0001_core_schema.sql:3`), but the seed inserts only `profiles` (`plan:598`). `playlists.playlist_url` is `not null` (`0001_core_schema.sql:14`), but the seed inserts only `(id, owner_id, playlist_key)` (`plan:599-600`). The harness cannot reach the assertions.

6. Task 8’s `awk '/@RE-RUNNABLE/{p=1} p'` selector is unsafe (`plan:628-630`). It has no stop condition, so after the first `@RE-RUNNABLE` marker it captures everything to EOF, including any later `@MIGRATION-ONLY` block. Current `05_assert.sql` has migration-only backfill assertions at `:54-72` and later anti-drift/corrections-copy assertions at `:885-919`; classification comments alone cannot make this selector correct.

7. `check-live-schema.py` is too narrow to prove applied/absent M4. Its `verdict()` only checks five tables and three `workspace_id` columns (`plan:263-278`). It ignores views, triggers, functions, type, indexes, constraints, policies, and live-table triggers. Therefore `--expect-absent` can pass while `0028` leaves functions/type/triggers behind. `--expect-present` can pass while views or triggers are missing.

**High**

1. The line citations are correct for the starting file but unstable inside the prescribed edit sequence. Task 1 cites `03_generations.sql:52,61,89-95,183-185,227-236,253-262` (`plan:57`), and those ranges currently match (`03_generations.sql:52`, `:61`, `:89-95`, `:183-185`, `:227-236`, `:253-262`). But Step 2 deletes two lines and adds a comment above `create table` (`plan:73-80`), shifting every later citation before Step 3. Task 2 has the same shape: deleting/replacing around `04_artifacts.sql:717` shifts the later `:777` site (`plan:139`, `04_artifacts.sql:717`, `:777`). A worker following line numbers literally will edit the wrong later lines.

2. Task 3’s red-path proof cannot work as described. It opens `psql` through `docker exec` with a heredoc containing `begin; create table ...` (`plan:293-297`), then says “in the same session run `--expect-absent`” (`:300`). `check-live-schema.py` opens its own connection, so it cannot see an uncommitted table in the prior `psql` session; and the heredoc session has ended.

3. Task 5 under-specifies the ratchet cleanup. It tells the implementer to delete only `art_pending_*` entries and add `video_artifact_sources` coverage (`plan:405-407`), but ADR-0011 also removes `sync_corrections_to_workspace_video`, still listed in `check-guard-coverage.py:119-122` and `:168-169`. It fixes the sentinel docstring (`plan:409-411`) but not the live nullable-column inventory entry `("workspace_videos", "corrections")` (`scripts/check-sentinel-meanings.py:70-71`).

**Medium**

1. Gate numbering is inconsistent. Task 3 says “add as gate 7/7” (`plan:199`, `:302`) but the command labels it `7/8` (`:307`). Task 7 adds `0/8` later (`:553-554`). The existing script is still `1/6` through `6/6` (`scripts/check-schema-gates.sh:29-46`). The milestone says nine checks numbered `0-8` (`plan:770-771`). The arithmetic is recoverable, but not as written.

2. The plan claims `05_assert.sql` has an arbitrary SQL executor at `:37` and deleter at `:2207` (`plan:22`). Those lines are currently accurate (`05_assert.sql:37`, `:2207`), but after Task 8 classification edits, those citations may drift unless anchored by search text.

**Low**

none

**IS THIS PLAN EXECUTABLE AS WRITTEN?**

No. A competent engineer could infer the intended design, but not follow the plan end to end without re-deriving gate polarity, rollback contents/order, assertion slicing, seed validity, and the post-ADR corrections sweep.

NOT CONVERGED
