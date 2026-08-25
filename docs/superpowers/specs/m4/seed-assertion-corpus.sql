-- Seeds the minimum corpus 05_assert.sql's RE-RUNNABLE assertions need to evaluate at all.
--
-- ⚠ Runs INSIDE a transaction the caller rolls back. It must never persist.
-- ⚠ It must exercise the DERIVE path — plain inserts, with `workspace_id` NEVER written directly.
--   That is the behaviour `05_assert.sql:1843-1859` asserts, and pre-filling the column would make
--   it pass vacuously. Nothing below mentions `workspace_id`; the triggers supply it.
--
-- ⟳ TWO DRAFTS FAILED BEFORE THIS ONE RAN. Both are the same shape — a write path with a collaborator
-- nobody looked at:
--
--   1. r1 B5 (codex) — it could not insert a single row. `profiles.id` references `auth.users(id)`
--      (0001_core_schema.sql:3), so a profile cannot exist without an auth user; and
--      `playlists.playlist_url` is `not null` (0001:14) and was omitted.
--
--   2. r2 — the fix for (1) added `insert into auth.users …` ABOVE an explicit
--      `insert into profiles …`, which is a guaranteed `duplicate key value violates unique
--      constraint "profiles_pkey"`. MEASURED: `auth.users` carries trigger `on_auth_user_created`,
--      and `handle_new_user()` is
--
--          insert into public.profiles (id, is_anonymous)
--          values (new.id, coalesce(new.is_anonymous, false));
--
--      The profile row therefore ALREADY EXISTS the moment the auth user does. **There is no
--      explicit profiles insert below, and adding one back breaks this file.**
--
-- Column lists were DERIVED, not eyeballed — every NOT NULL with no default, per table:
--   auth.users: id · playlists: owner_id, playlist_key, playlist_url
--   videos: playlist_id, owner_id, video_id, position, data
-- (`profiles`: id — supplied by the trigger above.)

-- 1. the auth user. `on_auth_user_created` creates the matching `profiles` row, and after M4 the
--    `profiles_ensure_workspace_trg` on THAT row creates the workspace.
insert into auth.users (id, instance_id, aud, role, email)
  values ('00000000-0000-0000-0000-0000000000a1', '00000000-0000-0000-0000-000000000000',
          'authenticated', 'authenticated', 'seed@example.test');

-- 2. a playlist. `playlists_resolve_workspace_ins_trg` derives its workspace_id from the owner.
insert into playlists (id, owner_id, playlist_key, playlist_url)
  values ('00000000-0000-0000-0000-0000000000b1', '00000000-0000-0000-0000-0000000000a1',
          'SEED_PL', 'https://youtube.com/playlist?list=SEED_PL');

-- 3. a video. `videos_resolve_workspace_ins_trg` derives its workspace_id from the playlist AND
--    upserts the `workspace_videos` parent the FK needs.
insert into videos (playlist_id, owner_id, video_id, position, data)
  values ('00000000-0000-0000-0000-0000000000b1', '00000000-0000-0000-0000-0000000000a1',
          'seedvid001', 0, '{"id":"seedvid001","title":"seed"}'::jsonb);

-- 4. THE SEED ASSERTS ITSELF. A corpus that silently seeds nothing makes every downstream assertion
--    vacuous — and a vacuous assertion reports success. This is the falsifier for that.
do $$
declare n_ws int; n_wv int; v_ws uuid;
begin
  select count(*) into n_ws from workspaces;
  select count(*) into n_wv from workspace_videos;
  select workspace_id into v_ws from videos where video_id = 'seedvid001';
  if n_ws = 0 then
    raise exception 'SEED FAILED: no workspace — profiles_ensure_workspace_trg did not fire';
  end if;
  if v_ws is null then
    raise exception 'SEED FAILED: videos.workspace_id is null — the derive trigger did not fire';
  end if;
  if n_wv = 0 then
    raise exception 'SEED FAILED: no workspace_videos parent row was upserted';
  end if;
end $$;
