-- supabase/migrations/0001_core_schema.sql
create table profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  is_anonymous boolean not null default false,
  created_at timestamptz not null default now()
);
alter table profiles enable row level security;
alter table profiles force row level security;

create table playlists (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references profiles(id) on delete cascade,
  playlist_key text not null,             -- YouTube list-id; Principal.outputFolder maps here
  playlist_url text not null,
  playlist_title text,
  created_at timestamptz not null default now(),
  unique (owner_id, playlist_key),
  unique (id, owner_id)                    -- enables the composite FK below
);
alter table playlists enable row level security;
alter table playlists force row level security;

create table videos (
  playlist_id uuid not null,
  owner_id    uuid not null,
  video_id    text not null,               -- Video.id
  position    int  not null,               -- array order in PlaylistIndex.videos
  data        jsonb not null,              -- the whole Video object, verbatim
  updated_at  timestamptz not null default now(),
  primary key (playlist_id, video_id),
  -- a video's owner MUST equal its playlist's owner (cross-tenant injection guard)
  foreign key (playlist_id, owner_id) references playlists(id, owner_id) on delete cascade,
  -- relational id == JSONB id AND id must be present (NULL guard: NULL = video_id is
  -- UNKNOWN and would pass the CHECK, so IS NOT NULL forces rejection of a missing id)
  check (data->>'id' is not null and data->>'id' = video_id),
  -- DEFERRABLE so writeIndex reordering can transiently duplicate a position within a
  -- transaction and settle valid at COMMIT. Must be a CONSTRAINT, not a unique INDEX.
  constraint videos_playlist_position_uniq unique (playlist_id, position)
    deferrable initially deferred
);
alter table videos enable row level security;
alter table videos force row level security;
create index on videos (owner_id);
