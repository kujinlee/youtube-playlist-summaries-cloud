-- 01 — workspaces, and the three-phase backfills.
-- Physical rule 4 (`add column … not null` aborts on a populated table) applies at THREE sites here:
-- playlists, videos, jobs. Each gets add-nullable → backfill → set not null. Round 4 J1-3/J1-1.

create table workspaces (
  id         uuid primary key,          -- NO default. The seed below sets id = owner_id, for migrated
                                        -- AND new workspaces alike (round 3 B-3; round 4 Codex #11
                                        -- corrected four sites that still said "random"). Opaque
                                        -- regardless: nothing may branch on the equality, and no
                                        -- predicate may compare a path segment to auth.uid().
                                        -- (There is no 02_*.sql — the seed had to merge into THIS
                                        -- file, because the backfills below read the rows it makes.)
  owner_id   uuid not null references profiles(id) on delete cascade,
  created_at timestamptz not null default now(),
  unique (owner_id),                    -- one workspace per user IS the rule for this slice
  unique (id, owner_id)                 -- FK target for the Q6 cross-tenant guard (round 3 B-6)
);
alter table workspaces enable row level security;
alter table workspaces force row level security;
grant select, insert, update, delete on workspaces to service_role;
grant select on workspaces to authenticated, anon;
create policy workspaces_owner_read on workspaces for select using (owner_id = auth.uid());

-- ── seed BEFORE any backfill reads it (round 4 verify run 1: the backfills ran first and
--    UPDATE 0'd, so `set not null` aborted. Ordering defect caught by executing, not reading).
-- ONE seeding statement, not two (round 4 J3-1 / Codex #1).
--
-- Every workspace takes its owner's uid as its id for the life of this slice, so Principal.id
-- (= auth.uid()) equals the workspace id BY CONSTRUCTION: no Principal change, no object moves.
-- Safe because authorization never compares the path segment to auth.uid() — it goes through
-- workspaces.owner_id, which is revocable.
-- EXPIRY: the day multiple workspaces per user ship, id can no longer equal owner_id.
insert into workspaces (id, owner_id) select id, id from profiles;

-- ── playlists ────────────────────────────────────────────────────────────────
alter table playlists add column workspace_id uuid references workspaces(id);
update playlists p set workspace_id = w.id from workspaces w where w.owner_id = p.owner_id;
alter table playlists alter column workspace_id set not null;

-- ── videos ───────────────────────────────────────────────────────────────────
alter table videos add column workspace_id uuid references workspaces(id);
update videos v set workspace_id = p.workspace_id from playlists p where p.id = v.playlist_id;
alter table videos alter column workspace_id set not null;

-- ── jobs ─────────────────────────────────────────────────────────────────────
alter table jobs add column workspace_id uuid references workspaces(id);
update jobs j set workspace_id = p.workspace_id from playlists p where p.id = j.playlist_id;
alter table jobs alter column workspace_id set not null;
-- §14 Q6's replacement cross-tenant guard, preserving ADR-0002's injection guard one level up.
alter table jobs add constraint jobs_workspace_owner_fk
  foreign key (workspace_id, owner_id) references workspaces (id, owner_id);
