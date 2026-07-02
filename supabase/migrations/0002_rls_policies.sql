-- supabase/migrations/0002_rls_policies.sql
create policy profiles_self  on profiles  for all
  using (id = auth.uid())        with check (id = auth.uid());
create policy playlists_owner on playlists for all
  using (owner_id = auth.uid())  with check (owner_id = auth.uid());
create policy videos_owner    on videos    for all
  using (owner_id = auth.uid())  with check (owner_id = auth.uid());
