-- supabase/migrations/0006_grants.sql
-- The pinned Supabase CLI default (auto_expose_new_tables unset) does NOT auto-grant
-- the Data API roles (anon, authenticated) on new public tables. RLS only FILTERS rows a
-- role can already access; without a base table GRANT, PostgREST returns 42501 permission
-- denied. Grant CRUD to both roles; forced RLS + the owner policies (0002) still confine
-- every role to owner_id = auth.uid(). GRANT is idempotent, so this is also safe on any
-- local image that still ships the legacy auto-grant seed (hosted-parity determinism).
grant select, insert, update, delete on public.profiles  to anon, authenticated;
grant select, insert, update, delete on public.playlists to anon, authenticated;
grant select, insert, update, delete on public.videos    to anon, authenticated;
