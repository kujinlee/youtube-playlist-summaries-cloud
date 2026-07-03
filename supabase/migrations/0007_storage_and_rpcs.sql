-- supabase/migrations/0007_storage_and_rpcs.sql

-- Private bucket for all artifacts.
insert into storage.buckets (id, name, public) values ('artifacts', 'artifacts', false)
  on conflict (id) do nothing;

-- storage.objects RLS: first path segment must equal auth.uid(); service_role full access.
-- name is like '<owner_id>/<playlist_key>/<key>'. split_part(name,'/',1) = owner segment.
-- `anon` is INTENTIONAL (F5): the parent architecture (§7/§8) mandates real anonymous guest
-- sessions for the /try path, which will write blobs under their own anon uid. When unsigned,
-- auth.uid() is NULL so split_part(...) = NULL is UNKNOWN → denied. Isolation holds for anon too.
create policy "artifacts_owner_rw" on storage.objects
  for all to authenticated, anon
  using (bucket_id = 'artifacts' and split_part(name, '/', 1) = auth.uid()::text)
  with check (bucket_id = 'artifacts' and split_part(name, '/', 1) = auth.uid()::text);
create policy "artifacts_service_all" on storage.objects
  for all to service_role using (bucket_id = 'artifacts') with check (bucket_id = 'artifacts');

-- claim_video_slot: append a reservation row under a playlist row-lock; returns position + serial.
create function claim_video_slot(p_playlist_id uuid, p_video_id text)
  returns table("position" int, serial_number int)
  language plpgsql security invoker set search_path = public as $$
declare v_pos int; v_serial int;
begin
  perform 1 from playlists
    where id = p_playlist_id and (owner_id = auth.uid() or auth.role() = 'service_role')
    for update;
  if not found then raise exception 'not authorized for playlist %', p_playlist_id; end if;

  select coalesce(max(v.position) + 1, 0),
         coalesce(max((v.data->>'serialNumber')::int) + 1, 1)
    into v_pos, v_serial
    from videos v where v.playlist_id = p_playlist_id;

  insert into videos (playlist_id, owner_id, video_id, position, data)
    select p_playlist_id, pl.owner_id, p_video_id, v_pos,
           jsonb_build_object('id', p_video_id, 'serialNumber', v_serial)
      from playlists pl where pl.id = p_playlist_id
    on conflict (playlist_id, video_id) do nothing;   -- idempotent claim

  return query select v_pos, v_serial;
end $$;
revoke all on function claim_video_slot(uuid, text) from public;
grant execute on function claim_video_slot(uuid, text) to authenticated, service_role;

-- reconcile_membership: single-transaction archive/restore by playlist membership.
create function reconcile_membership(p_playlist_id uuid, p_present text[])
  returns void language plpgsql security invoker set search_path = public as $$
begin
  perform 1 from playlists
    where id = p_playlist_id and (owner_id = auth.uid() or auth.role() = 'service_role');
  if not found then raise exception 'not authorized for playlist %', p_playlist_id; end if;

  update videos set data = data || jsonb_build_object(
      'archived', not (video_id = any(p_present)),
      'removedFromPlaylist', not (video_id = any(p_present)))
    where playlist_id = p_playlist_id;
end $$;
revoke all on function reconcile_membership(uuid, text[]) from public;
grant execute on function reconcile_membership(uuid, text[]) to authenticated, service_role;

-- merge_video_data: owner-guarded jsonb field merge. ARTIFACTS-AWARE (F6): the top-level
-- `artifacts` object is deep-merged one level (so writing one artifact kind never clobbers
-- sibling kinds); every other key is a plain shallow merge. Write-once fields (videoPublishedAt/
-- addedToPlaylistAt) are preserved by the caller passing the already-`??`-guarded value (F2b);
-- the accompanying integration test (Task 11) proves re-sync does not overwrite them.
create function merge_video_data(p_playlist_id uuid, p_video_id text, p_fields jsonb)
  returns void language plpgsql security invoker set search_path = public as $$
begin
  perform 1 from playlists
    where id = p_playlist_id and (owner_id = auth.uid() or auth.role() = 'service_role');
  if not found then raise exception 'not authorized for playlist %', p_playlist_id; end if;

  update videos set
    data = (data || (p_fields - 'artifacts'))
      || case when p_fields ? 'artifacts'
           then jsonb_build_object('artifacts',
                  coalesce(data->'artifacts', '{}'::jsonb) || (p_fields->'artifacts'))
           else '{}'::jsonb end,
    updated_at = now()
   where playlist_id = p_playlist_id and video_id = p_video_id;
end $$;
revoke all on function merge_video_data(uuid, text, jsonb) from public;
grant execute on function merge_video_data(uuid, text, jsonb) to authenticated, service_role;

-- merge_video_data_bulk: apply merge_video_data semantics to many videos in ONE transaction.
-- p_patches = jsonb array of { "video_id": text, "fields": jsonb }.
create function merge_video_data_bulk(p_playlist_id uuid, p_patches jsonb)
  returns void language plpgsql security invoker set search_path = public as $$
declare it jsonb;
begin
  perform 1 from playlists
    where id = p_playlist_id and (owner_id = auth.uid() or auth.role() = 'service_role');
  if not found then raise exception 'not authorized for playlist %', p_playlist_id; end if;

  for it in select * from jsonb_array_elements(p_patches) loop
    update videos set
      data = (data || ((it->'fields') - 'artifacts'))
        || case when (it->'fields') ? 'artifacts'
             then jsonb_build_object('artifacts',
                    coalesce(data->'artifacts', '{}'::jsonb) || ((it->'fields')->'artifacts'))
             else '{}'::jsonb end,
      updated_at = now()
     where playlist_id = p_playlist_id and video_id = it->>'video_id';
  end loop;
end $$;
revoke all on function merge_video_data_bulk(uuid, jsonb) from public;
grant execute on function merge_video_data_bulk(uuid, jsonb) to authenticated, service_role;
