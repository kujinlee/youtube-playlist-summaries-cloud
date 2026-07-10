-- supabase/migrations/0012_serve_model_charge.sql
-- Stage 1F-a serve-side spend governance (spec §4.2). One SECURITY DEFINER lease-reserve RPC
-- (Option A+): lease single-flight + charge-per-attempt + K-attempt bound + no release RPC.

-- 1. Lease/charge marker. force-RLS + service_role-only grants (mirrors spend_ledger, 0011):
--    writable only inside the definer RPC; never by a session client.
create table serve_model_charge (
  owner_id uuid not null references profiles(id) on delete cascade,
  doc_key text not null,                                   -- p_playlist_id::text || '/' || p_video_id
  day date not null,                                       -- (now() at time zone 'utc')::date
  lease_expires_at timestamptz not null,
  attempt_count int not null default 0 check (attempt_count >= 0),
  unique (owner_id, doc_key, day)
);
alter table serve_model_charge enable row level security;
alter table serve_model_charge force row level security;  -- owner-exemption removed; only BYPASSRLS roles write
grant select, insert, update, delete on serve_model_charge to service_role;  -- no anon/authenticated policy

-- 2. Serve-side guardrail constants (singleton row already inserted in 0011).
alter table guardrail_config add column magazine_est_cents int not null default 6  check (magazine_est_cents >= 1);
alter table guardrail_config add column max_serve_attempts int not null default 5  check (max_serve_attempts  >= 1);  -- K
alter table guardrail_config add column lease_ttl_seconds  int not null default 180 check (lease_ttl_seconds   >= 1);

-- 3. The reserve RPC. SECURITY DEFINER (owner = postgres, BYPASSRLS) so it can write the
--    service_role-only tables while being callable by a session client. auth.uid() is derived
--    internally — owner is NEVER a parameter.
create function reserve_serve_model(p_playlist_id uuid, p_video_id text)
  returns text
  language plpgsql security definer set search_path = public as $$
declare
  v_owner uuid := auth.uid();
  v_cfg guardrail_config;
  v_doc_key text;
  v_day date;
  v_promoted boolean;
  v_claimed int;
  v_existing int;
  v_lease_live boolean;
  v_result text;
begin
  if v_owner is null then raise exception 'reserve_serve_model: unauthenticated'; end if;

  -- Verify (playlist, video) owned by v_owner AND summary promoted. Else coarse 'denied' (no leak).
  select (v.data->'artifacts'->'summaryMd'->>'status') = 'promoted'
    into v_promoted
    from videos v join playlists p on p.id = v.playlist_id
    where v.playlist_id = p_playlist_id and v.video_id = p_video_id and p.owner_id = v_owner;
  if v_promoted is distinct from true then
    return 'denied';
  end if;

  select * into v_cfg from guardrail_config where id = true;
  v_doc_key := p_playlist_id::text || '/' || p_video_id;
  v_day := (now() at time zone 'utc')::date;

  -- Steps 4–5 in one sub-block: the implicit savepoint lets an at-capacity RAISE roll back the claim.
  begin
    -- 4. Claim/reclaim the lease atomically, bounded by K attempts/day.
    insert into serve_model_charge (owner_id, doc_key, day, lease_expires_at, attempt_count)
      values (v_owner, v_doc_key, v_day, now() + make_interval(secs => v_cfg.lease_ttl_seconds), 1)
    on conflict (owner_id, doc_key, day) do update
      set lease_expires_at = now() + make_interval(secs => v_cfg.lease_ttl_seconds),
          attempt_count = serve_model_charge.attempt_count + 1
      where serve_model_charge.lease_expires_at < now()
        and serve_model_charge.attempt_count < v_cfg.max_serve_attempts;
    get diagnostics v_claimed = row_count;   -- row-returned (fresh OR reclaim) is the generator signal, not xmax

    if v_claimed = 0 then
      -- No claim: either a live lease (in_flight) or all K attempts used AND the last lease expired
      -- (attempts_exhausted). Derive from BOTH attempt_count AND lease_expires_at, so a concurrent
      -- K-boundary reclaim (loser sees attempt_count = K while the winner's K-th lease is still LIVE)
      -- reports `in_flight` (single-flight guard), NOT a spurious `attempts_exhausted` (M-1 status race).
      -- No charge either way. (ON CONFLICT row-lock serialization makes this read see the committed row.)
      select attempt_count, lease_expires_at > now()
        into v_existing, v_lease_live
        from serve_model_charge
        where owner_id = v_owner and doc_key = v_doc_key and day = v_day;
      v_result := case
                    when v_lease_live then 'in_flight'                                   -- lease still held → single-flight
                    when v_existing >= v_cfg.max_serve_attempts then 'attempts_exhausted' -- expired AND K used up
                    else 'in_flight'                                                     -- expired but < K (transient; a reclaim will win next)
                  end;
    else
      -- 5. Charge THIS attempt against the daily cap (conditional-UPDATE arbiter, as enqueue_job/0011).
      insert into spend_ledger (day) values (v_day) on conflict do nothing;
      update spend_ledger set reserved_cents = reserved_cents + v_cfg.magazine_est_cents, updated_at = now()
        where day = v_day
          and reserved_cents + actual_cents + v_cfg.magazine_est_cents <= v_cfg.daily_cap_cents;
      if not found then raise exception 'serve_at_capacity' using errcode = 'PJ004'; end if;  -- rolls back the step-4 claim
      v_result := 'reserved';
    end if;
  exception
    when sqlstate 'PJ004' then
      v_result := 'at_capacity';   -- claim (fresh insert OR reclaim) rolled back to prior state; doc not bricked
  end;

  return v_result;
end $$;
revoke all on function reserve_serve_model(uuid, text) from public;
grant execute on function reserve_serve_model(uuid, text) to authenticated, anon;  -- owner derived internally
