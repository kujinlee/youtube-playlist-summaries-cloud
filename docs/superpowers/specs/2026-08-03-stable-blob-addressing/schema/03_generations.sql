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
-- Round 5 B2, SECOND-ORDER: `security_invoker = true` on the views means the view runs as the READER,
-- so the reader needs SELECT on EVERY base table the view joins — and a policy on each, since both
-- carry `force row level security`. MEASURED without this: `permission denied for table
-- workspace_videos`, i.e. the security fix made the serve path unusable.
-- Neither reviewer named this; it is the fix's own cost, found by executing it. Same shape as every
-- other one-site fix this review has produced — B2 was reported at the VIEW and applies at THREE
-- tables, and the sweep is what turns a security fix into a working one.
grant select on workspace_videos to authenticated, anon;
create policy workspace_videos_owner_read on workspace_videos for select to authenticated
  using (workspace_id in (select id from workspaces where owner_id = (select auth.uid())));

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
  -- Round 5 B3: sync's ClassASignals.mdHash had NO cloud source. The spec says so twice in its own
  -- other sections ("grep for mdHash across all 23 migrations returns ZERO"; "needs a persisted hash
  -- of the body, and none exists") while §5.3 asserted reconcileClassA "runs unmodified". It cannot:
  -- reconcile-class-a.ts:17-18 reads mdHash as PRESENCE and :32 as EQUALITY, so projecting it null
  -- makes :23 return copyToCloud unconditionally — every sync appends a new generation, forever, and
  -- every append is a paid slot. Deriving it by READING the blob instead reintroduces shape #1 on the
  -- money path. So it becomes a recorded fact, which is what "runs unmodified" always required.
  md_hash           text,
  created_at        timestamptz not null default now(),
  primary key (workspace_id, video_id, generation_id),
  unique (workspace_id, video_id, generation_id, kind),   -- FK target for video_artifacts (round 2 C2)
  foreign key (workspace_id, video_id)
    references workspace_videos (workspace_id, video_id) on delete cascade,
  -- Card completeness, kind-conditional.
  --
  -- Round 4 J1-2 hardened this against `card = NULL` (SQL null). Round 5 B1 MEASURED that it was
  -- still open one level down: `?&` tests key EXISTENCE, so `{"tldr":null, …}` passed. That is not
  -- merely "an incomplete card is accepted" — the empty card WON THE RANKING and became the served
  -- summary, because `card->>'x'` on a JSON null yields SQL NULL, and rung 1
  -- (`… is not distinct from wv.corrections_hash`) is TRUE when both sides are NULL, which is the
  -- common case (a video with no corrections). An all-null card beat a real doc_version_major=4
  -- generation AND a doc_version_major=99 one. Paid content, unreachable behind an empty row.
  --
  -- Live hazard, not hypothetical: sync-run.ts:534-542 constructs exactly
  -- `{docVersionMajor: 0, mdGeneratedAt: null, mdCorrectionsHash: null, mdHash: null}` and calls it
  -- "an HONEST unresolved placeholder". §5.3 records a local win AS A CARD. It can no longer.
  --
  -- NOTE the asymmetry, from the round-5 cross-derivation (C2): five facts must be non-null VALUES,
  -- but `mdCorrectionsHash` need only be a PRESENT KEY. A null there is the correct, meaningful
  -- answer for a video with no corrections, and requiring it non-null would make rung 1 false for
  -- every uncorrected video — silently demoting the whole ranking to format-only. The reviewer's
  -- proposed fix was deliberately weakened here, and this is why.
  constraint gen_card_complete check (
    kind <> 'summary' or (
      card is not null
      and card ?& array['tldr','takeaways','docVersion','mdGeneratedAt','processedAt',
                        'mdCorrectionsHash']
      -- Spelled out rather than `bool_and(...) from unnest(...)`: MEASURED — Postgres rejects that
      -- with `cannot use subquery in check constraint`. A new PHYSICAL rule, and the reviewer's
      -- proposed fix was the thing that did not execute. Add it to the sweep list.
      and card ->> 'tldr'          is not null
      and card ->> 'takeaways'     is not null
      and card ->> 'docVersion'    is not null
      and card ->> 'mdGeneratedAt' is not null
      and card ->> 'processedAt'   is not null)),
  constraint gen_summary_has_format check (kind <> 'summary' or doc_version_major is not null),
  constraint gen_summary_has_hash check (kind <> 'summary' or md_hash is not null),
  -- Round 5 H5: the ranking trusts `doc_version_major`, and nothing tied it to the `docVersion` the
  -- body actually carries. MEASURED: a card saying "3.3" with the column saying 99 inserted cleanly.
  -- That is §5.2's card/body lie relocated into the ranking key — the one place it does most damage,
  -- since the format rung is the rung that must never regress.
  constraint gen_major_matches_card check (
    kind <> 'summary'
    or doc_version_major = split_part(card ->> 'docVersion', '.', 1)::int)
);
alter table video_generations enable row level security;
alter table video_generations force row level security;
grant select, insert, update, delete on video_generations to service_role;
grant select on video_generations to authenticated, anon;   -- see workspace_videos above (round 5 B2)
create policy video_generations_owner_read on video_generations for select to authenticated
  using (workspace_id in (select id from workspaces where owner_id = (select auth.uid())));
