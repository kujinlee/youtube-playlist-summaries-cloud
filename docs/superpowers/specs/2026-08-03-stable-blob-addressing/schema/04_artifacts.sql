-- 04 — the artifact manifest, APPEND-ONLY, plus `current` as a view.
--
-- Round 4 J2-1 / Codex #6 (Blocking): `primary key (workspace, video, slot)` admits ONE row per slot,
-- while rule 13 ranks MANY and A-1's record-first order must insert one BEFORE the bytes. All three
-- ways out of that failed. Resolution: the manifest becomes append-only — one row per GENERATION per
-- slot — and `current` becomes a query rather than a stored pointer. That is what "current is derived"
-- always required and the round-2 PK silently forbade.

create function slot_kind(p_slot text) returns artifact_kind
  language sql immutable as $$
  select case
    when p_slot = 'summary'    then 'summary'
    when p_slot = 'model'      then 'model'
    when p_slot like 'dig:%'   then 'dig'
    when p_slot = 'digDeeper'  then 'digDeeper'
    when p_slot like 'pdf:%'   then 'render'
    when p_slot like 'html%'   then 'render'
  end::artifact_kind $$;

create table video_artifacts (
  workspace_id  uuid not null,
  video_id      text not null,
  slot          text not null,
  generation_id text,                    -- NULL for a free render: it belongs to no generation
  kind          artifact_kind not null,
  state         text not null default 'pending'
                check (state in ('pending','recorded','detached')),
  blob_key      text not null,
  source_generation_id text,             -- §5.1.2: what a derived artifact was built FROM
  start_sec     int,
  end_sec       int,
  lease_expires_at timestamptz,          -- round 4 Codex #5: `pending` MUST be leased, or a writer
  lease_attempts   int not null default 0, --   that dies leaves a permanent `busy`. Same shape as
                                           --   reserve_serve_model's lease/attempt bound (0012/0014).
  updated_at    timestamptz not null default now(),
  -- APPEND-ONLY: one row per (slot, generation), not one per slot.
  primary key (workspace_id, video_id, slot, generation_id),
  foreign key (workspace_id, video_id, generation_id, kind)
    references video_generations (workspace_id, video_id, generation_id, kind),
  constraint art_slot_kind check (slot_kind(slot) is not null and kind = slot_kind(slot)),
  constraint art_paid_has_generation check
    ((kind in ('summary','model','dig','digDeeper')) = (generation_id is not null)),
  constraint art_pending_is_leased check ((state = 'pending') = (lease_expires_at is not null))
);
alter table video_artifacts enable row level security;
alter table video_artifacts force row level security;
grant select, insert, update, delete on video_artifacts to service_role;
grant select on video_artifacts to authenticated, anon;

-- `current` — derived, ranked, with a FLOOR. Round 4 J2-4 / A-2:
--   servable  = state 'recorded'. That is the WHOLE test; it cannot empty a non-empty set.
--   preferred = the ranking below. Staleness RANKS, it never GATES.
-- Every rung is a recorded fact carried as DATA (produced_at, not now()) so the result is a
-- deterministic function of the generation set — round 4 J2-3.
create view video_artifacts_current as
select distinct on (a.workspace_id, a.video_id, a.slot) a.*
from video_artifacts a
join video_generations g
  on  g.workspace_id = a.workspace_id and g.video_id = a.video_id
  and g.generation_id = a.generation_id
join workspace_videos wv
  on  wv.workspace_id = a.workspace_id and wv.video_id = a.video_id
where a.state = 'recorded' and not g.body_collected
order by a.workspace_id, a.video_id, a.slot,
         (g.card->>'mdCorrectionsHash' is not distinct from wv.corrections_hash) desc,
         g.doc_version_major desc nulls last,
         g.produced_at desc,
         a.generation_id desc;
