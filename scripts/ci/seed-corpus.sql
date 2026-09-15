-- ONE auth user. Everything else the behavioural gates need is provisioned by the repo's own
-- triggers, and that is the entire point of seeding it this way.
--
-- ⭐ WHY A SEED IS NEEDED AT ALL. Three gates assert BEHAVIOUR rather than shape — gate 1
-- (`verify-schema.sh`), gate 2 (`mutate-schema.py`) and gate 8 (`run-schema-assertions.sh`) — and
-- they build their fixtures from rows that already exist. On the developer's stack those rows are
-- there as a side effect of using the app; a database built from migrations has none. MEASURED:
-- the gates refuse, correctly and loudly, with
--
--     ERROR: CANNOT RUN — no workspaces exist, so every fixture below would be NULL-keyed
--
-- which is the right behaviour and NOT something to paper over — it is why this file exists rather
-- than the gates being taught to tolerate an empty database.
--
-- ⛔ WHY ONE `auth.users` ROW AND NOTHING ELSE. Inserting a profile or a workspace directly would
-- fabricate state the application can never produce, and any drift between the fixture and the real
-- provisioning path would be invisible — the fixture would keep working precisely when provisioning
-- broke. MEASURED on the CI image: a single `auth.users` insert yields
--
--     users=1  profiles=1  workspaces=1
--
-- through `handle_new_user()` and the provisioning migration. So the seed exercises the real path,
-- and if that path ever breaks, this file fails instead of hiding it.

-- ⛔ TWO USERS, NOT ONE, AND THE SECOND IS NOT A SPARE. Gates 1 and 2 refuse a single-workspace
-- database outright:
--
--     CANNOT RUN — only 1 workspace(s); t_ws and t_w2 are the SAME row (…), so the cross-tenant
--     assertions would be vacuous. Seed a second workspace.
--
-- That refusal is the gates protecting themselves from a corpus in which every isolation assertion
-- compares a tenant to itself and passes for free. A one-user seed would have produced a suite that
-- ran, went green, and proved nothing about tenant isolation — the exact shape this repo files
-- findings about. The second user is what makes RLS falsifiable.
insert into auth.users (id, aud, role, email, instance_id)
values (gen_random_uuid(), 'authenticated', 'authenticated',
        'ci-seed-a@example.test', '00000000-0000-0000-0000-000000000000'),
       (gen_random_uuid(), 'authenticated', 'authenticated',
        'ci-seed-b@example.test', '00000000-0000-0000-0000-000000000000');

-- ⛔ ONE PLAYLIST PER WORKSPACE — user data, so it is inserted directly, unlike the workspace above.
-- Gate 1's ingest assertion opens with `select id, workspace_id into v_pl, v_ws from playlists
-- limit 1` and then asserts that a new video derives its workspace and gains a manifest parent. With
-- no playlists that select binds NULL, the insert matches no rows, and the gate fails with
-- `ASSERTION FAILED — no manifest parent was created for a new video` — a true statement about an
-- empty database rather than about the schema.
--
-- ⚠ Direct insert is correct HERE and wrong above: a workspace is PROVISIONED by a trigger, so
-- writing one by hand would bypass the path under test. A playlist is created by the application
-- during ingest, which no trigger reproduces — so there is nothing to bypass. The `owner_id` and
-- `workspace_id` are read back from the provisioned rows rather than invented, which keeps the
-- foreign keys honest.
--
-- One per workspace, not one in total: the cross-tenant assertions need each tenant to own
-- something, and a single shared playlist would make "the other tenant cannot see it" vacuous in
-- exactly the way the two-user seed above exists to prevent.
insert into public.playlists (owner_id, workspace_id, playlist_key, playlist_url, playlist_title)
select w.owner_id, w.id,
       'ci-seed-' || left(w.id::text, 8),
       'https://www.youtube.com/playlist?list=ci-seed-' || left(w.id::text, 8),
       'CI seed playlist'
  from public.workspaces w;

-- ⛔ THE POSTCONDITION, asserted here rather than hoped for downstream. "The insert returned
-- INSERT 0 1" is a claim about the insert; this is a claim about what the triggers DID. Without it,
-- a provisioning trigger that silently stopped firing would surface 140 seconds later as an
-- unrelated gate's confusing failure.
do $$
declare n_profiles int; n_workspaces int; n_playlists int;
begin
  select count(*) into n_profiles   from public.profiles;
  select count(*) into n_workspaces from public.workspaces;
  select count(*) into n_playlists  from public.playlists;
  if n_profiles < 2 or n_workspaces < 2 or n_playlists < 2 then
    raise exception 'CANNOT RUN — seeding two auth users produced % profile(s) and % workspace(s); '
                    'and % playlist(s); wanted at least 2 of each. Either the provisioning triggers did not fire, or '
                    'both users landed in ONE workspace — and a single-tenant corpus makes every '
                    'cross-tenant assertion vacuous rather than failing.', n_profiles, n_workspaces, n_playlists;
  end if;
end $$;
