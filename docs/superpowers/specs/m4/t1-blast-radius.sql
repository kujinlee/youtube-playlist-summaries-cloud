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

\echo === pgcrypto: the NAMESPACE is the question, not the count ===
-- ⟳ ROUND 4 M4 — THIS USED TO COUNT ROWS AND COULD NOT FAIL. It was
--   `count(*) from pg_proc p join pg_namespace n ... where proname='digest'`
-- with `n` joined and NEVER USED, so it printed `digest_callable=2` identically whether pgcrypto sat
-- somewhere resolvable or somewhere it did not. The schema says why that matters in its own voice
-- (03_generations.sql:30-35): Supabase installs pgcrypto into `extensions`, NOT `public`, and
-- `corrections_hash_of` resolves it through a pinned `set search_path = public, extensions` (03:39).
-- That function is on the ingest path of EVERY `insert into videos` (03:185) and on the
-- post-payment corrections write (03:232).
-- FAILS IF: pgcrypto, or either `digest` overload, is in a schema outside that pinned search_path.
select 'pgcrypto_schema=' || coalesce(
         (select extnamespace::regnamespace::text from pg_extension where extname='pgcrypto'),
         'NOT-INSTALLED') as pgcrypto_ns;
select 'digest_schemas=' || coalesce(string_agg(distinct n.nspname, ','), 'NONE') as digest_ns
  from pg_proc p join pg_namespace n on n.oid = p.pronamespace
 where p.proname = 'digest';
-- ⚠ NO BACKTICKS IN \echo. psql performs shell command substitution on backquotes inside
-- meta-command arguments, exactly as bash does inside double quotes. Measured 2026-08-25: writing
-- the schema names in backticks here made psql run them, printing `sh: public: not found` into the
-- middle of the measurement. Same root cause as the --prompt-file / --body-file rule in
-- docs/plugins.md; a THIRD interpreter that eats backquotes.
\echo --- the assertion: any schema outside public/extensions is a RED T1 ---
select case
         when not exists (select 1 from pg_extension where extname='pgcrypto')
           then 'FAIL: pgcrypto not installed'
         when exists (
           select 1 from pg_proc p join pg_namespace n on n.oid = p.pronamespace
            where p.proname='digest' and n.nspname not in ('public','extensions'))
           then 'FAIL: a digest() lives outside corrections_hash_of''s pinned search_path'
         when not exists (
           select 1 from pg_proc p join pg_namespace n on n.oid = p.pronamespace
            where p.proname='digest' and n.nspname in ('public','extensions'))
           then 'FAIL: no digest() is reachable on the pinned search_path'
         else 'PASS: pgcrypto resolvable from corrections_hash_of'
       end as pgcrypto_verdict;

\echo === does any video already sit in 2+ playlists ACROSS owners (future risk shape) ===
select 'video_ids_in_multiple_playlists=' || count(*)::text as shape
  from (select video_id from videos group by video_id having count(distinct playlist_id) > 1) x;
-- Run: docker exec -i -e PGU="$CLAUDE_RO_DATABASE_URL" supabase_db_youtube-playlist-summaries-cloud \
--        bash -c 'psql "$PGU" -tAq -v ON_ERROR_STOP=1' < docs/superpowers/specs/m4/t1-blast-radius.sql
