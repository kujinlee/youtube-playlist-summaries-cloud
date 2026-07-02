-- supabase/migrations/0005_reorder_helper.sql
-- SECURITY INVOKER: runs under the caller's RLS (owner-only). One transaction so the
-- DEFERRABLE INITIALLY DEFERRED position constraint is validated at COMMIT.
create function reorder_videos(p_playlist_id uuid, items jsonb)
  returns void language plpgsql security invoker set search_path = public as $$
declare it jsonb;
begin
  -- Codex H7: explicit ownership guard (defense-in-depth over the caller-RLS no-op).
  -- A user who does not own the playlist (or whose RLS hides it) sees no matching row.
  if not exists (
    select 1 from playlists
     where id = p_playlist_id
       and (owner_id = auth.uid() or auth.role() = 'service_role')
  ) then
    raise exception 'not authorized for playlist %', p_playlist_id;
  end if;

  for it in select * from jsonb_array_elements(items) loop
    update videos set position = (it->>'position')::int, updated_at = now()
     where playlist_id = p_playlist_id and video_id = it->>'video_id';
  end loop;
end $$;

-- Codex H7: not callable by anon/PUBLIC by default; only authenticated + service_role.
revoke all on function reorder_videos(uuid, jsonb) from public, anon;
grant execute on function reorder_videos(uuid, jsonb) to authenticated, service_role;
