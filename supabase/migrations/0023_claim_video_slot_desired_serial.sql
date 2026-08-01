-- supabase/migrations/0023_claim_video_slot_desired_serial.sql
--
-- A1 of the serial-coherence slice. Two changes to claim_video_slot, one new and one a fix.
--
-- 1. NEW — p_desired_serial. `base`, the address of every derived blob (models/<base>.json,
--    dig/<base>/<sectionId>.r<V>.md), is `<serial>_<slug>`. Cloud-sync copies the sender's
--    summaryMd KEY verbatim while letting the receiver allocate its own serial, so the receiver row
--    says serialNumber: 7 beside a file named 003_alpha.md and every blob under dig/003_alpha/ is
--    silently orphaned. The receiver must be able to ASK for the sender's serial.
--
--    Adoption is conditional and resolved HERE, under the playlist row-lock the function already
--    takes, so two racing claims for one serial cannot both win. On collision the function allocates
--    max+1 and returns it; the caller compares against what it asked for and aborts that video.
--    It never substitutes silently — a wrong serial is worse than a refusal, because it is the
--    incoherence the parameter exists to remove.
--
-- 2. FIX — the returned serial was a PHANTOM. The old body computed v_serial, then inserted with
--    `on conflict (playlist_id, video_id) do nothing`, then returned the value it had computed —
--    even when the insert no-oped because the row already existed. Callers got a serial that was
--    never stored. `reserve_video_slot` (0009:88-99) already had the right shape: re-select after
--    the insert. This adopts it, and short-circuits an existing row before touching anything.
--
-- Why DROP and not CREATE OR REPLACE: Postgres identifies a function by its full argument-type
-- signature, so adding a defaulted parameter CREATES A SECOND FUNCTION. Every existing 2-arg call
-- would then match both candidates and fail with "function is not unique". Privileges do not
-- survive the drop, so the revoke/grant is re-issued below.

drop function if exists claim_video_slot(uuid, text);

create function claim_video_slot(p_playlist_id uuid, p_video_id text, p_desired_serial int default null)
  returns table("position" int, serial_number int)
  language plpgsql security invoker set search_path = public as $$
declare v_pos int; v_serial int;
begin
  -- Reject before any I/O; mirrors assertDesiredSerial in lib/storage/metadata-store.ts. NULL means
  -- "no preference" and is the only non-positive value accepted.
  if p_desired_serial is not null and p_desired_serial <= 0 then
    raise exception 'claim_video_slot: desired serial must be a positive integer, got %', p_desired_serial;
  end if;

  perform 1 from playlists
    where id = p_playlist_id and (owner_id = auth.uid() or auth.role() = 'service_role')
    for update;
  if not found then raise exception 'not authorized for playlist %', p_playlist_id; end if;

  -- An EXISTING row's persisted values win. Returning a computed serial for a row that already has
  -- one is the phantom described above.
  select v.position, (v.data->>'serialNumber')::int into v_pos, v_serial
    from videos v where v.playlist_id = p_playlist_id and v.video_id = p_video_id;
  if found then
    if v_serial is null then
      -- Row predates the serial prefix. FILL it (a merge, never a replacement) and return the value
      -- now stored, matching LocalFsMetadataStore. Deliberately NOT reserve_video_slot's invariant
      -- raise: that function is the worker's accessor on a path that must not write, whereas a
      -- claim is already a write and filling a gap can only add.
      select coalesce(max((v.data->>'serialNumber')::int) + 1, 1) into v_serial
        from videos v where v.playlist_id = p_playlist_id;
      update videos set data = data || jsonb_build_object('serialNumber', v_serial), updated_at = now()
        where playlist_id = p_playlist_id and video_id = p_video_id;
    end if;
    return query select v_pos, v_serial;
    return;
  end if;

  select coalesce(max(v.position) + 1, 0),
         coalesce(max((v.data->>'serialNumber')::int) + 1, 1)
    into v_pos, v_serial
    from videos v where v.playlist_id = p_playlist_id;

  -- Adopt only when free. Under the row-lock taken above, this read cannot race a sibling claim.
  if p_desired_serial is not null
     and not exists (select 1 from videos v
                      where v.playlist_id = p_playlist_id
                        and (v.data->>'serialNumber')::int = p_desired_serial) then
    v_serial := p_desired_serial;
  end if;

  insert into videos (playlist_id, owner_id, video_id, position, data)
    select p_playlist_id, pl.owner_id, p_video_id, v_pos,
           jsonb_build_object('id', p_video_id, 'serialNumber', v_serial)
      from playlists pl where pl.id = p_playlist_id
    on conflict (playlist_id, video_id) do nothing;   -- idempotent claim

  -- Re-select: on conflict the row already existed and ITS values, not the ones computed above,
  -- are the truth (0009:88-99).
  select v.position, (v.data->>'serialNumber')::int into v_pos, v_serial
    from videos v where v.playlist_id = p_playlist_id and v.video_id = p_video_id;

  return query select v_pos, v_serial;
end $$;
revoke all on function claim_video_slot(uuid, text, int) from public;
grant execute on function claim_video_slot(uuid, text, int) to authenticated, service_role;
