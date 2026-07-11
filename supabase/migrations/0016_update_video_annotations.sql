-- supabase/migrations/0016_update_video_annotations.sql

-- update_video_annotations: owner-guarded personal-annotation writer (Stage 2a Task 7).
-- Distinct from merge_video_data (UNCHANGED, left untouched by this migration):
--   * Allowlists the writable keys IN SQL ({personalScore, personalNote, archived}) — a
--     non-allowlisted key in p_set (e.g. summaryMd) is silently dropped, never written.
--   * Owner is derived ONLY from auth.uid() in the WHERE clause — there is no p_owner
--     parameter and no service_role bypass. SECURITY INVOKER + RLS both apply; this
--     function is the sole write path for personal annotations.
--   * The UPDATE always runs (even when the sliced p_set/p_clear are empty), so
--     row_count reflects row existence/ownership — callers use the returned count to
--     distinguish "no such video / not yours" (0) from "written" (>0) and 404 on 0.
create function update_video_annotations(
  p_playlist_id uuid, p_video_id text, p_set jsonb, p_clear text[]
) returns integer language plpgsql security invoker set search_path = public as $$
declare
  allow text[] := array['personalScore','personalNote','archived'];
  v_set jsonb := '{}'::jsonb; k text; n integer;
begin
  for k in select jsonb_object_keys(coalesce(p_set,'{}'::jsonb)) loop
    if k = any(allow) then v_set := v_set || jsonb_build_object(k, p_set->k); end if;
  end loop;
  update videos
     set data = (data || v_set) - (select coalesce(array_agg(c),'{}') from unnest(coalesce(p_clear,'{}')) c where c = any(allow))
   where playlist_id = p_playlist_id and video_id = p_video_id and owner_id = auth.uid();
  get diagnostics n = row_count;
  return n;
end $$;
revoke all on function update_video_annotations(uuid, text, jsonb, text[]) from public;
grant execute on function update_video_annotations(uuid, text, jsonb, text[]) to authenticated;
