\echo === SUBJECT (named before any verdict) ===
select 'db=' || current_database()
    || ' user=' || current_user
    || ' server=' || coalesce(host(inet_server_addr())::text, 'local-socket')
    || ' now=' || now()::timestamptz(0)::text as subject;

\echo === REACHABILITY: the tables this question is about must exist ===
select 'videos_rows=' || (select count(*) from videos)::text
    || ' playlists_rows=' || (select count(*) from playlists)::text
    || ' profiles_rows=' || (select count(*) from profiles)::text as reachability;

\echo === does workspace_id already exist? (it must NOT — M4 adds it) ===
select 'videos.workspace_id_exists=' ||
       (select count(*) from information_schema.columns
         where table_schema='public' and table_name='videos' and column_name='workspace_id')::text as pre_m4;

\echo === CONTEXT: how many videos carry a non-empty corrections value ===
select 'videos_with_corrections=' ||
       (select count(*) from videos where coalesce(data->>'corrections','') <> '')::text as ctx;

\echo === CONTEXT: same video appearing more than once under one prospective workspace ===
select 'multi_row_groups=' || count(*)::text as ctx2
  from (select owner_id, video_id from videos
         group by owner_id, video_id having count(*) > 1) g;

\echo === THE FALSIFIER: groups with MORE THAN ONE DISTINCT non-empty corrections ===
select 'CONFLICTING_GROUPS=' || count(*)::text as falsifier
  from (select owner_id, video_id
          from videos
         where coalesce(data->>'corrections','') <> ''
         group by owner_id, video_id
        having count(distinct data->>'corrections') > 1) c;
\echo === ORPHANS that would defeat SET NOT NULL ===
select 'videos_with_no_playlist=' ||
  (select count(*) from videos v left join playlists p on p.id = v.playlist_id where p.id is null)::text
 || ' playlists_with_no_profile=' ||
  (select count(*) from playlists p left join profiles f on f.id = p.owner_id where f.id is null)::text
 || ' jobs_with_no_playlist=' ||
  (select count(*) from jobs j left join playlists p on p.id = j.playlist_id where p.id is null)::text
  as orphans;

\echo === row counts the NOT NULL promotions must rewrite ===
select 'playlists=' || (select count(*) from playlists)::text
    || ' videos='    || (select count(*) from videos)::text
    || ' jobs='      || (select count(*) from jobs)::text as blast_radius;

\echo === pgcrypto digest available? (M4 introduces prod's first dependency) ===
select 'pgcrypto_installed=' ||
       (select count(*) from pg_extension where extname='pgcrypto')::text
    || ' digest_callable=' ||
       (select count(*) from pg_proc p join pg_namespace n on n.oid=p.pronamespace
         where p.proname='digest')::text as pgcrypto;

\echo === does any video already sit in 2+ playlists ACROSS owners (future risk shape) ===
select 'video_ids_in_multiple_playlists=' || count(*)::text as shape
  from (select video_id from videos group by video_id having count(distinct playlist_id) > 1) x;
-- Run: docker exec -i -e PGU="$CLAUDE_RO_DATABASE_URL" supabase_db_youtube-playlist-summaries-cloud \
--        bash -c 'psql "$PGU" -tAq -v ON_ERROR_STOP=1' < docs/superpowers/specs/m4/t1-blast-radius.sql
