-- supabase/migrations/0014_serve_owner_budget.sql
-- Stage 1G / G1: per-owner daily serve-spend cap. Adds a per-(owner,day) cents counter enforced by a
-- second atomic arbiter in reserve_serve_model, checked BEFORE the global arbiter (spec D1/D2/D3).

-- 1. Per-owner counter (analog of spend_ledger). force-RLS + service_role-only (no client policy).
create table serve_owner_budget (
  owner_id uuid not null references profiles(id) on delete cascade,
  day date not null,
  spent_cents int not null default 0 check (spent_cents >= 0),
  primary key (owner_id, day));
alter table serve_owner_budget enable row level security;
alter table serve_owner_budget force row level security;
grant select, insert, update, delete on serve_owner_budget to service_role;

-- 2. Config column. CHECK guarantees >= one attempt always fits (spec D2).
alter table guardrail_config add column per_owner_serve_daily_cents int not null
  default 60 check (per_owner_serve_daily_cents >= magazine_est_cents);

-- 3. Replace reserve_serve_model: per-owner arbiter (5a) FIRST, then global (5b). CREATE OR REPLACE with
--    the UNCHANGED signature preserves ACL + ownership, but the definer/search_path attributes are part
--    of the definition and MUST be restated verbatim (spec Blocking/H2). Do NOT drop the function.
create or replace function reserve_serve_model(p_playlist_id uuid, p_video_id text)
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

  begin
    -- 4. Claim/reclaim the lease atomically, bounded by K attempts/day (UNCHANGED from 0012).
    insert into serve_model_charge (owner_id, doc_key, day, lease_expires_at, attempt_count)
      values (v_owner, v_doc_key, v_day, now() + make_interval(secs => v_cfg.lease_ttl_seconds), 1)
    on conflict (owner_id, doc_key, day) do update
      set lease_expires_at = now() + make_interval(secs => v_cfg.lease_ttl_seconds),
          attempt_count = serve_model_charge.attempt_count + 1
      where serve_model_charge.lease_expires_at < now()
        and serve_model_charge.attempt_count < v_cfg.max_serve_attempts;
    get diagnostics v_claimed = row_count;

    if v_claimed = 0 then
      select attempt_count, lease_expires_at > now()
        into v_existing, v_lease_live
        from serve_model_charge
        where owner_id = v_owner and doc_key = v_doc_key and day = v_day;
      v_result := case
                    when v_lease_live then 'in_flight'
                    when v_existing >= v_cfg.max_serve_attempts then 'attempts_exhausted'
                    else 'in_flight'
                  end;
    else
      -- 5a. PER-OWNER daily cap (checked FIRST) → PJ005 → 'owner_over_budget'.
      --     Over-budget owners fail here without ever locking the global spend_ledger money row.
      insert into serve_owner_budget (owner_id, day) values (v_owner, v_day) on conflict do nothing;
      update serve_owner_budget set spent_cents = spent_cents + v_cfg.magazine_est_cents
        where owner_id = v_owner and day = v_day
          and spent_cents + v_cfg.magazine_est_cents <= v_cfg.per_owner_serve_daily_cents;
      if not found then raise exception 'serve_owner_over_budget' using errcode = 'PJ005'; end if;

      -- 5b. GLOBAL daily cap (unchanged logic) → PJ004 → 'at_capacity'.
      insert into spend_ledger (day) values (v_day) on conflict do nothing;
      update spend_ledger set reserved_cents = reserved_cents + v_cfg.magazine_est_cents, updated_at = now()
        where day = v_day
          and reserved_cents + actual_cents + v_cfg.magazine_est_cents <= v_cfg.daily_cap_cents;
      if not found then raise exception 'serve_at_capacity' using errcode = 'PJ004'; end if;

      v_result := 'reserved';
    end if;
  exception
    when sqlstate 'PJ005' then v_result := 'owner_over_budget';  -- 5a claim + any 5a state rolled back
    when sqlstate 'PJ004' then v_result := 'at_capacity';        -- 5a increment + step-4 claim rolled back
  end;

  return v_result;
end $$;

-- Same signature → grants/ownership preserved; restate for auditability (spec §6).
revoke all on function reserve_serve_model(uuid, text) from public;
grant execute on function reserve_serve_model(uuid, text) to authenticated, anon;

-- P17 catalog probe helper (read-only; lets the test assert definer preservation without admin catalog access).
create function reserve_serve_model_meta()
  returns table(secdef boolean, cfg text[])
  language sql security definer set search_path = public as $$
    select p.prosecdef, p.proconfig
    from pg_proc p
    where p.oid = 'public.reserve_serve_model(uuid,text)'::regprocedure  -- exact overload, not proname match
  $$;
revoke all on function reserve_serve_model_meta() from public;
grant execute on function reserve_serve_model_meta() to authenticated, anon, service_role;
