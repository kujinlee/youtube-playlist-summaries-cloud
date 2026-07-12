-- supabase/migrations/0017_share_token_id_return.sql
-- Stage 2c: create_share_token now also returns the new row's id so the cloud consumption UI
-- can revoke the share it just created (POST /api/share/<id>/revoke) without a share-list route.
-- Return type changes from scalar timestamptz to table(id, expires_at) → DROP + CREATE (Postgres
-- cannot CREATE OR REPLACE across a return-type change). DROP also drops GRANT EXECUTE, so the
-- grant to authenticated is re-applied below. Ownership/hash/TTL/promoted logic is unchanged.
drop function if exists create_share_token(uuid, text, timestamptz, text);

create function create_share_token(
  p_playlist_id uuid, p_video_id text, p_expiry timestamptz, p_token_hash text
) returns table(id uuid, expires_at timestamptz) language plpgsql security definer set search_path = public as $$
declare
  v_owner uuid := auth.uid();
  v_promoted boolean;
  v_id uuid;
begin
  if v_owner is null then raise exception 'create_share_token: unauthenticated'; end if;
  if p_token_hash !~ '^[0-9a-f]{64}$' then raise exception 'create_share_token: bad hash format'; end if;
  if not (p_expiry is null
          or (p_expiry > now() and p_expiry <= now() + make_interval(days => 365) + interval '1 hour')) then
    raise exception 'create_share_token: expiry out of bounds';
  end if;
  select (v.data->'artifacts'->'summaryMd'->>'status') = 'promoted'
    into v_promoted
    from videos v join playlists p on p.id = v.playlist_id and p.owner_id = v.owner_id
    where v.playlist_id = p_playlist_id and v.video_id = p_video_id and p.owner_id = v_owner;
  if v_promoted is distinct from true then
    raise exception 'create_share_token: denied';  -- not owned or not promoted → coarse 404
  end if;
  insert into share_tokens (token_hash, owner_id, playlist_id, video_id, expires_at)
    values (p_token_hash, v_owner, p_playlist_id, p_video_id, p_expiry)
    returning share_tokens.id into v_id;
  return query select v_id, p_expiry;
end $$;

revoke all on function create_share_token(uuid, text, timestamptz, text) from public;
grant execute on function create_share_token(uuid, text, timestamptz, text) to authenticated;
