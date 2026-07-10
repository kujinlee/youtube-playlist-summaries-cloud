-- supabase/migrations/0013_share_tokens.sql
-- Stage 1F-b share tokens (spec §4.1/§4.2). force-RLS + service_role-only grants (mirrors
-- serve_model_charge, 0012); all writes go through SECURITY DEFINER RPCs that derive the
-- owner from auth.uid() internally. MAX_SHARE_TTL_DAYS = 365 (inlined in the RPC bound).

create table share_tokens (
  id            uuid primary key default gen_random_uuid(),
  token_hash    text not null unique check (token_hash ~ '^[0-9a-f]{64}$'),  -- lowercase hex of sha256; plaintext never stored
  owner_id      uuid not null references profiles(id) on delete cascade,
  playlist_id   uuid not null,
  video_id      text not null,
  created_at    timestamptz not null default now(),
  expires_at    timestamptz,                           -- null = never
  revoked_at    timestamptz
);
alter table share_tokens enable row level security;
alter table share_tokens force row level security;      -- only BYPASSRLS roles read/write
grant select, insert, update, delete on share_tokens to service_role;  -- no anon/authenticated policy
create index share_tokens_owner_idx on share_tokens (owner_id);

-- Ownership + promoted predicate helper (inlined; same shape as reserve_serve_model, 0012:44-47).
create function create_share_token(
  p_playlist_id uuid, p_video_id text, p_expiry timestamptz, p_token_hash text
) returns timestamptz language plpgsql security definer set search_path = public as $$
declare
  v_owner uuid := auth.uid();
  v_promoted boolean;
begin
  if v_owner is null then raise exception 'create_share_token: unauthenticated'; end if;
  if p_token_hash !~ '^[0-9a-f]{64}$' then raise exception 'create_share_token: bad hash format'; end if;
  -- Trust-boundary TTL bound (+1h grace absorbs app/DB clock skew; still rejects > ~1 year).
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
    values (p_token_hash, v_owner, p_playlist_id, p_video_id, p_expiry);
  return p_expiry;
end $$;

create function revoke_share_token(p_id uuid) returns boolean
  language plpgsql security definer set search_path = public as $$
declare v_owner uuid := auth.uid(); v_rows int;
begin
  if v_owner is null then raise exception 'revoke_share_token: unauthenticated'; end if;
  update share_tokens set revoked_at = now()
    where id = p_id and owner_id = v_owner and revoked_at is null;
  get diagnostics v_rows = row_count;
  return v_rows > 0;
end $$;

create function revoke_all_share_tokens(p_playlist_id uuid, p_video_id text) returns integer
  language plpgsql security definer set search_path = public as $$
declare v_owner uuid := auth.uid(); v_rows int;
begin
  if v_owner is null then raise exception 'revoke_all_share_tokens: unauthenticated'; end if;
  update share_tokens set revoked_at = now()
    where owner_id = v_owner and playlist_id = p_playlist_id and video_id = p_video_id and revoked_at is null;
  get diagnostics v_rows = row_count;
  return v_rows;
end $$;

create function list_share_tokens(p_playlist_id uuid, p_video_id text)
  returns table(id uuid, created_at timestamptz, expires_at timestamptz, revoked_at timestamptz)
  language plpgsql security definer set search_path = public as $$
declare v_owner uuid := auth.uid();
begin
  if v_owner is null then raise exception 'list_share_tokens: unauthenticated'; end if;
  return query
    select t.id, t.created_at, t.expires_at, t.revoked_at from share_tokens t
    where t.owner_id = v_owner and t.playlist_id = p_playlist_id and t.video_id = p_video_id
    order by t.created_at;
end $$;

revoke all on function create_share_token(uuid, text, timestamptz, text) from public;
revoke all on function revoke_share_token(uuid) from public;
revoke all on function revoke_all_share_tokens(uuid, text) from public;
revoke all on function list_share_tokens(uuid, text) from public;
grant execute on function create_share_token(uuid, text, timestamptz, text) to authenticated;
grant execute on function revoke_share_token(uuid) to authenticated;
grant execute on function revoke_all_share_tokens(uuid, text) to authenticated;
grant execute on function list_share_tokens(uuid, text) to authenticated;
