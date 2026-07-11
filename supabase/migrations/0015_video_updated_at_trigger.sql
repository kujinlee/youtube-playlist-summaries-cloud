-- supabase/migrations/0015_video_updated_at_trigger.sql
--
-- Closes the gap where SupabaseMetadataStore.upsertVideo() does a direct
-- `.update({ data })` with no `updated_at` in the payload, leaving the column
-- stale. This BEFORE UPDATE trigger sets `updated_at = now()` on EVERY row
-- update — idempotent alongside the RPCs (merge_video_data,
-- merge_video_data_bulk, reconcile_membership) that already set it explicitly
-- inline; the trigger simply re-sets the same value in that case.
create or replace function set_videos_updated_at() returns trigger
  language plpgsql set search_path = public as $$
begin new.updated_at = now(); return new; end $$;
drop trigger if exists trg_videos_updated_at on videos;
create trigger trg_videos_updated_at before update on videos
  for each row execute function set_videos_updated_at();
