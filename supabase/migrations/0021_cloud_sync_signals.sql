-- supabase/migrations/0021_cloud_sync_signals.sql
-- Stage 3 Cloud Sync (§5.7): per-field annotationsEditedAt stamping, corrections
-- allowlisting, conditional merge restamp, and mdGeneratedAt/mdCorrectionsHash on persist.

-- (0) DROP the old signatures FIRST. Adding a defaulted `p_edited_at` parameter to
--     update_video_annotations / merge_video_data with `create or replace` would create a
--     NEW overload and LEAVE the old 4-arg / 3-arg functions in place. A caller that omits
--     p_edited_at (e.g. SupabaseMetadataStore.updateVideoAnnotations' 4-key rpc call) would
--     then match BOTH overloads → PostgREST error PGRST203 "could not choose the best
--     candidate function" → the live Archive button + annotation/field writes break. Dropping
--     the old signatures makes the 3/4-key call resolve unambiguously to the single surviving
--     defaulted function. (persist_summary keeps its 5-arg signature unchanged → no drop needed.)
drop function if exists update_video_annotations(uuid, text, jsonb, text[]);
drop function if exists merge_video_data(uuid, text, jsonb);

-- (1) update_video_annotations: add corrections to the allowlist; stamp per-field
--     annotationsEditedAt for each Class-B field set OR cleared; accept an explicit
--     sync-path timestamp (defaults to now() for the user-edit path).
create or replace function update_video_annotations(
  p_playlist_id uuid, p_video_id text, p_set jsonb, p_clear text[],
  p_edited_at timestamptz default now()
) returns integer language plpgsql security invoker set search_path = public as $$
declare
  allow text[] := array['personalScore','personalNote','corrections','archived'];
  classb text[] := array['personalScore','personalNote','corrections'];
  v_set jsonb := '{}'::jsonb;
  v_stamp jsonb := '{}'::jsonb;
  v_clear text[] := '{}';
  k text; n integer;
  ts text := to_char(p_edited_at at time zone 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.MS"Z"');
begin
  for k in select jsonb_object_keys(coalesce(p_set,'{}'::jsonb)) loop
    if k = any(allow) then
      v_set := v_set || jsonb_build_object(k, p_set->k);
      if k = any(classb) then v_stamp := v_stamp || jsonb_build_object(k, ts); end if;
    end if;
  end loop;
  -- clears: only allowlisted; each Class-B clear stamps its timestamp
  select coalesce(array_agg(c),'{}') into v_clear
    from unnest(coalesce(p_clear,'{}')) c where c = any(allow);
  foreach k in array v_clear loop
    if k = any(classb) then v_stamp := v_stamp || jsonb_build_object(k, ts); end if;
  end loop;

  -- Only touch annotationsEditedAt when there IS a Class-B stamp; an archived-only
  -- (or empty) write must not create an empty annotationsEditedAt:{} (§4.1 "archived-only
  -- write restamps nothing").
  update videos
     set data = case when v_stamp <> '{}'::jsonb
                  then jsonb_set((data || v_set) - v_clear, '{annotationsEditedAt}',
                         coalesce(data->'annotationsEditedAt','{}'::jsonb) || v_stamp, true)
                  else (data || v_set) - v_clear end
   where playlist_id = p_playlist_id and video_id = p_video_id and owner_id = auth.uid();
  get diagnostics n = row_count;
  return n;
end $$;
revoke all on function update_video_annotations(uuid, text, jsonb, text[], timestamptz) from public;
grant execute on function update_video_annotations(uuid, text, jsonb, text[], timestamptz) to authenticated;

-- (2) merge_video_data: conditional annotationsEditedAt restamp when a Class-B key is
--     present in the patch (a bare MD-finalize / artifact / membership write must NOT bump it).
create or replace function merge_video_data(
  p_playlist_id uuid, p_video_id text, p_fields jsonb,
  p_edited_at timestamptz default now()
) returns void language plpgsql security invoker set search_path = public as $$
declare
  classb text[] := array['personalScore','personalNote','corrections'];
  v_stamp jsonb := '{}'::jsonb; k text;
  ts text := to_char(p_edited_at at time zone 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.MS"Z"');
begin
  perform 1 from playlists
    where id = p_playlist_id and (owner_id = auth.uid() or auth.role() = 'service_role');
  if not found then raise exception 'not authorized for playlist %', p_playlist_id; end if;

  foreach k in array classb loop
    if p_fields ? k then v_stamp := v_stamp || jsonb_build_object(k, ts); end if;
  end loop;

  update videos set
    data = (data || (p_fields - 'artifacts'))
      || case when p_fields ? 'artifacts'
           then jsonb_build_object('artifacts',
                  coalesce(data->'artifacts', '{}'::jsonb) || (p_fields->'artifacts'))
           else '{}'::jsonb end
      || case when v_stamp <> '{}'::jsonb
           then jsonb_build_object('annotationsEditedAt',
                  coalesce(data->'annotationsEditedAt','{}'::jsonb) || v_stamp)
           else '{}'::jsonb end,
    updated_at = now()
   where playlist_id = p_playlist_id and video_id = p_video_id;
end $$;
revoke all on function merge_video_data(uuid, text, jsonb, timestamptz) from public;
grant execute on function merge_video_data(uuid, text, jsonb, timestamptz) to authenticated, service_role;

-- (3) persist_summary: SAME 5-arg signature (no drop needed). Body copied VERBATIM from 0009
--     (git show HEAD:supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql)
--     with ONLY two additional keys added to the summary-owned jsonb_build_object:
--     'mdGeneratedAt' and 'mdCorrectionsHash' (§5.7).
create or replace function persist_summary(p_owner_id uuid, p_playlist_id uuid, p_video_id text, p_video jsonb, p_artifact_status text)
  returns void language plpgsql security invoker set search_path = public as $$
declare v_count int;
begin
  if not (p_owner_id = auth.uid() or auth.role() = 'service_role') then raise exception 'not authorized'; end if;
  perform 1 from playlists where id = p_playlist_id and owner_id = p_owner_id;
  if not found then raise exception 'playlist % not owned by %', p_playlist_id, p_owner_id; end if;
  -- Whitelist: a summary persist writes ONLY summary-owned fields and preserves EVERYTHING else.
  -- Layering (right wins): (1) p_video defaults — used only for keys the existing row lacks, i.e. a
  -- first-time write off a bare reserve row; (2) the existing row's NON-summary fields win back over
  -- those defaults, so a possibly-stale job payload can never revert operational/membership/metadata/
  -- other-feature state (archived, removedFromPlaylist, playlistIndex, title, timestamps, dig
  -- artifacts, personal notes, …) that a concurrent writer (reconcile_membership / merge_video_data /
  -- upsertVideo) may have changed while this job ran; (3) the top-level summaryMd key resolved from
  -- payload-or-existing; (4) the artifacts.summaryMd merge with a lock-consistent, KEY-SCOPED
  -- monotonic status. The UPDATE's row lock serializes concurrent persists (Task-2 lost-update fix).
  update videos v set
    data = (p_video - 'artifacts')                            -- (1) payload defaults — fill keys a first-time bare row lacks
      || (v.data - 'artifacts')                               -- (2) ALL existing fields win back: never clobber non-summary
                                                              --     state AND never drop existing summary fields on a
                                                              --     status-only persist (p_video omits them)
      || jsonb_strip_nulls(jsonb_build_object(                -- (3) re-apply ONLY the summary-owned fields p_video PROVIDES
           'language', p_video->'language',                   --     (present ones win; absent → existing preserved by (2))
           'ratings', p_video->'ratings',
           'overallScore', p_video->'overallScore',
           'processedAt', p_video->'processedAt',
           'videoType', p_video->'videoType',
           'audience', p_video->'audience',
           'tags', p_video->'tags',
           'tldr', p_video->'tldr',
           'takeaways', p_video->'takeaways',
           'docVersion', p_video->'docVersion',
           'mdGeneratedAt', p_video->'mdGeneratedAt',
           'mdCorrectionsHash', p_video->'mdCorrectionsHash'))
      || jsonb_strip_nulls(jsonb_build_object('summaryMd', coalesce(p_video->>'summaryMd', v.data->>'summaryMd')))
      || jsonb_build_object('artifacts',
           coalesce(v.data->'artifacts', '{}'::jsonb)
           || jsonb_build_object('summaryMd', jsonb_build_object(
                'key', coalesce(p_video->>'summaryMd', v.data->'artifacts'->'summaryMd'->>'key'),
                -- Monotonic status, KEY-SCOPED: preserve 'promoted' against a stale 'committed' write
                -- ONLY when the artifact key is unchanged. A different key is a genuinely new artifact
                -- that IS in committed state, so it must be allowed through (else the row would claim a
                -- promoted artifact for a blob that has not been promoted yet).
                'status', case
                            when v.data->'artifacts'->'summaryMd'->>'status' = 'promoted'
                                 and p_artifact_status = 'committed'
                                 and v.data->'artifacts'->'summaryMd'->>'key'
                                     = coalesce(p_video->>'summaryMd', v.data->'artifacts'->'summaryMd'->>'key')
                              then 'promoted'
                            else p_artifact_status end))),
    updated_at = now()
   where v.playlist_id = p_playlist_id and v.video_id = p_video_id and v.owner_id = p_owner_id;
  get diagnostics v_count = row_count;
  if v_count = 0 then raise exception 'persist_summary: no video row for %/%', p_playlist_id, p_video_id; end if;
end $$;
revoke all on function persist_summary(uuid,uuid,text,jsonb,text) from public;
grant execute on function persist_summary(uuid,uuid,text,jsonb,text) to authenticated, service_role;
