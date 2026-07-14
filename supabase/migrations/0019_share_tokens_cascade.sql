-- supabase/migrations/0019_share_tokens_cascade.sql
-- Completes the delete surface (plan Task 6 / spec §B2, §B4):
--   (a) share_tokens.playlist_id had NO FK (0013) — deleting a playlist orphaned its share
--       tokens. Add the same composite cascade FK already used for videos/jobs (0001/0009) so
--       `DELETE playlists` cascades ALL DB state atomically (one transaction, no RPC).
--   (b) the existing playlist cancel path (app/api/jobs/cancel + SupabaseJobQueue.listByPlaylist)
--       filters job_kind='summary' and would miss `dig` jobs. Add a SECURITY DEFINER RPC that
--       cancels ALL non-terminal jobs (any kind) for a playlist, owner-guarded via auth.uid(),
--       mirroring the per-job request_cancel_job (0010).

-- Defensive one-shot: remove any pre-existing share_tokens rows orphaned by a playlist delete
-- that happened BEFORE this cascade FK existed. Once the FK below is in place this delete can
-- never find a match again (RI prevents new orphans) — it exists solely so historical orphans
-- don't block the ALTER ... ADD CONSTRAINT from succeeding. Untested directly (see plan Task 6
-- behavior 1 / spec §B2): a clean ALTER is the only available signal that this ran without error.
delete from share_tokens st
  where not exists (select 1 from playlists p
                    where p.id = st.playlist_id and p.owner_id = st.owner_id);

-- Composite (playlist_id, owner_id) — not bare playlist_id — matches videos/jobs and keeps the
-- cross-tenant guarantee (a share token's owner always equals its playlist's owner). RI actions
-- bypass RLS, so this cascade fires even though share_tokens is force-RLS with no authenticated
-- policy — the same mechanism already relied on for videos/jobs.
alter table share_tokens
  add constraint share_tokens_playlist_owner_fk
  foreign key (playlist_id, owner_id) references playlists(id, owner_id) on delete cascade;

-- Cascade deletes scan children by playlist_id; index it.
create index if not exists share_tokens_playlist_id_idx on share_tokens (playlist_id);

-- Cancel ALL non-terminal jobs (any job_kind) for a playlist. Mirrors request_cancel_job (0010)
-- but scoped to a whole playlist; owner-guarded via auth.uid() (no separate ownership check
-- needed — the WHERE clause itself is the guard, same pattern as 0010).
create or replace function request_cancel_playlist_jobs(p_playlist_id uuid) returns int
  language plpgsql security definer set search_path = public as $$
declare n int;
begin
  update jobs
     set cancel_requested = true,
         status = case when status = 'queued' then 'cancelled' else status end,
         updated_at = now()
   where playlist_id = p_playlist_id
     and owner_id = auth.uid()
     and status in ('queued','active');
  get diagnostics n = row_count;
  return n;
end $$;
revoke all on function request_cancel_playlist_jobs(uuid) from public;
grant execute on function request_cancel_playlist_jobs(uuid) to authenticated, service_role;
