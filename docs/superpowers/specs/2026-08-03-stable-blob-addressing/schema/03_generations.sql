-- 03 — the workspace-scoped video entity, and generations.
-- Round 4 J3-2: three columns that round-3 fixes depend on existed ONLY in prose. They are here.

create table workspace_videos (
  workspace_id uuid not null references workspaces(id) on delete cascade,
  video_id     text not null,
  -- fields describing the SHARED BODY live here, not on the per-playlist videos row (round 2 B3):
  corrections        text,
  corrections_hash   text,          -- hash of `corrections`; a generation is "corrections-current"
                                    -- when its mdCorrectionsHash equals this. RANKS, never gates.
  primary key (workspace_id, video_id)
);
alter table workspace_videos enable row level security;
alter table workspace_videos force row level security;
grant select, insert, update, delete on workspace_videos to service_role;

-- videos gains its FK only AFTER workspace_videos is populated (round 4 J1-4).
insert into workspace_videos (workspace_id, video_id)
  select distinct workspace_id, video_id from videos;
alter table videos add constraint videos_workspace_video_fk
  foreign key (workspace_id, video_id) references workspace_videos (workspace_id, video_id);

create type artifact_kind as enum ('summary','model','dig','digDeeper','render');

create table video_generations (
  workspace_id      uuid not null,
  video_id          text not null,
  generation_id     text not null,
  kind              artifact_kind not null,
  card              jsonb,
  doc_version_major int,             -- rule 13's format rung. Round 4 J3-2: ranked on, never defined.
  produced_at       timestamptz not null,   -- PRODUCTION time, carried as DATA across replicas —
                                            -- not now(), which is clock-derived (round 4 J2-3).
  body_collected    boolean not null default false,  -- round 1 H7's lifecycle marker.
  created_at        timestamptz not null default now(),
  primary key (workspace_id, video_id, generation_id),
  unique (workspace_id, video_id, generation_id, kind),   -- FK target for video_artifacts (round 2 C2)
  foreign key (workspace_id, video_id)
    references workspace_videos (workspace_id, video_id) on delete cascade,
  -- Card completeness, kind-conditional. `card ?& …` is FALSE (not NULL) when card is NULL,
  -- so `kind <> 'summary' or (…)` fails CLOSED for a summary with no card — round 4 J1-2.
  constraint gen_card_complete check (
    kind <> 'summary' or (card is not null and card ?& array[
      'tldr','takeaways','docVersion','mdGeneratedAt','processedAt','mdCorrectionsHash'])),
  constraint gen_summary_has_format check (kind <> 'summary' or doc_version_major is not null)
);
alter table video_generations enable row level security;
alter table video_generations force row level security;
grant select, insert, update, delete on video_generations to service_role;
