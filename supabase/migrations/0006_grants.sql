-- supabase/migrations/0006_grants.sql
-- The pinned Supabase CLI default (auto_expose_new_tables unset) does NOT auto-grant
-- the Data API roles (anon, authenticated, service_role) on new public tables. RLS only
-- FILTERS rows a role can already access; without a base table GRANT, PostgREST returns
-- 42501 permission denied. Grant CRUD to all three Data API roles.
--
-- anon/authenticated: forced RLS + the owner policies (0002) still confine every request
--   to owner_id = auth.uid().
-- service_role: has BYPASSRLS (the trusted worker path, spec §5.4 — writes with owner_id
--   set explicitly), but BYPASSRLS does NOT bypass table-level GRANTs, so it still needs
--   this grant to use the Data API. Its confinement is enforced by lib/supabase/service.ts
--   (server-only + import-graph scan), NOT by withholding DB privileges.
--
-- GRANT is idempotent, so this is also safe on any local image that still ships the legacy
-- auto-grant seed (hosted-parity determinism).
grant select, insert, update, delete on public.profiles  to anon, authenticated, service_role;
grant select, insert, update, delete on public.playlists to anon, authenticated, service_role;
grant select, insert, update, delete on public.videos    to anon, authenticated, service_role;
