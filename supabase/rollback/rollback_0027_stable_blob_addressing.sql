-- Reverse migration 0027 (M4: the stable-blob-addressing schema — ADR-0006, 0007, 0011).
--
-- ⛔ THIS IS NOT A MIGRATION, AND IT MUST NEVER BE MOVED INTO supabase/migrations/.
-- ------------------------------------------------------------------------------------------------
-- MEASURED 2026-08-25, with two throwaway migrations (9998 creates a table, 9999 drops it):
--
--     Applying migration 9998_probe_create.sql...
--     Applying migration 9999_probe_drop.sql...
--     {"applied":[…9998…,…9999…],"message":"Migrations applied"}
--     m4_order_probe rows in catalog: 0
--
-- `supabase migration up` applies EVERY pending file in ascending version order, in one pass. So a
-- rollback filed as `0028` runs immediately after `0027` on every fresh database — `db push` to
-- production, `db reset`, and `tests/integration/global-setup.ts` alike. The pair composes to a
-- NO-OP: M4 is created and dropped in the same command, production receives an empty milestone,
-- and the local suite tests a schema that is not there.
--
-- The five schema gates that rebuild from the spec files cannot see this; they never read the
-- migration directory. `check-live-schema.py --expect-present` can, and would go red.
--
-- HOW TO RUN IT (deliberately manual, deliberately one transaction):
--
--     docker exec -i supabase_db_youtube-playlist-summaries-cloud \
--       psql -U postgres -d postgres -v ON_ERROR_STOP=1 \
--       < supabase/rollback/rollback_0027_stable_blob_addressing.sql
--
-- ⚠ NOT `supabase migration down`, which RESETS (drop-and-recreate) and accepts --linked.
-- ⚠ `psql -f` without ON_ERROR_STOP leaves a half-reversed schema. The `begin/commit` below is the
--   guarantee; the apply command must not undermine it.
--
-- LOSSLESS, falsifiably: every column and row 0027 creates is a function of state that predates it,
-- and no caller writes any of it. `workspace_videos` holds only (workspace_id, video_id), both
-- derived (ADR-0011 removed the one column that was not).
-- ⛔ EXPIRES AT M5, the moment `record_artifact` gets a caller. Re-verify with Task 9 Step 2's grep.
--
-- ⛔ NO `cascade`, ANYWHERE. Postgres will recommend it twice. MEASURED: `drop table workspaces
--    cascade` leaves ALL SEVEN live-table triggers alive, still calling `public.workspaces` —
--    signup fails with `relation "public.workspaces" does not exist` inside
--    `ensure_workspace_for_profile()`. That is an outage, not a rollback. A failed drop means the
--    ORDER below is wrong; fix the order.
begin;

-- 1. LIVE-TABLE TRIGGERS FIRST. Their tables survive, so nothing else removes them, and the
--    column drops in step 5 fail while the `_upd_` ones still list the column.
drop trigger if exists profiles_ensure_workspace_trg        on profiles;
drop trigger if exists playlists_resolve_workspace_ins_trg  on playlists;
drop trigger if exists playlists_resolve_workspace_upd_trg  on playlists;
drop trigger if exists videos_resolve_workspace_ins_trg     on videos;
drop trigger if exists videos_resolve_workspace_upd_trg     on videos;
drop trigger if exists jobs_resolve_workspace_ins_trg       on jobs;
drop trigger if exists jobs_resolve_workspace_upd_trg       on jobs;

-- 2. VIEWS, in REVERSE creation order — collectable (:918) reads artifacts_current (:728).
drop view if exists video_generations_collectable;
drop view if exists video_artifacts_current;
drop view if exists video_summary_current;

-- 3. the FK that points videos at workspace_videos
alter table videos drop constraint if exists videos_workspace_video_fk;

-- 4. M4's own tables. Their triggers, indexes and policies go with them.
drop table if exists video_artifact_sources;
drop table if exists video_artifacts;
drop table if exists video_generations;
drop table if exists workspace_videos;

-- 5. the derived columns (now that no trigger lists them)
alter table playlists drop column if exists workspace_id;
alter table videos    drop column if exists workspace_id;
alter table jobs      drop column if exists workspace_id;

-- 6. the tenancy root, last of the tables
drop table if exists workspaces;

-- 7. FUNCTIONS — now unreferenced. 13 after ADR-0011.
--    ⛔ A WRONG SIGNATURE IS A SILENT NO-OP UNDER `if exists`: the statement succeeds, the function
--    survives, nothing reports it. Two of these thirteen were wrong in the first draft — `slot_kind`
--    takes `text` (not `artifact_kind`), and `record_artifact` takes 13 parameters (not 7). Derive
--    them, never eyeball them:
--      select p.proname||'('||pg_get_function_identity_arguments(p.oid)||')' from pg_proc p …
--    The falsifier: `check-live-schema.py --expect-absent` names any survivor.
drop function if exists ensure_workspace_for_profile();
drop function if exists resolve_workspace_from_playlist();
drop function if exists record_artifact(uuid, text, text, text, artifact_kind, text, text,
                                        int, int, text, jsonb, int, timestamptz);
drop function if exists video_generations_freeze();
drop function if exists forbid_collecting_current();
drop function if exists video_artifacts_append_only();
drop function if exists video_artifacts_generation_complete();
drop function if exists video_artifact_sources_append_only();
drop function if exists video_artifact_sources_insert_once();
drop function if exists art_summary_has_no_source();
drop function if exists slot_kind(text);
drop function if exists corrections_hash_of(text);
drop function if exists no_corrections_hash();

-- 8. the enum, last — functions above reference it in their signatures
drop type if exists artifact_kind;
commit;
